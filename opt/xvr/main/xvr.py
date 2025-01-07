#!/usr/bin/python3

# -*- coding: utf-8 -*-
#########################################################
# SCRIPT : xvr.py                                       #
#          Xtended (Network) Video Recorder             #
#          Simple network video recorder                #
#          I. Helwegen 2024                             #
#########################################################

####################### IMPORTS #########################
import os
import sys
from threading import Event
from time import sleep
import signal
import logging
import logging.handlers
import locale
from common.common import common
from process.manager import manager
import yaml
from interface.restapi import restapi
from interface.mqtt import mqtt
from process.topics.topics import topics

#########################################################

####################### GLOBALS #########################

APP_NAME = "xvr"
VERSION = "0.8.1"
YML_FILENAME = "xvr.yml" #"/etc/xvr.yml"
LOG_FILENAME = "xvr.log"
DOCKER_BASE = "/data"
DOCKER_CFG = "config"
GENERAL_CFG = "." #"/etc"
DOCKER_LOG = "log"
GENERAL_LOG = "." #"/var/log"
DOCKER_CAMERAS = "/cameras"
DOCKER_RESTAPIPORT = 8081
DEFAULT_YML = "./xvr_default.yml"
LOG_MAXSIZE  = 100*1024*1024

#########################################################

###################### FUNCTIONS ########################

#########################################################
# Class : xvr                                           #
#########################################################

