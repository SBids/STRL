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
double MAX_PROPOGATION_DELAY = 150;
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
const double minSuppressionTime = 1.0f;
const double maxSuppressionTime= 15000.0f;
static bool seeded = false;

unsigned int UNSET = -1234;
int CHARACTER_SIZE = 126;
int maxIgnore = 0;

int counter = 0;


char FIFO_OBJECT[] = "fifo_object_details";
char FIFO_VALUE[] = "fifo_suppression_value";
int previous_time_i = 0;
int previous_time_d = 0;

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
  prefix = "/producer/sta1";
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
  NFD_LOG_INFO("****************** LongestPrefixMatch Function called ********************" << prefix);
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
  NFD_LOG_INFO("****************** GetSuppressionTime Function without random called ********************" << name);
  double val, suppressionTime;
  val = longestPrefixMatch(name);
  NFD_LOG_INFO("Longest prefix match value for " << name << " is " << val);
  suppressionTime = (val == UNSET) ? minSuppressionTime : val;
  time::milliseconds suppressionTimer (static_cast<int> (suppressionTime));
  NFD_LOG_INFO("Suppression time: " << suppressionTime << " Suppression timer: " << suppressionTimer);
  return suppressionTimer;
}




/* objectName granularity is (-1) name component
  m_lastForwardStaus is set to true if this node has successfully forwarded an interest or data
  else is set to false.
  start with 15ms, MAX propagation time, for a node to hear other node
  or start with 1ms, and let node find stable suppression time region?
*/
EMAMeasurements::EMAMeasurements(double expMovingAverage = 0, int lastDuplicateCount = 0, double suppressionTime =0) 
: m_expMovingAveragePrev (expMovingAverage)
, m_expMovingAverageCurrent (expMovingAverage)
// , m_currentSuppressionTime(suppressionTime)
, m_currentSuppressionTimeInterest(suppressionTime)
, m_currentSuppressionTimeData(suppressionTime)
, m_computedMaxSuppressionTime(suppressionTime)
, m_lastDuplicateCount(lastDuplicateCount)
, m_maxDuplicateCount (1)
, m_minSuppressionTime(minSuppressionTime)
, ignore(0)
// , m_fifo()
{
}


void
EMAMeasurements::addUpdateEMA(int duplicateCount, bool wasForwarded, std::string name, std::string seg_name, char type, time::milliseconds waitTime, int rtt)
{
  NFD_LOG_INFO("***********************Add update ema function called to calculate duplicate count and moving average******************" << seg_name);

  NFD_LOG_INFO("Ignore = " << ignore << "Segment name " << seg_name << "Duplicate Count " << duplicateCount << " Last Duplicate count " << m_lastDuplicateCount << " m_expMovingAveragePrev " << m_expMovingAveragePrev << " m_expMovingAverageCurrent " << m_expMovingAverageCurrent);
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

  
  updateDelayTime(name, seg_name, duplicateCount, waitTime, wasForwarded, type, rtt);
  NFD_LOG_INFO("Moving average" << " before: " << m_expMovingAveragePrev
                                << " after: " << m_expMovingAverageCurrent
                                << " duplicate count: " << duplicateCount
                                // << " suppression time: "<< m_currentSuppressionTime
                                << " suppression time Interest: "<< m_currentSuppressionTimeInterest
                                << " suppression time Data: "<< m_currentSuppressionTimeData
                                // << " computed max: " << m_computedMaxSuppressionTime
                                << " wait time: " << waitTime
                                << " seg name " << seg_name
              );

}


