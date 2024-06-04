/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2014-2022,  Regents of the University of California,
 *                           Arizona Board of Regents,
 *                           Colorado State University,
 *                           University Pierre & Marie Curie, Sorbonne University,
 *                           Washington University in St. Louis,
 *                           Beijing Institute of Technology,
 *                           The University of Memphis.
 *
 * This file is part of NFD (Named Data Networking Forwarding Daemon).
 * See AUTHORS.md for complete list of NFD authors and contributors.
 *
 * NFD is free software: you can redistribute it and/or modify it under the terms
 * of the GNU General Public License as published by the Free Software Foundation,
 * either version 3 of the License, or (at your option) any later version.
 *
 * NFD is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
 * without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
 * PURPOSE.  See the GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along with
 * NFD, e.g., in COPYING.md file.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "link-service.hpp"
#include "face.hpp"
#include <thread>

namespace nfd::face {

NFD_LOG_INIT(LinkService);

LinkService::~LinkService() = default;

void
LinkService::setFaceAndTransport(Face& face, Transport& transport) noexcept
{
  BOOST_ASSERT(m_face == nullptr);
  BOOST_ASSERT(m_transport == nullptr);

  m_face = &face;
  m_transport = &transport;
}

void
LinkService::sendInterest(const Interest& interest)
{
  NFD_LOG_INFO("****************** SendInterest Function called ********************" << this->getFace()->getLinkType() << " interest name " << interest.getName());
  BOOST_ASSERT(m_transport != nullptr);
  NFD_LOG_FACE_TRACE(__func__);

  if (this->getFace()->getLinkType() != ndn::nfd::LINK_TYPE_MULTI_ACCESS)
  {
    NFD_LOG_INFO("Interest Counter increased not LINK_TYPE_MULTI_ACCESS");
    ++this->nOutInterests;
    doSendInterest(interest);
    NFD_LOG_INFO("Average packet count interest outgoing " << nOutInterests);
    return;
  }
  // apply suppression algorithm if sending through multicast face
  // check if the interest is already in flight
  if (m_multicastSuppression.interestInflight(interest)) {
    NFD_LOG_INFO ("Interest drop, Interest " <<  interest.getName() << " is in flight, drop the forwarding");
    return; // need to catch this, what should be the behaviour after dropping the interest?? 
  }
  // wait for suppression time before forwarding
  // check if another interest is overheard during the wait, if heard, cancle the forwarding
  auto entry_name = interest.getName();
  // nm.printNameTreeSuppressionTime(entry_name.getPrefix(-1).toUri());
  entry_name.appendNumber(0);
  
  auto suppressionTime = m_multicastSuppression.getDelayTimer(interest.getName(), 'i');
  NFD_LOG_INFO ("Interest " <<  interest.getName() << " not in flight, waiting" << suppressionTime << "before forwarding");

  NFD_LOG_INFO("Interest Counter increased  LINK_TYPE_MULTI_ACCESS");
  auto eventId = getScheduler().schedule(suppressionTime, [this, interest, entry_name, suppressionTime] {
    ++this->nOutInterests;
    doSendInterest(interest);
    NFD_LOG_INFO("Wait time " << suppressionTime  << "Analysis History Interest sent finally: " << interest.getName());
    NFD_LOG_INFO("Average packet count interest outgoing " << nOutInterests);
    m_multicastSuppression.recordInterest(interest, true, suppressionTime);
    // m_mutlicastSuppression.insertAnalysisHistory(interest, suppressionTime);

    if (m_scheduledEntry.count(entry_name) > 0)
      m_scheduledEntry.erase(entry_name);
  });

  NFD_LOG_INFO("Event Id " << eventId << " for " << entry_name);
  m_scheduledEntry.emplace(entry_name, eventId);
}





// void
// LinkService::sendInterest(const Interest& interest)
// {
//   NFD_LOG_INFO("****************** SendInterest Function called ********************" << this->getFace()->getLinkType());
//   BOOST_ASSERT(m_transport != nullptr);
//   NFD_LOG_FACE_TRACE(__func__);

//   if (this->getFace()->getLinkType() != ndn::nfd::LINK_TYPE_MULTI_ACCESS)
//   {
//     NFD_LOG_INFO("Interest Counter increased not LINK_TYPE_MULTI_ACCESS");
//     ++this->nOutInterests;
//     doSendInterest(interest);
//     NFD_LOG_INFO("Average packet count interest outgoing " << nOutInterests);
//     return;
//   }
//   // apply suppression algorithm if sending through multicast face
//   // check if the interest is already in flight
//   if (m_multicastSuppression.interestInflight(interest)) {
//     NFD_LOG_INFO ("Interest drop, Interest " <<  interest.getName() << " is in flight, drop the forwarding");
//     return; // need to catch this, what should be the behaviour after dropping the interest?? 
//   }
//   // wait for suppression time before forwarding
//   // check if another interest is overheard during the wait, if heard, cancle the forwarding
//   auto entry_name = interest.getName();
//   // nm.printNameTreeSuppressionTime(entry_name.getPrefix(-1).toUri());
//   entry_name.appendNumber(0);
  
//   auto suppressionTime = m_multicastSuppression.getDelayTimer(interest.getName(), 'i');
//   NFD_LOG_INFO ("Interest " <<  interest.getName() << " not in flight, waiting" << suppressionTime << "before forwarding");

//   NFD_LOG_INFO("Interest Counter increased  LINK_TYPE_MULTI_ACCESS");
//   auto eventId = getScheduler().schedule(suppressionTime, [this, interest, entry_name, suppressionTime] {
//     ++this->nOutInterests;
//     doSendInterest(interest);
//     NFD_LOG_INFO("Wait time " << suppressionTime  << "Analysis History Interest sent finally: " << interest.getName());
//     NFD_LOG_INFO("Average packet count interest outgoing " << nOutInterests);
//     m_multicastSuppression.recordInterest(interest, true, suppressionTime);
//     // m_mutlicastSuppression.insertAnalysisHistory(interest, suppressionTime);

//     if (m_scheduledEntry.count(entry_name) > 0)
//       m_scheduledEntry.erase(entry_name);
//   });

//   NFD_LOG_INFO("Event Id " << eventId << " for " << entry_name);
//   m_scheduledEntry.emplace(entry_name, eventId);
// }

void
LinkService::sendData(const Data& data)
{
  NFD_LOG_INFO("****************** SendData Function called ********************" << data.getName());
  BOOST_ASSERT(m_transport != nullptr);
  NFD_LOG_FACE_TRACE(__func__);
  if (this->getFace()->getLinkType() != ndn::nfd::LINK_TYPE_MULTI_ACCESS)
  {
    ++this->nOutData;
    doSendData(data);
    NFD_LOG_DEBUG("Returning back from egress");
    NFD_LOG_INFO("Average packet count data outgoing " << nOutData);
    return;
  }
  auto suppressionTime = m_multicastSuppression.getDelayTimer(data.getName(), 'd');
  auto entry_name = data.getName();
  entry_name.appendNumber(1);
  NFD_LOG_INFO ("Data " <<  data.getName() << " not in flight, waiting " << suppressionTime << " ms before forwarding");

  
  NFD_LOG_INFO("The scheduler is called for the entry name " << entry_name);
  auto eventId = getScheduler().schedule(suppressionTime, [this, data, entry_name, suppressionTime] {

    ++this->nOutData;
    doSendData(data);
    NFD_LOG_INFO("Wait Time for " << suppressionTime << " Analysis History Data sent finally:" << data.getName());
    NFD_LOG_INFO("Average packet count data outgoing " << nOutData);
    m_multicastSuppression.recordData(data, true, suppressionTime);
    if(m_scheduledEntry.count(entry_name) > 0)
        m_scheduledEntry.erase(entry_name);

  });
  m_scheduledEntry.emplace(entry_name, eventId);
}

void
LinkService::sendNack(const ndn::lp::Nack& nack)
{
  NFD_LOG_INFO("****************** sendNack Function called ********************");
  BOOST_ASSERT(m_transport != nullptr);
  NFD_LOG_FACE_TRACE(__func__);

  ++this->nOutNacks;

  doSendNack(nack);
}

bool
LinkService::cancelIfSchdeuled(Name name, int type)
{
  NFD_LOG_INFO("****************** cancelIfScheduled Function called ********************" << name);
  auto entry_name = name.appendNumber(type);
  auto it = m_scheduledEntry.find(entry_name);
  if (it != m_scheduledEntry.end()) {
    it->second.cancel();
    m_scheduledEntry.erase(entry_name);
    return true;
  }
  return false;
}

void
LinkService::receiveInterest(const Interest& interest, const EndpointId& endpoint)
{
  NFD_LOG_INFO("****************** receiveInterest Function called ********************" << this->getFace()->getLinkType() << " interest name " << interest.getName());
  NFD_LOG_FACE_TRACE(__func__);
  // record multicast interest
  if (this->getFace()->getLinkType() == ndn::nfd::LINK_TYPE_MULTI_ACCESS)
  {
    NFD_LOG_INFO("!!!!!!!!!!!!!!!!! Interest Starts from here !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!");
    NFD_LOG_INFO("Multicast interest received: " << interest.getName());
    // check if a same interest is scheduled, if so drop it
    if (cancelIfSchdeuled(interest.getName(), 0)) // checks whether the packet is in measurement table and drops if its already there
      NDN_LOG_INFO("Interest drop by suppression, with name " << interest.getName() << " overheard, duplicate forwarding dropped");
    auto suppressionTime = m_multicastSuppression.getDelayTimer(interest.getName(), 'i');
    m_multicastSuppression.recordInterest(interest, false, suppressionTime);
  }
  ++this->nInInterests;
  NFD_LOG_INFO("Average packet count interest outgoing " << nInInterests);
  afterReceiveInterest(interest, endpoint);
}

void
LinkService::receiveData(const Data& data, const EndpointId& endpoint)
{
  NFD_LOG_INFO("****************** receiveData Function called ********************" << data.getName());
  NFD_LOG_FACE_TRACE(__func__);
  // record multicast Data received
  if (this->getFace()->getLinkType() == ndn::nfd::LINK_TYPE_MULTI_ACCESS)
  {
    NFD_LOG_INFO("Multicast data received: " << data.getName());
    if (cancelIfSchdeuled(data.getName(), 1))
      NDN_LOG_INFO("Data drop by suppression, with name " << data.getName() << " overheard, duplicate forwarding dropped");

    if (cancelIfSchdeuled(data.getName(), 0)) // also can drop interest if shceduled for this data
      NDN_LOG_INFO("Interest drop by suppression, with name " << data.getName() << " overheard, drop the corresponding scheduled interest"); 
    auto suppressionTime = m_multicastSuppression.getDelayTimer(data.getName(), 'd');
    m_multicastSuppression.recordData(data, false, suppressionTime);
  }

  ++this->nInData;
  NFD_LOG_INFO("Average packet count data incoming " << nInData);
  // record multicast data
  afterReceiveData(data, endpoint);
}

void
LinkService::receiveNack(const ndn::lp::Nack& nack, const EndpointId& endpoint)
{
  NFD_LOG_INFO("****************** receiveNack Function called ********************");
  NFD_LOG_FACE_TRACE(__func__);

  ++this->nInNacks;

  afterReceiveNack(nack, endpoint);
}

void
LinkService::notifyDroppedInterest(const Interest& interest)
{
  NFD_LOG_INFO("****************** notifyDroppedInterest Function called ********************");
  ++this->nInterestsExceededRetx;
  onDroppedInterest(interest);
}

std::ostream&
operator<<(std::ostream& os, const FaceLogHelper<LinkService>& flh)
{
  const Face* face = flh.obj.getFace();
  if (face == nullptr) {
    os << "[id=0,local=unknown,remote=unknown] ";
  }
  else {
    os << "[id=" << face->getId() << ",local=" << face->getLocalUri()
       << ",remote=" << face->getRemoteUri() << "] ";
  }
  return os;
}

} // namespace nfd::face
