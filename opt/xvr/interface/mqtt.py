# -*- coding: utf-8 -*-
#########################################################
# SERVICE : mqtt.py                                     #
#           Handles communication and protocol with     #
#           MQTT                                        #
#           I. Helwegen 2024                            #
#########################################################

####################### IMPORTS #########################
from json import dumps
import logging
from common.common import common
import paho.mqtt.client as mqttclient
from threading import Lock
#########################################################

####################### GLOBALS #########################
RETAIN           = True
RETAINEVENT      = False ##################################
QOS              = 0
HASTATUS         = "status"
HAONLINE         = "online"
CONFIG           = "config"
DEFAULTPORT      = 1883
DEFAULTHAENABLED = False
DEFAULTHATOPIC   = "homeassistant"
MANUFACTURER     = "IOTControl"
CONNECTIONRETRY  = 5 

#########################################################

###################### FUNCTIONS ########################

#########################################################

# main topic: myhome/device/subtopic settings["maintopic"]
# Subscribe to: myhome/garden/gardenlights
# publish: myhome/garden/gardenlights_status, myhome/garden/btngardenlights_status
# [maintopic]/[device]/get all aliases per device


#########################################################
# Class : mqtt                                          #
#########################################################
class mqtt(object):
    def __init__(self, base, basename, settings):
        self.logger       = logging.getLogger('{}.mqtt'.format(basename))
        self.enabled      = common.getsetting(settings, "enable", False)
        self.settings     = settings
        self.base         = base
        self.connected    = False
        self.rcConnect    = 0
        self.rcDisconnect = 0
        self.client       = None
        self.topics       = {}
        self.mutex = Lock()
        if self.enabled: 
            myUuid = common.getUuid(-6)
            try:
                self.client = mqttclient.Client(mqttclient.CallbackAPIVersion.VERSION1, "IOTUSB_" + myUuid)  #create new instance
            except: # version < 2
                self.client = mqttclient.Client("IOTUSB_" + myUuid)  #create new instance
            self.client.on_message = self._onmessage #attach function to callback
            self.client.on_connect = self._onconnect  #bind call back function
            self.client.on_disconnect = self._ondisconnect  #bind call back function
            self.client.on_log = self._onlog
        else:
            self.client = None

    def __del__(self):
        del self.mutex
        if self.client:
            del self.client
        del self.topics
        del self.logger

    def terminate(self):
        if self.enabled and self.client:
            self.logger.info("terminating")
            #self.client.wait_for_publish() # wait for all messages published
            self.client.loop_stop()    #Stop loop
            self.client.disconnect() # disconnect

    def connect(self, retry = 1):
        if retry > 0: # else already connected
            retry -= 1
            if self.enabled and self.client:
                if retry == 0:
                    try:
                        self.logger.info("running")
                        if common.getsetting(self.settings, "username"):
                            self.client.username_pw_set(common.getsetting(self.settings, "username"), common.getsetting(self.settings, "password"))
                        try:
                            self.client.connect(common.getsetting(self.settings, "broker"), port=common.getsetting(self.settings, "port", DEFAULTPORT)) #connect to broker
                            self.client.loop_start() #start the loop
                        except:
                            self.logger.error("Invalid connection, check server address")
                            retry = CONNECTIONRETRY # retry in 5 seconds
                    except Exception as e:
                        self.logger.exception(e)
                        retry = 0 # no retry, code error
        elif not self.connected:
            retry = CONNECTIONRETRY
        return retry

    def add(self, devname, topics):
        with self.mutex:
            self.topics[devname] = topics
            if self.connected:
                self.subscribeTopics(devname, topics)
                self.publishDiscoTopics(devname, topics)

    def loadDiscoTopics(self):
        with self.mutex:
            for devname, topics in self.topics.items():
                self.publishDiscoTopics(devname, topics)

    def loadSubTopics(self):
        with self.mutex:
            for devname, topics in self.topics.items():
                self.subscribeTopics(devname, topics)

    def publishDiscoTopics(self, devname, topics):
        hatopic = common.getsetting(self.settings, "hatopic")
        if self.enabled and self.client and hatopic:
            ids = common.doHash(devname)
            dev = {}
            dev["name"] = devname
            dev["mf"] = MANUFACTURER
            dev["mdl"] = self.base.loadModel(devname)
            dev["ids"] = [ ids ]
            for topic in topics:
                discotopic = self.buildDiscoTopic(devname, topic, hatopic)
                disco = dumps(self.buildDisco(devname, topic, ids, dev))
                self.client.publish(discotopic, disco, QOS, RETAIN)
                self.logger.debug("MQTT: HA Discovery [" + discotopic + "]: " + disco) 
    
    def setValue(self, devname, tag, value, evt = False):
        if evt:
            retain = False
        else:
            retain = common.getsetting(self.settings, "retain", RETAIN)
        maintopic = self.buildTopic(common.getsetting(self.settings, "maintopic", "iotusb"), devname)
        self.publish(self.buildTopic(maintopic, tag), common.convnumber(value), retain)
    
    def _onlog(self, client, userdata, level, buf):
        self.logger.debug(buf)

    def _onmessage(self, client, userdata, message):
        hatopic = common.getsetting(self.settings, "hatopic")
        if hatopic and self.buildTopic(hatopic, HASTATUS) == message.topic:
            if message.payload.decode('utf-8') == HAONLINE:
                self.logger.debug("MQTT: received HA online, issue HA Discovery")
                self.loadDiscoTopics()
                self.base.onlineEvent()
                return
        self.base.set(self.getDevname(message.topic), self.getTag(message.topic), common.gettype(message.payload.decode('utf-8')))

    def _onconnect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info("Connected OK, Returned code = " + str(rc))
            self.connected = True
            self.rcDisconnect = 0
        else:
            if self.rcConnect != rc:
                self.logger.info("Bad connection, Returned code = " + str(rc))
            self.connected = False
        self.rcConnect = rc

        if self.connected:
            ####### Subscribe hatopic
            hatopic = common.getsetting(self.settings, "hatopic")
            if hatopic:
                self.client.subscribe(self.buildTopic(hatopic, HASTATUS), QOS)            
            self.loadSubTopics()
            self.loadDiscoTopics()
            self.base.requestStatus(self.base.MQTT)
            self.base.onlineEvent()

    def _ondisconnect(self, client, userdata, rc):
        if rc == 0 or self.rcDisconnect != rc:
            self.logger.info("Disconnected, Returned code = " + str(rc))
            self.rcConnect = 0
        self.connected = False
        self.rcDisconnect = rc

    def publish(self, pubTopic, value, retain = RETAIN):
        if self.enabled and self.client:
            qos = common.getsetting(self.settings, "qos", 0)
            if pubTopic:
                self.client.publish(pubTopic, value, qos, retain)

    ###########################################################################################

    def subscribeTopics(self, devname, topics):
        if self.enabled and self.client:
            qos = common.getsetting(self.settings, "qos", 0)
            maintopic = self.buildTopic(common.getsetting(self.settings, "maintopic", "iotusb"), devname)
            for topic in topics:
                if topic["cmd_t"]:
                    subTopic = self.buildTopic(maintopic, topic["cmd_t"])
                    self.client.subscribe(subTopic, qos)

    def buildDiscoTopic(self, devname, topic, hatopic):
        if topic["dev_cla"]:
            dev_cla = topic["dev_cla"]
        else:
            dev_cla = topic["type"]
        return self.buildTopic(self.buildTopic(self.buildTopic(hatopic,topic["type"]), devname + "_" + topic["name"] + "_" + dev_cla), CONFIG)

    def buildDisco(self, devname, topic, ids, dev):
        disco = {}
        disco["name"] = topic["name"]
        disco["~"] = self.buildTopic(common.getsetting(self.settings, "maintopic", "iotusb"), devname)
        main_t = "~"
        disco["uniq_id"] = ids + "_" + topic["name"]
        if topic["cmd_t"]:
           disco["cmd_t"] = self.buildTopic(main_t, topic["cmd_t"])
        if topic["stat_t"]:
           disco["stat_t"] = self.buildTopic(main_t, topic["stat_t"]) 
        if topic["type"] == "binary_sensor" or topic["type"] == "switch":
            disco["pl_on"] = "1"
            disco["pl_off"] = "0"
        elif topic["type"] == "event":
            disco["event_types"] = ["1", "0"]
        elif topic["type"] == "button":
            disco["pl_prs"] = "1"
        if topic["dev_cla"]:
            disco["dev_cla"] = topic["dev_cla"]
        # no payload for number or sensor
        disco["dev"] = dev
        return disco
                
    def buildTopic(self, maintopic, subtopic):
        topic = ""
        if maintopic:
            if maintopic.startswith("/"):
                topic = maintopic[1:]
            else:
                topic = maintopic
            if topic.endswith("/"):
                topic = topic[0:-1]
        if subtopic:
            if not subtopic.startswith("/"):
                topic += "/"
            topic += subtopic
            if topic.endswith("/"):
                topic = topic[0:-1]
        return topic
    
    def getDevname(self, topic):
        retval = ""
        slash1 = topic.find("/")
        if slash1 > -1:
            slash2 = topic.find("/", slash1+1)
        else:
            slash2 = -1
        if slash1 > -1 and slash2 > -1:
            retval = topic[slash1+1:slash2]
        return retval

    def getTag(self, topic):
        retval = ""
        slash1 = topic.find("/")
        if slash1 > -1:
            slash2 = topic.find("/", slash1+1)
        else:
            slash2 = -1
        if slash2 > -1:
            retval = topic[slash2+1:]
        return retval