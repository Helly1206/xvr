# -*- coding: utf-8 -*-
#########################################################
# SERVICE : detector.py                                 #
#           detect motion via ONVIF interface           #
#                                                       #
#           I. Helwegen 2024                            #
#########################################################

####################### IMPORTS #########################
import asyncio
from datetime import timedelta
import logging
import onvif
import os.path
from threading import Thread, Event
import time
from common.common import common
#########################################################

####################### GLOBALS #########################
SUBSCRIPTION_TIME = timedelta(minutes=1)
WAIT_TIME = timedelta(seconds=1)

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : detector                                      #
#########################################################
class detector(Thread):
    def __init__(self, basename, camname, settings, callback = None, loglevel = logging.CRITICAL):
        self.logger = logging.getLogger('{}.detector [{}]'.format(basename, camname))
        self.detect = {"motion": False, "pet": False, "vehicle": False, "person": False}
        self.settings = settings
        self.callback = callback
        logging.getLogger("zeep").setLevel(loglevel)
        logging.getLogger("httpx").setLevel(loglevel)
        self.term = Event()
        self.term.clear()
        self.retries = 0
        Thread.__init__(self)
        
    def __del__(self):
        del self.term
        del self.logger

    def subscription_lost(self):
        self.logger.info("subscription lost")
        self.retries += 1
        
    def parseTopicMessage(self, nm):
        tp = nm["Topic"]["_value_1"].split(":")
        if len(tp) > 1:
            ns = tp[0]
            topic = tp[1]
        else:
            topic = tp[0]
            ns = ""
        mes = nm["Message"]["_value_1"]
        return topic, mes, ns
        
    def getTopicType(self, topic):
        topictype = None
        if topic == "RuleEngine/CellMotionDetector/Motion" or topic == "RuleEngine/MotionRegionDetector/Motion":
            topictype = "motion"
        elif topic == "RuleEngine/MyRuleDetector/DogCatDetect":
            topictype = "pet"
        elif topic == "RuleEngine/MyRuleDetector/VehicleDetect":
            topictype = "vehicle"
        elif topic == "RuleEngine/MyRuleDetector/PeopleDetect" or topic == "RuleEngine/TPSmartEventDetector/TPSmartEvent" or topic == "RuleEngine/PeopleDetector/People":
            topictype = "person"
        return topictype
        
    def checkvalue(self, topictype, mes):
        changed = False
        if topictype:
            value = mes.Data.SimpleItem[0].Value == "true"
            if self.detect[topictype] != value:
                changed = True
                self.detect[topictype] = value
        return changed
    
        
    def parse(self, messages):
        if 'NotificationMessage' in messages:
            for nm in messages['NotificationMessage']:
                topic, mes, ns = self.parseTopicMessage(nm)
                topictype = self.getTopicType(topic)
                if self.checkvalue(topictype, mes):
                    if self.callback:
                        types = common.getsetting(self.settings, "onviftype", [])
                        if topictype in types:
                            self.callback(topictype, self.detect[topictype])
                    self.logger.debug(f"{topictype}: {self.detect[topictype]}")
        
    """
    tns1:RuleEngine/CellMotionDetector/Motion
    tns1:RuleEngine/MotionRegionDetector/Motion
    tns1:RuleEngine/MyRuleDetector/DogCatDetect
    tns1:RuleEngine/MyRuleDetector/VehicleDetect
    tns1:RuleEngine/PeopleDetector/People or tns1:RuleEngine/TPSmartEventDetector/TPSmartEvent
        or tns1:RuleEngine/MyRuleDetector/PeopleDetect
    {
        'CurrentTime': datetime.datetime(2024, 12, 7, 8, 57, 21, tzinfo=datetime.timezone.utc),
        'TerminationTime': datetime.datetime(2024, 12, 7, 8, 58, 7, tzinfo=datetime.timezone.utc),
        'NotificationMessage': [
            {
                'SubscriptionReference': {
                    'Address': {
                        '_value_1': None,
                        '_attr_1': None
                    },
                    'ReferenceParameters': None,
                    'Metadata': None,
                    '_value_1': None,
                    '_attr_1': None
                },
                'Topic': {
                    '_value_1': 'tns1:RuleEngine/CellMotionDetector/Motion',
                    'Dialect': 'http://www.onvif.org/ver10/tev/topicExpression/ConcreteSet',
                    '_attr_1': {
                }
                },
                'ProducerReference': None,
                'Message': {
                    '_value_1': {
                        'Source': {
                            'SimpleItem': [
                                {
                                    'Name': 'VideoSourceConfigurationToken',
                                    'Value': 'vsconf'
                                },
                                {
                                    'Name': 'VideoAnalyticsConfigurationToken',
                                    'Value': 'VideoAnalyticsToken'
                                },
                                {
                                    'Name': 'Rule',
                                    'Value': 'MyMotionDetectorRule'
                                }
                            ],
                            'ElementItem': [],
                            'Extension': None,
                            '_attr_1': None
                        },
                        'Key': None,
                        'Data': {
                            'SimpleItem': [
                                {
                                    'Name': 'IsMotion',
                                    'Value': 'true'
                                }
                            ],
                            'ElementItem': [],
                            'Extension': None,
                            '_attr_1': None
                        },
                        'Extension': None,
                        'UtcTime': datetime.datetime(2024, 12, 7, 8, 57, 21, tzinfo=datetime.timezone.utc),
                        'PropertyOperation': 'Changed',
                        '_attr_1': {
                    }
                    }
                }
            }
        ]
    }


    """

    async def events(self):
        try:
            mycam = onvif.ONVIFCamera(common.getsetting(self.settings, "host"), 
                                      common.getsetting(self.settings, "onvifport", 2020), 
                                      common.getsetting(self.settings, "username"), 
                                      common.getsetting(self.settings, "password"), 
                                      wsdl_dir=f"{os.path.dirname(onvif.__file__)}/wsdl/")
            await mycam.update_xaddrs()
        except:
            self.retries += 1
            if self.retries == 1:
                self.logger.error("Cannot connect to camera")
            return
        
        try:
            manager = await mycam.create_pullpoint_manager(SUBSCRIPTION_TIME, self.subscription_lost)
            await manager.set_synchronization_point()
        
            pullpoint = manager.get_service()
        except:
            self.retries += 1
            if self.retries == 1:
                self.logger.error("Cannot create pullpoint")
            return
            
        self.logger.info("listening")
        self.retries = 0
        while (not self.term.is_set()) and (not self.retries):
            try:
                messages = await pullpoint.PullMessages({"MessageLimit": 100, "Timeout": WAIT_TIME})
                self.parse(messages)
            except:
                self.retries += 1
                if self.retries == 1:
                    self.logger.error("Cannot retrieve (pull) messages")

        self.logger.info("shutdown")
        try:
            await manager.shutdown()
        except:
            pass
        try:
            await mycam.close()
        except: 
            pass
        
    def run(self):
        if not common.getsetting(self.settings, "onvifdetect", True):
            self.logger.debug("No detection as onvifdetect is not enabled")
            return
        loop = asyncio.new_event_loop()
        while not self.term.is_set():
            if self.retries > 10:
                time.sleep(1)
            loop.run_until_complete(self.events())
        
    def terminate(self):
        self.term.set()
#########################################################
          
######################### MAIN ##########################
if __name__ == "__main__":
    pass