// Update suppression time
void
EMAMeasurements::updateDelayTime(std::string name, std::string seg_name, float duplicateCount, time::milliseconds suppression_time, bool wasForwarded, char type, int rtt)
{
  NFD_LOG_INFO("****************** UpdateDelayTimer Function called ********************" << seg_name);
 
  boost::property_tree::ptree message;
  MulticastSuppression multicastSuppression;
  message.put("ewma_dc", duplicateCount);
  message.put("name", name);
  // message.put("rtt", rtt);
  message.put("type", type);
  message.put("wasForwarded", wasForwarded);
  message.put("suppression_time", suppression_time);
  std::ostringstream oss;
  boost::property_tree::write_json(oss, message, false);
  std::string messageString = oss.str(); 
  NFD_LOG_INFO("The forwarded status for " << seg_name << " is " << wasForwarded << " with suppression TIme " << suppression_time << " and dc " << duplicateCount << "and type is " << type);
  NFD_LOG_INFO("The forwarded status for " << seg_name << " The suppression time for up interest " << suppression_time << " and the previous time " << previous_time_i);
  NFD_LOG_INFO("The forwarded status for " << seg_name << "The suppression time for up data " << suppression_time << " and the previous time " << previous_time_d);


  // auto from_python = m_fifo.fifo_handler(messageString);
  // NFD_LOG_INFO("Python Test from python = " << from_python);
  // m_currentSuppressionTime = std::round(from_python * 100.0) / 100.0;;
  // NFD_LOG_INFO("The m_currentSuppressionTime is " << m_currentSuppressionTime);  
  // NameTree* nameTree = multicastSuppression.getNameTree('i');
  // nameTree->insert(name, m_currentSuppressionTime);


  // if(suppression_time.count() == previous_time_i){
  //   int st = suppression_time.count();
  //   NFD_LOG_INFO("The suppression time for interest " << st << " and the previous time " << previous_time_i);

  //   auto from_python = m_fifo.fifo_handler(messageString);
  //   NFD_LOG_INFO("Python Test from python = " << from_python);
  //   m_currentSuppressionTime = std::round(from_python * 100.0) / 100.0;;
  //   NFD_LOG_INFO("The m_currentSuppressionTime is " << m_currentSuppressionTime);  
  //   NameTree* nameTree = multicastSuppression.getNameTree('i');
  //   nameTree->insert(name, m_currentSuppressionTime);
  //   previous_time_i = m_currentSuppressionTime;   
  //   auto chkst = multicastSuppression.getDelayTimer(name, 'i');
  //   NFD_LOG_INFO("Checking the stored suppression time in name tree " << chkst << " Previous time set " << previous_time_i << " m_currentSuppressionTime" << m_currentSuppressionTime);
  // }
  // if(wasForwarded){
  NFD_LOG_INFO("The m_currentSuppressionTime Data is " << m_currentSuppressionTimeData << " segment " << seg_name << " wait time " << suppression_time);
  NFD_LOG_INFO("The m_currentSuppressionTime Interest is " << m_currentSuppressionTimeInterest << " segment " << seg_name << " wait time " << suppression_time);
  if(type == 'i' && suppression_time.count() == previous_time_i){
    int st = suppression_time.count();
    NFD_LOG_INFO("type " << type << " suppression time " << st << " status of the condition ");
    NFD_LOG_INFO("The suppression time for interest " << suppression_time << " and the previous time " << previous_time_i);
    auto from_python = m_fifo.fifo_handler(messageString);
    NFD_LOG_INFO("Python Test from python = " << from_python);
    m_currentSuppressionTimeInterest = std::round(from_python * 100.0) / 100.0;;
    NameTree* nameTree = multicastSuppression.getNameTree(type);
    nameTree->insert(name, m_currentSuppressionTimeInterest);
    previous_time_i = m_currentSuppressionTimeInterest; 
    auto chkst = multicastSuppression.getDelayTimer(seg_name, 'i');
    NFD_LOG_INFO("Checking the stored suppression time in name tree Interest " << chkst << " Previous time set " << previous_time_i << " m_currentSuppressionTime" << m_currentSuppressionTimeInterest << " seg name " << seg_name);
  }
  else if(type == 'd' && suppression_time.count() == previous_time_d){    
    int st = suppression_time.count();
   
    NFD_LOG_INFO("The suppression time for data " << suppression_time << " and the previous time " << previous_time_d << " seg name " << seg_name);
    auto from_python = m_fifo.fifo_handler(messageString);
    NFD_LOG_INFO("Python Test from python = " << from_python<< " seg name " << seg_name);
    m_currentSuppressionTimeData = std::round(from_python * 100.0) / 100.0;;
    NameTree* nameTree = multicastSuppression.getNameTree(type);
    nameTree->insert(name, m_currentSuppressionTimeData);
    previous_time_d = m_currentSuppressionTimeData;  
    auto chkst = multicastSuppression.getDelayTimer(seg_name, 'd');
    NFD_LOG_INFO("Checking the stored suppression time in name tree data" << chkst << " Previous time set " << previous_time_d << " m_currentSuppressionTime Data" << m_currentSuppressionTimeData << " seg name " << seg_name);
  
  } 
}

