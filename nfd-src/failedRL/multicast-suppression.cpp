#include "multicast-suppression.hpp"
#include <tuple>
#include <functional>
#include <iostream>
#include "common/global.hpp"
#include "common/logger.hpp"
#include <algorithm>
#include <numeric>
#include<stdio.h>
#include <random>
#include <math.h>
#include <fstream>
#include <errno.h>

namespace nfd {
namespace face {
namespace ams {

NFD_LOG_INIT(MulticastSuppression);

double DISCOUNT_FACTOR = 0.125;
double MAX_PROPOGATION_DELAY = 15;
const time::milliseconds MAX_MEASURMENT_INACTIVE_PERIOD = 300_s; // 5 minutes



/* This is 2*MAX_PROPOGATION_DELAY.  Basically, when a nodes (C1) forwards a packet, it will take 15ms to reach
its neighbors (C2). The packet will be recevied by the neighbors and they will suppress their forwarding. In case,
if the neighbor didnt received the packet from C1 in 15 ms, it will forward its own packet. Now, the actual duplicate count
in the network is 2, both nodes C1 & C2 should record dc = 2. For this to happen, it takes about 15ms for the packet from C2 to
reach C1. Thus, DEFAULT_INSTANT_LIFETIME = 30ms*/
// Originally Default instant lifetime (interest life time in measurement table) = 30 ms
const time::milliseconds DEFAULT_INSTANT_LIFETIME = 30_ms; // 2*MAX_PROPOGATION_DELAY
const double DUPLICATE_THRESHOLD = 1.3; // parameter to tune
const double ADATIVE_DECREASE = 5.0;
const double MULTIPLICATIVE_INCREASE = 1.2;

// in milliseconds ms
// probably we need to provide sufficient time for other party to hear you?? MAX_PROPAGATION_DELAY??
const double minSuppressionTime = 10.0f;
const double maxSuppressionTime= 15000.0f;
static bool seeded = false;

unsigned int UNSET = -1234;
int CHARACTER_SIZE = 126;
int maxIgnore = 0;

int counter = 0;


char FIFO_OBJECT[] = "fifo_object_details";
char FIFO_VALUE[] = "fifo_suppression_value";

/* only for experimentation, will be removed later */
int
getSeed()
{
  std::string line;
  std::ifstream f ("seed"); // read file and return the value
  getline(f, line);
  auto seed = std::stoi (line);
  NFD_LOG_INFO ("value of the seed: " << seed);
  return seed;
}

int
getRandomNumber(int upperBound)
{
  if (!seeded)
  {
    unsigned seed = getSeed();
    NFD_LOG_INFO ("seeded " << seed);
    std::srand(seed);
    seeded = true;
  }
  return std::rand() % upperBound;
}

NameTree::NameTree()
: isLeaf(false)
, suppressionTime(UNSET)
{
}

double 
_FIFO::fifo_handler(const std::string& content)
{
  char buffer[1024];
  int fifo; 
  try {
    fifo = open(FIFO_OBJECT, O_WRONLY, 0666);
  }
  catch (const std::exception &e) {
    NFD_LOG_INFO("Unfortunately came here");
    std::cerr << e.what() << '\n';
  }
  if (fifo < 0)
  {
    NFD_LOG_INFO("Couldn't open fifo file");
    NFD_LOG_INFO("writer open failed: " << fifo << strerror(fifo));
    return 0.0;
  }
  try {
      NFD_LOG_INFO("This is the message to write: " << content);
      auto ret_code = write(fifo, content.c_str(), content.size());
      NFD_LOG_INFO("return code: " << ret_code << " after write: " << content);
    }
    catch (const std::exception &e) {
      NFD_LOG_INFO("Unfortunately came here");
      std::cerr << e.what() << '\n';
    }
  counter += 1;
  auto ret = close(fifo);
  NFD_LOG_INFO("return code after close: " << ret);

    // wait for a response from python process
  auto pipeFile = open(FIFO_OBJECT, O_RDONLY);
  if (pipeFile == -1) {
    std::cerr << "Error opening named pipe." << std::endl;
    return 0.0;
  }
  int bytesRead = read(pipeFile, buffer, sizeof(buffer) - 1);
  buffer[bytesRead] = '\0';
  NFD_LOG_INFO("Python Test: " << buffer << " Counter " << counter);

  close(pipeFile);
  auto suppression_time = std::stod(std::string(buffer));
  return suppression_time;  
}


void
NameTree::insert(std::string prefix, double value)
{
  NFD_LOG_INFO("The suppression time to be inserted " << value << " for the prefix " << prefix);
  auto node = this; // this should be root
  for (unsigned int i = 0; i < prefix.length(); i++)
  {
    auto index = prefix[i] - 'a';
    if (!node->children[index])
      node->children[index] = new NameTree();

    if (i == prefix.length() - 1) {
      node->suppressionTime = value;
      // node->suppressionTime = minSuppressionTime;
    }
    node = node->children[index];
  }
  // leaf node
  node->isLeaf = true;
}

// std::pair<double, double>
double
NameTree::longestPrefixMatch(const std::string& prefix) // longest prefix match
{
  // NFD_LOG_INFO("****************** LongestPrefixMatch Function called ********************" << prefix);
  auto node = this;
  double lastValueFound = UNSET;
  // double minSuppressionTime = 0;
  for (unsigned int i=0; i < prefix.length(); i++)
  {
    auto index = prefix[i] - 'a';
    if (prefix[i+1] == '/') // key at i is the available prefix if the next item is /
      {
        lastValueFound = node->suppressionTime;
        // minSuppressionTime = node->minSuppressionTime;
      }

    if (!node->children[index])
      return lastValueFound;
      // return std::make_pair(lastValueFound, minSuppressionTime);

    if (i == prefix.length() - 1)
      {
        lastValueFound = node->suppressionTime;
        // minSuppressionTime = node->minSuppressionTime;
      }

    node = node->children[index];
  }
  return lastValueFound;
  // return std::make_pair(lastValueFound, minSuppressionTime);;
}

time::milliseconds
NameTree::getSuppressionTimer(const std::string& name)
{
  // NFD_LOG_INFO("****************** GetSuppressionTime Function without random called ********************" << name);
  double val, suppressionTime;
  val = longestPrefixMatch(name);
  // NFD_LOG_INFO("The suppression time from the name tree is : " << val);
  suppressionTime = (val == UNSET) ? minSuppressionTime : val;
  time::milliseconds suppressionTimer (static_cast<int> (suppressionTime));
  // NFD_LOG_INFO("Suppression time: " << suppressionTime << " Suppression timer: " << suppressionTimer);
  return suppressionTimer;
}




/* objectName granularity is (-1) name component
  m_lastForwardStaus is set to true if this node has successfully forwarded an interest or data
  else is set to false.
  start with 15ms, MAX propagation time, for a node to hear other node
  or start with 1ms, and let node find stable suppression time region?
*/
EMAMeasurements::EMAMeasurements(double expMovingAverage = 0, int lastDuplicateCount = 0, double suppressionTime = 15)
: m_expMovingAveragePrev (expMovingAverage)
, m_expMovingAverageCurrent (expMovingAverage)
, m_currentSuppressionTime(suppressionTime)
, m_computedMaxSuppressionTime(suppressionTime)
, m_lastDuplicateCount(lastDuplicateCount)
, m_maxDuplicateCount (1)
, m_minSuppressionTime(minSuppressionTime)
, ignore(0)
// , m_fifo()
{
}


void
EMAMeasurements::addUpdateEMA(int duplicateCount, bool wasForwarded, std::string name, std::string seg_name, char type, time::milliseconds waitTime, NameTree* nameTree)
{
  // NFD_LOG_INFO("***********************Add update ema function called to calculate duplicate count and moving average******************" << seg_name);

  // NFD_LOG_INFO("Ignore = " << ignore << "Segment name " << seg_name << "Duplicate Count " << duplicateCount << " Last Duplicate count " << m_lastDuplicateCount << " m_expMovingAveragePrev " << m_expMovingAveragePrev << " m_expMovingAverageCurrent " << m_expMovingAverageCurrent);
  m_lastDuplicateCount = duplicateCount;
  ignore = 0;

  m_expMovingAveragePrev = m_expMovingAverageCurrent;
  if (m_expMovingAverageCurrent == 0) {
    m_expMovingAverageCurrent = duplicateCount;
  }
  else
  {
    // m_expMovingAverageCurrent =  round ((DISCOUNT_FACTOR*duplicateCount + 
    //                                          (1 - DISCOUNT_FACTOR)*m_expMovingAverageCurrent)*100.0)/100.0;
    m_expMovingAverageCurrent =  round ((DISCOUNT_FACTOR*duplicateCount + 
                                              (1 - DISCOUNT_FACTOR)*m_expMovingAveragePrev)*100.0)/100.0; 
    // if this node hadn't forwarded don't update the delay timer ???
  }
  if (m_maxDuplicateCount < duplicateCount) { m_maxDuplicateCount = duplicateCount; }

  if (m_maxDuplicateCount > 1)
    m_minSuppressionTime = (float) MAX_PROPOGATION_DELAY;
  else if (m_maxDuplicateCount == 1 && m_minSuppressionTime > 1)
      m_minSuppressionTime--;

  // if(wasForwarded || duplicateCount == 0){
  //   updateDelayTime(name, seg_name, m_expMovingAverageCurrent, waitTime, wasForwarded, type, nameTree);
  // }
  updateDelayTime(name, seg_name, m_expMovingAverageCurrent, waitTime, wasForwarded, type, nameTree);
  NFD_LOG_INFO("Moving average" << " before: " << m_expMovingAveragePrev
                                << " after: " << m_expMovingAverageCurrent
                                << " duplicate count: " << duplicateCount
                                << " suppression time: "<< m_currentSuppressionTime
                                << " computed max: " << m_computedMaxSuppressionTime
                                << " wait time: " << waitTime
              );
}


// Update suppression time
void
EMAMeasurements::updateDelayTime(std::string name, std::string seg_name, float duplicateCount, time::milliseconds suppression_time, bool wasForwarded, char type, NameTree* nameTree)
{
  // NFD_LOG_INFO("****************** UpdateDelayTime Function called ********************" << seg_name);

  auto suppressionTimer = nameTree->getSuppressionTimer(name);
  NFD_LOG_INFO("Name tree suppression time " << suppressionTimer);
  // std::istringstream iss(seg_name);
  // std::string token;
  // while (std::getline(iss, token, '='));
  // NFD_LOG_INFO("The token is " << token);

 
  boost::property_tree::ptree message;
  message.put("ewma_dc", duplicateCount);
  message.put("name", name);
  message.put("suppression_time", suppression_time);
  std::ostringstream oss;
  boost::property_tree::write_json(oss, message, false);
  std::string messageString = oss.str(); 

  // NFD_LOG_INFO("The forwarded status for " << seg_name << " is " << wasForwarded << " with suppression TIme " << suppression_time << " and dc " << duplicateCount);
  // NFD_LOG_INFO("The state is forwarded as no other packets were heard for " << seg_name << " with average duplicate ");

  auto from_python = round(m_fifo.fifo_handler(messageString));
  m_currentSuppressionTime =(m_minSuppressionTime, from_python);


  // NFD_LOG_INFO("the suppression timer are " << suppressionTimer);
  // auto from_python = round(m_fifo.fifo_handler(messageString));
  // m_currentSuppressionTime =(m_minSuppressionTime, from_python);
    
  
  
  NFD_LOG_INFO("For moving average " << duplicateCount << " name " << seg_name << " from the time " << suppression_time << "Got suppression time " << m_currentSuppressionTime);
  // NFD_LOG_INFO("Python Test from python = " << from_python << " m suppression time " << m_currentSuppressionTime);

}

void
MulticastSuppression::recordInterest(const Interest interest, bool isForwarded, time::milliseconds suppressionTime)
{
  // NFD_LOG_INFO("****************** RecordInterest Function called ********************" << interest.getName() << " Forwarded status = " << isForwarded << " wait time " << suppressionTime);
  auto name = interest.getName();
  // NFD_LOG_INFO("Interest to check/record " << name);
  auto it = m_interestHistory.find(name); //check if interest is already in the map
  if (it == m_interestHistory.end()) // the element with key 'name' is not found
  {     
    m_interestHistory.emplace(name, ObjectHistory{1, isForwarded});
    NFD_LOG_INFO ("Interest: " << name << " inserted into map");
    //  remove the entry after the lifetime expires
    time::milliseconds entryLifetime = DEFAULT_INSTANT_LIFETIME;
    NFD_LOG_INFO("Erasing the interest from the map in : " << entryLifetime);
    setUpdateExpiration(entryLifetime, name, 'i', suppressionTime, isForwarded);
  }
  else {    
    NFD_LOG_INFO("Counter for interest " << name << " incremented");
    if (!getForwardedStatus(name, 'i') && isForwarded) {
      ++it->second.counter;
      it->second.isForwarded = true;
    }
    else {
      ++it->second.counter;
    }
  }
  
}


void
MulticastSuppression::recordData(Data data, bool isForwarded, time::milliseconds waitTime)
{
  // NFD_LOG_INFO("****************** RecordData Function called ********************" << data.getName() << " Forwarded status = " << isForwarded << " wait Time " << waitTime);
    auto name = data.getName(); //.getPrefix(-1); //removing nounce
    NFD_LOG_INFO("Data to check/record " << name);
    auto it = m_dataHistory.find(name);
    // NFD_LOG_INFO("Analysis History Satisfied data for Corresponding interest: " << name);
    if (it == m_dataHistory.end()) // if data is not in dataHistory
    {
      // NFD_LOG_INFO("Inserting data " << name << " into the map");
      m_dataHistory.emplace(name, ObjectHistory{1, isForwarded});
      time::milliseconds entryLifetime = DEFAULT_INSTANT_LIFETIME;
      // NFD_LOG_INFO("Erasing the data from the map in : " << entryLifetime);
      setUpdateExpiration(entryLifetime, name, 'd', waitTime, isForwarded);
    }
    else
    {
      if (!getForwardedStatus(name, 'd') && isForwarded) {
        NFD_LOG_INFO("Counter for  data " << name << " incremented, and the flag is updated " << !getForwardedStatus(name, 'd'));
        ++it->second.counter;
        it->second.isForwarded = true;
      }
      else if (!isForwarded) {
        NFD_LOG_INFO("Counter for  data " << name << " incremented , no change in flag");
        ++it->second.counter;
      }
      else NFD_LOG_INFO("do nothing"); // do nothing
    }

    // need to check if we have the interest in the map
    // if present, need to remove it from the map
    ndn::Name name_cop = name;
    name_cop.appendNumber(0);
    auto itr_timer = m_objectExpirationTimer.find(name_cop);
    if (itr_timer != m_objectExpirationTimer.end())
    {
      NFD_LOG_INFO("Data overheard, deleting interest " <<name << " from the map");
      itr_timer->second.cancel();
      // schedule deletion now
      if (m_interestHistory.count(name) > 0)
      {
        // Calculate the EWMA of the duplicate count
        updateMeasurement(name, 'i', waitTime, "no");
        int dup_int_count = 0;
        // auto duplicateCountInterest = getDuplicateCount(name, 'i');
      
        // NFD_LOG_INFO("Duplicate Count " << duplicateCountInterest <<"Analysis History Interest " << name);
        // Remove the matching Interest entry from the table
        m_interestHistory.erase(name);
        NFD_LOG_INFO("Interest successfully deleted from the history " <<name);
      }
    }
}

int
MulticastSuppression::getDuplicateCount(const Name name, char type)
{
  auto temp_map = getRecorder(type);
  auto it = temp_map->find(name);
  if (it != temp_map->end()){
    return it->second.counter;
  }
  return 0;
}
void
MulticastSuppression::setUpdateExpiration(time::milliseconds entryLifetime, Name name, char type, time::milliseconds waitTime, bool isForwarded)
{
  // NFD_LOG_INFO("****************** SetUPdateExpiration Function called ********************" << name << " the entry life time is " << entryLifetime);
  auto vec = getRecorder(type);
  auto duplicateCount = getDuplicateCount(name, type);
  // if(!isForwarded && waitTime > time::milliseconds(0)){
  //   NFD_LOG_INFO("The interest is dropped which had wait time " << waitTime);
  //   updateMeasurement(name, 'i', waitTime, "yes");
  //   return;
    
  // }
  auto eventId = getScheduler().schedule(entryLifetime, [=]  {
    if (vec->count(name) > 0)
    {
      //  record interest into moving average
      updateMeasurement(name, type, waitTime, "no");
     
      vec->erase(name);
      NFD_LOG_INFO("Name: " << name << " type: " << type << " expired, and deleted from the instant history");

    }
    });

    name =  (type == 'i') ? name.appendNumber(0) : name.appendNumber(1);
    auto itr_timer = m_objectExpirationTimer.find(name);
    if (itr_timer != m_objectExpirationTimer.end())
    {
      NFD_LOG_INFO("Updating timer for name: " << name << "type: " << type);
      itr_timer->second.cancel();
      itr_timer->second = eventId;
    }
    else
    {
      m_objectExpirationTimer.emplace(name, eventId);
    }
}

void
MulticastSuppression::updateMeasurement(Name name, char type, time::milliseconds waitTime, std::string isDropped)
{
    // NFD_LOG_INFO("****************** UpdateMeasurement Function called ********************" << name);
    // if the measurment expires, can't the name stay with EMA = 0? so that we dont have to recreate it again later
    auto objectHistory = getEMARecorder(type); //return (type =='i') ? &m_EMA_interest : &m_EMA_data;
    auto nameTree = getNameTree(type); //return (type =='i') ? &m_interestNameTree : &m_dataNameTree; //0x555fd2842058
    auto duplicateCount = getDuplicateCount(name, type);
    NFD_LOG_INFO("getDuplicateCount Function called from updateMeasuerment " << duplicateCount << "for segment " << name << " name tree " << nameTree); 
    bool wasForwarded = getForwardedStatus(name, type);
     if(type=='i'){
        NFD_LOG_INFO("Duplicate count "<< duplicateCount << "type = " << type << " Analysis History Interest " << name);
      }
      else{
        NFD_LOG_INFO("Duplicate count "<< duplicateCount << "type = " << type << " Analysis History Data " << name);
      }

    NFD_LOG_INFO("Name:  " << name << " Duplicate Count from getDuplicate: " << duplicateCount << " type: " << type);
    // granularity = name - last component e.g. /a/b --> /a
    auto seg_name = name.toUri();
    name = name.getPrefix(-1);
    auto& emaEntry = (*objectHistory)[name];

    // no records
    if (!emaEntry)
    {
      emaEntry = std::make_shared<EMAMeasurements>();
      NFD_LOG_INFO("Creating EMA record for name: " << name << " type: " << type);
      auto expirationId = getScheduler().schedule(MAX_MEASURMENT_INACTIVE_PERIOD, [=]  {
                                      objectHistory->erase(name);  // remove expired record
                                      nameTree->insert(name.toUri(), UNSET);  // unset the value in the name tree
                                  });
      emaEntry->setEMAExpiration(expirationId);

      // emaEntry->getCurrentSuppressionTime() will return m_currentSuppressionTime
      nameTree->insert(name.toUri(), emaEntry->getCurrentSuppressionTime());
      // auto emtime = emaEntry->getCurrentSuppressionTime();
      // NFD_LOG_INFO("THe name inserted in name tree " << name << " and the suppression time from ema for new " << emtime);
    }
    // update existing record
    else
    {
      NFD_LOG_INFO("Updating EMA record for name: " << name << " type: " << type);
      emaEntry->getEMAExpiration().cancel();
      auto expirationId = getScheduler().schedule(MAX_MEASURMENT_INACTIVE_PERIOD, [=]  {
                                          objectHistory->erase(name);  // remove expired record
                                          nameTree->insert(name.toUri(), UNSET);  // unset the value in the name tree
    });
      emaEntry->setEMAExpiration(expirationId);
      nameTree->insert(name.toUri(), emaEntry->getCurrentSuppressionTime());
      // NFD_LOG_INFO("THe name inserted in name tree " << name << " and the suppression time from update " << emaEntry->getCurrentSuppressionTime());

    }
    
    if(isDropped == "yes"){
      emaEntry->addUpdateEMA(0, wasForwarded, name.toUri(), seg_name, type, waitTime, nameTree);
    }
    else{
      emaEntry->addUpdateEMA(duplicateCount, wasForwarded, name.toUri(), seg_name, type, waitTime, nameTree);
    }
      // emaEntry->updateDelayTime(name.toUri(), seg_name, 0.0, waitTime, false, type);

}


time::milliseconds
MulticastSuppression::getDelayTimer(Name name, char type)
{
  NFD_LOG_INFO("Getting supperssion timer for name: " << name << " type " << type);
  auto nameTree = getNameTree(type);

  auto suppressionTimer = nameTree->getSuppressionTimer(name.getPrefix(-1).toUri());
  NFD_LOG_INFO("Suppression timer for name: " << name << " and type: "<< type << " = " << suppressionTimer << " name tree " << nameTree);
  return suppressionTimer;
}


} //namespace ams
} //namespace face
} //namespace nfd