class xvr(object):
    ALL = 0
    MQTT = 1
    RESTAPI = 2

    def __init__(self, docker = False):
        self.settings = {}
        self.cameras = {}
        self.mqtt = None
        self.restapi = None
        self.term = Event()
        self.term.clear()
        self.loglevel = logging.DEBUG
        self.docker = docker
        self.logger = logging.getLogger(APP_NAME)
        self.logger.setLevel(self.loglevel)
        self.exitval = 0
        fh = logging.handlers.RotatingFileHandler(self.GetLogger(), maxBytes=LOG_MAXSIZE, backupCount=5)
        ch = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        logging.captureWarnings(True)
        tmformat=("{} {}".format(locale.nl_langinfo(locale.D_FMT),locale.nl_langinfo(locale.T_FMT)))
        tmformat=tmformat.replace("%y", "%Y")
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s', tmformat)
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        self.logger.info("{} app, version {}".format(APP_NAME, VERSION))

    def __del__(self):
        del self.term
        del self.cameras
        del self.settings
        del self.logger

    def run(self, argv):
        signal.signal(signal.SIGINT, self.exit_app)
        signal.signal(signal.SIGTERM, self.exit_app)
        self.handleArgs(argv)
        self.setlogger()
        
        for camname, data in common.getsetting(self.settings, "cameras", {}).items():
            self.cameras[camname] = manager(APP_NAME, camname, data, common.getsetting(self.settings, "general", {}), self.getcb)
            self.cameras[camname].start()
        devices = list(self.cameras.keys())
        devices.append("general")
        self.restapi=restapi(self, APP_NAME, common.getsetting(self.settings, "restapi"), devices)
        self.restapi.start()
        self.getcb("general", "online", True)
        self.mqtt=mqtt(self, APP_NAME, common.getsetting(self.settings, "mqtt"))
        retry = self.mqtt.connect()
        retry = self.addTopics(retry)

        while not self.term.is_set():
            sleep(1)
            retry = self.mqtt.connect(retry) # reconnect if connection failed the first time
            retry = self.addTopics(retry)

        self.getcb("general", "online", False)

        for camname in self.cameras.keys():
            if self.cameras[camname]:
                self.cameras[camname].terminate()
                self.cameras[camname].join(5)
        
        if self.mqtt != None:
            self.mqtt.terminate()
        if self.restapi != None:
            self.restapi.terminate()
            self.restapi.join(5)
        
        self.logger.handlers.clear()
        return self.exitval
        
    def getcb(self, camname, key, value, interface = 0):
        self.logger.debug("<" + camname + ": " + key + " = " + str(value))
        if interface != self.MQTT:
            if self.restapi != None:
                self.restapi.setValue(camname, key, value)
        if interface != self.RESTAPI:
            if self.mqtt != None:
                self.mqtt.setValue(camname, key, value)

    def requestStatus(self, interface): #use interface to send data to correct interface
        for camname in self.cameras.keys():
            self.cameras[camname].requestStatus(interface)

    def addTopics(self, retry): # for mqtt
        if retry == 0:
            retry -= 1
            for camname in self.cameras.keys():
                self.mqtt.add(camname, self.cameras[camname].getTopics())
            self.mqtt.add("general", topics("general", "1", {"st_suffix": ""}).getTopics())
            self.getcb("general", "online", False)
        elif retry > -5:
            retry -= 1
            if retry == -5:
                self.getcb("general", "online", True)
        return retry
    
    def loadModel(self, camname):
        if camname == "general":
            return "xvr"
        else:
            return repr(self.cameras[camname])
    
    def set(self, camname, key, value):
        retval = None
        self.logger.debug(">" + camname + ": " + key + " = " + str(value))
        try:
            if camname == "general":
                if key == "restart" and int(value) == 1:
                    self.exitval = int(value)
                    self.term.set()
                    retval = value
            elif self.cameras[camname].publish(key, value):
                retval = value
        except:
            pass
        return retval
        
    def GetLogger(self):
        if self.docker:
            logpath = os.path.join(DOCKER_BASE, DOCKER_LOG)
        else:
            logpath = GENERAL_LOG
        LoggerPath = ""
        # first look in log path
        if os.path.exists(logpath):
            if os.access(logpath, os.W_OK):
                LoggerPath = os.path.join(logpath,LOG_FILENAME)
        if (not LoggerPath):
            # then look in home folder
            if os.access(os.path.expanduser('~'), os.W_OK):
                LoggerPath = os.path.join(os.path.expanduser('~'),LOG_FILENAME)
            else:
                print("Error opening logger, exit xvr")
                exit(1)
        return (LoggerPath)
    
    def GetYml(self):
        if self.docker:
            ymlpath = os.path.join(DOCKER_BASE, DOCKER_CFG)
        else:
            ymlpath = GENERAL_CFG
        YamlPath = ""
        # first look in log path
        if os.path.exists(ymlpath):
            if os.access(ymlpath, os.W_OK):
                YamlPath = os.path.join(ymlpath,YML_FILENAME)
                self.checkYml(YamlPath)
        if (not YamlPath):
            # then look in home folder
            if os.access(os.path.expanduser('~'), os.W_OK):
                YamlPath = os.path.join(os.path.expanduser('~'),YML_FILENAME)
                self.checkYml(YamlPath)
            else:
                print("Error opening yaml, exit xvr")
                exit(1)
        return (YamlPath)
    
    def checkYml(self, YamlPath):
        if not os.path.isfile(YamlPath):
            try:
                with open(DEFAULT_YML, "r") as src:
                    with open (YamlPath, "w") as dest:
                        while line := src.readline():
                            dest.write(line)
            except:
                print("Error writing default yaml, exit xvr")
                exit(1)

            
    def handleArgs(self, argv):
        if len(sys.argv) > 1:
            arg = sys.argv[1]
            if arg == "-h" or arg == "--help":
                self.printHelp()
            else:
                self.logger.error("Incorrect argument entered")
                self.printError()
        try:
            with open(self.GetYml(), "r") as f:
                try:
                    self.settings = yaml.safe_load(f)
                    if self.docker: # use default video path and restapi port for docker
                        self.settings["general"]["videofolder"] = DOCKER_CAMERAS
                        self.settings["restapi"]["port"] = DOCKER_RESTAPIPORT
                except:
                    self.logger.error("Error parsing yaml file")
                    self.printError()
        except:
            self.logger.error("yaml file not found")
            self.printError()

    def setlogger(self):
        settingsGeneral = common.getsetting(self.settings, "general")
        if settingsGeneral:
            settingsLogging = common.getsetting(settingsGeneral, "logging")
            if settingsLogging:
                if settingsLogging.lower() == "critical":
                    self.loglevel = logging.CRITICAL
                elif settingsLogging.lower() == "error":
                    self.loglevel = logging.ERROR
                elif settingsLogging.lower() == "info":
                    self.loglevel = logging.INFO 
            self.logger.setLevel(self.loglevel)    

    def printHelp(self):
        print("Option:")
        print("    -h, --help: print this help file and exit")
        print(" ")
        print("Enter options in /etc/xvr.yml")
        exit(0)

    def printError(self):
        print("Enter {} -h for help".format(APP_NAME))
        exit(1)

    def exit_app(self, signum, frame):
        self.exitval = 0
        self.term.set()

#########################################################

######################### MAIN ##########################
if __name__ == "__main__":
    xvr().run(sys.argv)