void
MulticastSuppression::recordInterest(const Interest interest, bool isForwarded, time::milliseconds suppressionTime)
{
  NFD_LOG_INFO("****************** RecordInterest Function called ********************" << interest.getName());
  auto name = interest.getName();
  NFD_LOG_INFO("Interest to check/record " << name);
  auto it = m_interestHistory.find(name); //check if interest is already in the map
  if (it == m_interestHistory.end()) // the element with key 'name' is not found
  { 

    std::chrono::time_point<std::chrono::system_clock> currentTime = std::chrono::system_clock::now();
    std::chrono::milliseconds currentTimeMs = std::chrono::duration_cast<std::chrono::milliseconds>(currentTime.time_since_epoch());
    long long send_time_milliseconds = currentTimeMs.count();
    NFD_LOG_INFO("Send time " << send_time_milliseconds);
    // Print the milliseconds value
    NFD_LOG_INFO("Milliseconds Sent Interest: " << isForwarded << std::endl);    
    m_interestHistory.emplace(name, ObjectHistory{1, isForwarded, send_time_milliseconds, 0});
    NFD_LOG_INFO ("Interest: " << name << " inserted into map");
    //  remove the entry after the lifetime expires
    time::milliseconds entryLifetime = DEFAULT_INSTANT_LIFETIME;
    NFD_LOG_INFO("Erasing the interest from the map in : " << entryLifetime << " name of interest " << name);
    setUpdateExpiration(entryLifetime, name, 'i', suppressionTime);
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
  NFD_LOG_INFO("****************** RecordData Function called ********************" << data.getName());
    auto name = data.getName(); //.getPrefix(-1); //removing nounce
    NFD_LOG_INFO("Data to check/record " << name);
    auto it = m_dataHistory.find(name);
    std::chrono::time_point<std::chrono::system_clock> currentTime = std::chrono::system_clock::now();
    std::chrono::milliseconds currentTimeMs = std::chrono::duration_cast<std::chrono::milliseconds>(currentTime.time_since_epoch());
    long long receive_time_milliseconds = currentTimeMs.count();
    NFD_LOG_INFO("Receive time " << receive_time_milliseconds);
    int rtt = 0;
    auto interest_record = m_interestHistory.find(name);
   if (interest_record != m_interestHistory.end()) {
        ObjectHistory& interestValue = interest_record->second;
        auto i_time_milliseconds = interestValue.propagationTime;

        // Calculate RTT if interest record exists
        rtt = receive_time_milliseconds - i_time_milliseconds;
        NFD_LOG_INFO("Interest time milli " << i_time_milliseconds << " receive time milili " << receive_time_milliseconds << " RTT " << rtt);
    } else {
        // Log a message indicating that interest record doesn't exist
        NFD_LOG_INFO("No interest record found for " << name);
    }

    NFD_LOG_INFO("Analysis History Satisfied data for Corresponding interest: " << name);
    if (it == m_dataHistory.end()) // if data is not in dataHistory
    {
      NFD_LOG_INFO("Inserting data " << name << " into the map");
     
      m_dataHistory.emplace(name, ObjectHistory{1, isForwarded, receive_time_milliseconds, rtt});
      time::milliseconds entryLifetime = DEFAULT_INSTANT_LIFETIME;
      NFD_LOG_INFO("Erasing the data from the map in : " << entryLifetime << " name " << name);
      setUpdateExpiration(entryLifetime, name, 'd', waitTime);
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
        updateMeasurement(name, 'i', waitTime, rtt);
        auto duplicateCount = getDuplicateCount(name, 'i');
        NFD_LOG_INFO("The duplciat ecount for setUpdateExpiration " << name << " is " << duplicateCount << " type " << 'i');
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
MulticastSuppression::setUpdateExpiration(time::milliseconds entryLifetime, Name name, char type, time::milliseconds waitTime)
{
  NFD_LOG_INFO("****************** SetUPdateExpiration Function called ********************" << name << " the entry life time is " << entryLifetime);
  auto vec = getRecorder(type);
  
  auto eventId = getScheduler().schedule(entryLifetime, [=]  {
    if (vec->count(name) > 0)
    {
      //  record interest into moving average
      updateMeasurement(name, type, waitTime, 0);
      auto duplicateCount = getDuplicateCount(name, type);
      NFD_LOG_INFO("The duplciat ecount for setUpdateExpiration " << name << " is " << duplicateCount << " type " << type);
      vec->erase(name);

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
MulticastSuppression::updateMeasurement(Name name, char type, time::milliseconds waitTime, int rtt)
{
    NFD_LOG_INFO("****************** UpdateMeasurement Function called ********************" << name);
      // if the measurment expires, can't the name stay with EMA = 0? so that we dont have to recreate it again later
    auto vec = getEMARecorder(type);
    auto nameTree = getNameTree(type);
    auto duplicateCount = getDuplicateCount(name, type);
    bool wasForwarded = getForwardedStatus(name, type);

    NDN_LOG_INFO("Name:  " << name << " Duplicate Count: " << duplicateCount << " type: " << type);
    // granularity = name - last component e.g. /a/b --> /a
    auto seg_name = name.toUri();
    name = name.getPrefix(-1);
    auto it = vec->find(name);

    // no records
    if (it == vec->end())
    {
      NFD_LOG_INFO("Creating EMA record for name: " << name << " type: " << type << " wait time " << waitTime<< " seg name " << seg_name);
      auto expirationId = getScheduler().schedule(MAX_MEASURMENT_INACTIVE_PERIOD, [=]  {
                                      if (vec->count(name) > 0)
                                          vec->erase(name);
                                          // dont delete the entry in the nametree, just unset the value
                                      // nameTree->insert(name.toUri(), it->second->getCurrentSuppressionTimeInterest());
                                  });
      auto& emaEntry = vec->emplace(name, std::make_shared<EMAMeasurements>()).first->second;
      emaEntry->setEMAExpiration(expirationId);
      emaEntry->addUpdateEMA(duplicateCount, wasForwarded, name.toUri(), seg_name, type, waitTime, rtt);
      // nameTree->insert(name.toUri(), emaEntry->getCurrentSuppressionTime(), emaEntry->getMinimumSuppressionTime());
      if(type == 'i'){
        nameTree->insert(name.toUri(), emaEntry->getCurrentSuppressionTimeInterest());
      }
      else{
        nameTree->insert(name.toUri(), emaEntry->getCurrentSuppressionTimeData());
      }

      
    }
    // update existing record
    else
    {
      NFD_LOG_INFO("Updating EMA record for name: " << name << " type: " << type);
      it->second->getEMAExpiration().cancel();
      auto expirationId = getScheduler().schedule(MAX_MEASURMENT_INACTIVE_PERIOD, [=]  {
                                          if (vec->count(name) > 0)
                                              vec->erase(name);
                                              // set the value in the nametree = -1
                                          // if(type == 'i'){
                                          //   nameTree->insert(name.toUri(), it->second->getCurrentSuppressionTimeInterest());
                                          // }
                                          // else{
                                          //   nameTree->insert(name.toUri(), it->second->getCurrentSuppressionTimeData());  
                                          // } 


                                      });

      it->second->setEMAExpiration(expirationId);
      it->second->addUpdateEMA(duplicateCount, wasForwarded, name.toUri(), seg_name, type, waitTime, rtt);
      if(type == 'i'){
        nameTree->insert(name.toUri(), it->second->getCurrentSuppressionTimeInterest());
        auto suppressionTime = getDelayTimer(seg_name, type);

        NFD_LOG_INFO("Interest update EMA After setting the ema entry get the suppression time from nametree" << suppressionTime << " but the wait time is " << waitTime);
 
      }
      else{
        nameTree->insert(name.toUri(), it->second->getCurrentSuppressionTimeData());
        auto suppressionTime = getDelayTimer(seg_name, type);

        NFD_LOG_INFO("Data update EMA After setting the ema entry get the suppression time from nametree" << suppressionTime << " but the wait time is " << it->second->getCurrentSuppressionTimeData());
 
      }  
      
    }
}




time::milliseconds
MulticastSuppression::getDelayTimer(Name name, char type)
{
  NFD_LOG_INFO("Getting supperssion timer for name: " << name << " type " << type);
  // auto nameTree = getNameTree(type);
  auto nameTree = getNameTree(type);

 
  // nameTree->printAllRecords(name.getPrefix(-1).toUri());

  auto suppressionTimer = nameTree->getSuppressionTimer("/producer/sta1");
  NFD_LOG_INFO("Suppression timer for name: " << name << " and type: "<< type << " = " << suppressionTimer);
  return suppressionTimer;
}


void NameTree::printNameTreeSuppressionTime(NameTree* node, std::string currentPrefix = "") {
    if (node == nullptr) {
        return;
    }

    if (node->isLeaf) {
        // Print the current prefix and associated suppression time
        std::cout << "Prefix: " << currentPrefix << ", Suppression Time: " << node->suppressionTime << std::endl;
    }

    for (int i = 0; i < 26; i++) {
        char currentChar = 'a' + i;
        if (node->children[i]) {
            // Recursively traverse the child node with the updated prefix
            printNameTreeSuppressionTime(node->children[i], currentPrefix + currentChar);
        }
    }
}




} //namespace ams
} //namespace face
} //namespace nfd