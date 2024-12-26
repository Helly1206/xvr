# -*- coding: utf-8 -*-
#########################################################
# SERVICE : manager.py                                  #
#           Manager cameras, triggers and recordings    #
#                                                       #
#           I. Helwegen 2024                            #
#########################################################

####################### IMPORTS #########################
from threading import Thread, Lock, Event
import logging
from time import sleep
from datetime import datetime
import os
from common.common import common
from process.topics.topics import topics
from interface.detector import detector
from recorder.recorder import recorder
from process.wiper import wiper
from process.timeline import timeline

#########################################################

####################### GLOBALS #########################
RETRY_WAIT  = 600 # 600 x 100 ms = 60 s
CLEANUPTIME = datetime(1900,1,1,3,0,0,0).time() # 3:00, 0:00 doesn't work, 0:01 does

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : manager                                       #
#########################################################
class manager(Thread):
    def __init__(self, basename, camname, settings, general, cbget):
        self.logger = logging.getLogger('{}.manager [{}]'.format(basename, camname))
        self.camname = camname
        self.settings = settings
        self.general = general
        self.cbget = cbget
        self.detecting = False
        self.detectionStop = 0
        self.setPath()
        self.mutex = Lock()
        self.term = Event()
        self.term.clear()
        self.continuerec = common.getsetting(self.settings, "continuerec", False)
        self.topics = None
        self.enable = True
        self.record = False
        self.cleaned = False
        self.stream = recorder(basename, camname, self.settings, self.path, self.setRecording)
        self.detector = detector(basename, camname, self.settings, self.manageDetection)
        self.wiper = wiper(basename, camname, self.settings, self.path)
        self.timeline = timeline(basename, camname, self.settings, self.general, self.path)
        Thread.__init__(self)

    def __del__(self):
        if self.timeline:
            del self.timeline
        if self.wiper:
            del self.wiper
        if self.detector:
            del self.detector
        if self.stream:
            del self.stream
        if self.topics:
            del self.topics
        del self.term
        del self.mutex
        del self.logger

    def __repr__(self):
        if self.topics:
            return repr(self.topics)
        else:
            return "Unknown"

    def terminate(self):
        self.logger.info("terminating")
        self.term.set()
        if self.detector:
            self.detector.terminate()
            self.detector.join(5)

    def run(self):
        self.logger.info("running")
        self.loadTopics()
        self.detector.start()
        retry = 0
        if self.continuerec:
            if not self.stream.start():
                retry = RETRY_WAIT
                self.logger.error(f"Error starting recording, retry in {retry/10} s")
        maxfilesize = common.getsetting(self.settings, "maxfilesize", 3600)
        while not self.term.is_set():
            with self.mutex:
                self.manageDetectionStop()
                if self.stream.recording():
                    errcode = self.stream.poll()
                    if errcode != None: # recording process is stopped
                        self.logger.error(f"Recording exited with errorcode {errcode}")
                        if self.continuerec:
                            retry = RETRY_WAIT
                    elif self.stream.getData()["time_s"] > maxfilesize:
                        if not self.stream.restart():
                            retry = RETRY_WAIT
                            self.logger.error(f"Error restarting recording, retry in {retry/10} s")
                if retry:
                    retry -= 1
                    if retry == 0:
                        if not self.stream.start():
                            retry = RETRY_WAIT
                            self.logger.error(f"Error starting recording, retry in {retry/10} s")
                self.checkCleanup()
            sleep(0.1)
        self.stream.stop()

    def requestStatus(self, interface):
        with self.mutex:
            self.setValue("detected", self.detecting, interface)
            self.setValue("recording", self.stream.recording(), interface)
            self.setValue("enable", self.enable, interface)
            self.setValue("record", self.record, interface)
            self.setValue("detection", "none", interface)

    def getTopics(self):
        if self.topics:
            return self.topics.getTopics()
        return []

    def loadTopics(self):
        aliasSettings = common.getsetting(self.settings, "alias")
        self.topics = topics("xvr", "1", aliasSettings)

    def publish(self, key, value):
        result = False
        topic = key
        if self.topics:
            topic = self.topics.getTopic(key)
        # {“pub”: {"topic": true}}
        if topic:
            if topic == "enable":
                result = self.setEnable(value)
            elif topic == "record":
                result = self.setRecord(value)
        return result
    
    def setEnable(self, enable): # enable --> self.enable
        with self.mutex:
            if common.getsetting(self.settings, "extenable", False):
                self.enable = enable
            else:
                self.enable = True
            self.setValue("enable", self.enable)
        return True
    
    def setRecord(self, record): # record --> self.record
        result = True
        self.record = False
        if common.getsetting(self.settings, "extrecord", False):
            result = self.manageDetection("record", record)
            if result:
                self.record = record
        self.setValue("record", self.record)
        return result

    def manageRecording(self, record): #no mutex as only called from within mutex
        if not common.getsetting(self.settings, "continuerec", False):
            if record:
                if self.stream.recording(): # already recording, clear delayed stop
                    if self.enable:
                        self.stream.delayedStop(0)
                else: # start new recording
                    if self.enable:
                        self.stream.start()
            else: #(delayed) stop
                recordpost = common.getsetting(self.settings, "recordpost", 0)
                if recordpost > 0:
                    self.stream.delayedStop(recordpost)
                else:
                    self.stream.stop
        return True

    # check code for detection parcel, doorbell - doesn't seem to work yet, keep with motion for now
    def manageDetection(self, topicType, detect):
        with self.mutex:
            if self.enable: # detection enabled
                if detect: # detection started
                    self.detectionStop = 0
                    self.manageRecording(True)
                    if self.detecting: # still detecting
                        self.setDetectionType(topicType)
                    else: # new detection
                        self.detecting = True
                        self.timeline.start(topicType, self.stream.getData())
                        self.setDetected(True)
                        self.setValue("detection", topicType)
                else: #detection finished
                    if self.detecting:
                        self.detectionStop = datetime.now().timestamp() + common.getsetting(self.settings, "detectpost", 5)
            elif self.detecting: # not enabled anymore but ongoing detection
                self.detectionStop = datetime.now().timestamp() + common.getsetting(self.settings, "detectpost", 5)                
        return True

    def manageDetectionStop(self):
        if self.detecting and self.detectionStop > 0:
            if datetime.now().timestamp() > self.detectionStop:
                self.timeline.stop(self.detectionStop)
                self.detectionStop = 0
                self.detecting = False
                self.setValue("detection", "none")
                self.setDetected(False)
                self.manageRecording(False)
                
    def setDetectionType(self, topicType): # more dependencies can be set here later
        if topicType != "motion":
            self.setValue("detection", topicType)
            self.timeline.updateType(topicType)

    def setDetected(self, isDetected):
        self.setValue("detected", isDetected)

    def setRecording(self, isRecording):
        self.setValue("recording", isRecording)

    def setValue(self, key, value, interface = 0):
        if self.cbget:
            try:
                alias = key
                if self.topics:
                    alias = self.topics.getAlias(key)
                self.cbget(self.camname, alias, value, interface)
            except:
                pass

    def checkCleanup(self):
        now = datetime.now().time()
        if self.cleaned and now < CLEANUPTIME:
            self.cleaned = False
        elif not self.cleaned and now >= CLEANUPTIME:
            self.wiper.cleanup()
            self.timeline.cleanup()
            self.cleaned = True

    def setPath(self):
        self.path = os.path.abspath(os.path.join(common.getsetting(self.general, "videofolder", "."),self.camname))
        if os.path.exists(self.path):
            if not os.access(self.path, os.W_OK):
                self.logger.error("Video path cannot be written, default to ~")
                self.path = os.path.join(os.path.expanduser("~"),self.camname)
                if not os.path.exists(self.path):
                    try:
                        os.makedirs(self.path)
                    except:
                        self.logger.error("Cannot create videopath on ~, no files will be written")
                        self.path = None
        else:
            try:
                os.makedirs(self.path)
            except:
                self.logger.error("Cannot create videopath on {}, no files will be written".format(common.getsetting(self.general, "videofolder", ".")))
                self.path = None

######################### MAIN ##########################
if __name__ == "__main__":
    pass
