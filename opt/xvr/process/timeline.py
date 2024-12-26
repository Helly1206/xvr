# -*- coding: utf-8 -*-
#########################################################
# SERVICE : datalog.py                                  #
#           logging of data from detections to file     #
#                                                       #
#           I. Helwegen 2024                            #
#########################################################

####################### IMPORTS #########################
import logging
import os
from datetime import datetime, timedelta
from common.common import common
import json

#########################################################

####################### GLOBALS #########################
TIMELINE_FILE = "timeline"
TIMELINE_EXTJSON = ".json"
TIMELINE_EXTCSV = ".csv"
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : timeline                                      #
#########################################################
class timeline(object):
    def __init__(self, basename, camname, settings, general, path):
        self.logger = logging.getLogger('{}.timeline [{}]'.format(basename, camname))
        self.camname = camname
        self.settings = settings
        self.general = general
        self.path = path
        self.data = {"time": 0, "type": "none", "filename": "", "filetime": 0, "duration": 0}

    def __del__(self):
        del self.data
        del self.logger

    def start(self, topicType, streamData):
        self.data["time"] = datetime.now().timestamp()
        self.data["type"] = topicType
        self.data["filename"] = streamData["filename"]
        self.data["filetime"] = streamData["time_s"]
        self.data["duration"] = 0

    def stop(self, stopTime):
        self.data["duration"] = stopTime - self.data["time"]
        self.addData()

    def updateType(self, topicType):
        self.data["type"] = topicType

    def cleanup(self):
        days = common.getsetting(self.settings, "keepdays", 28)
        if days > 0:
            self.logger.debug("Cleaning up timeline")
            if common.getsetting(self.general, "timelineformat", "json").lower() == "json":
                self.cleanupJson(days)
            else:
                self.cleanupCsv(days)

    def addData(self):
        data = self.processData()  
        if common.getsetting(self.general, "timelineformat", "json").lower() == "json":
            self.writeJson(data)
        else:
            self.writeCsv(data)
        self.logger.debug("Added timeline data")

    def processData(self):
        data = {}
        data["time"] = datetime.fromtimestamp(self.data["time"]).strftime("%Y-%m-%d %H:%M:%S")
        data["type"] = self.data["type"]
        data["filename"] = self.data["filename"]
        data["filetime"] = str(timedelta(seconds=int(self.data["filetime"]))) #).strftime("%H:%M:%S")
        data["duration"] = int(self.data["duration"])
        return data
    
    def writeJson(self, data):
        filename = self.GetFilename()
        if filename:
            jdata = json.dumps(data) + "\n" + "]\n"
            with open(filename, "r+") as f:
                pos = 0
                while line := f.readline().strip():
                    if line[0] != "]":
                        pos = f.tell()
                f.seek(pos)
                f.truncate()
                if pos > 2:
                    f.write(",\n")
                f.write(jdata)

    def writeCsv(self, data):
        filename = self.GetFilename()
        if filename:
            cdata = "{}, {}, {}, {}, {}\n".format(data["time"], data["type"], data["filename"], data["filetime"], data["duration"])
            with open(filename, "a") as f:
                f.write(cdata)

    def cleanupJson(self, days):
        filename = self.GetFilename()
        if filename:
            with open(filename, "r+") as f:
                lines = f.readlines()
                f.seek(0)
                dellist = []
                for i, line in enumerate(lines):
                    try:
                        if line[0] == "{":
                            jline = json.loads(line)
                            if self.deleteLine(jline["time"], days):
                                dellist.append(i)
                                self.logger.debug(f"Cleanup timeline: deleted {jline["time"]}")
                                if i + 1 < len(lines):
                                        if lines[i+1][0] == ",":
                                            dellist.append(i+1)
                    except:
                        pass
                if dellist:
                    for i in reversed(dellist):
                        lines.pop(i)
                    f.truncate()
                    f.writelines(lines)

    def cleanupCsv(self, days):
        filename = self.GetFilename()
        if filename:
            with open(filename, "r+") as f:
                lines = f.readlines()
                f.seek(0)
                dellist = []
                for i, line in enumerate(lines):
                    try:
                        timeStr = line.split(",")[0].strip()
                        if timeStr != "time":
                            if self.deleteLine(timeStr, days):
                                dellist.append(i)
                                self.logger.debug(f"Cleanup timeline: deleted {timeStr}")
                    except:
                        pass
                if dellist:
                    for i in reversed(dellist):
                        lines.pop(i)
                    f.truncate()
                    f.writelines(lines)

    def deleteLine(self, timeStr, days):
        result = False
        try:
            timeFmt = datetime.strptime(timeStr, "%Y-%m-%d %H:%M:%S")
            if (datetime.now() - timeFmt).days > days:
                result = True
        except:
            pass
        return result

    def GetFilename(self):
        filename = ""
        if not self.path:
            self.logger.error("Cannot record timeline, as no path available")
        else:
            if common.getsetting(self.general, "timelineformat", "json").lower() == "json":
                filename = os.path.join(self.path, TIMELINE_FILE + TIMELINE_EXTJSON)
                if not os.path.isfile(filename):
                    with open(filename, "w") as f:
                        f.write("[\n]\n")
                    self.logger.info(f"Created new timeline file {filename}")
            else:
                filename = os.path.join(self.path, TIMELINE_FILE + TIMELINE_EXTCSV)
                if not os.path.isfile(filename):
                    with open(filename, "w") as f:
                        f.write("time, type, filename, filetime, duration\n")
                    self.logger.info(f"Created new timeline file {filename}")
        return filename


######################### MAIN ##########################
if __name__ == "__main__":
    pass
