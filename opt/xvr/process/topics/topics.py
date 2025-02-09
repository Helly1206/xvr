# -*- coding: utf-8 -*-
#########################################################
# SERVICE : topics.py                                   #
#           Class handling topics naming                #
#                                                       #
#           I. Helwegen 2024                            #
#########################################################

####################### IMPORTS #########################
from common.common import common

#########################################################

# dict: {device: [{ cmd_t: "", stat_t: "", type: ..., class: ... }]}
# types:
# analog actuator: "number"
# digital actuator: "switch", "event"
# analog sensor: "sensor"
# digital sensor: "binary_sensor", "button"

####################### GLOBALS #########################
DEFAULT_STATUS = "_st"
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : topics                                        #
#########################################################
class topics(object):
    def __init__(self, type, rev, settings = {}):
        self.data = None
        dataImport = common.Import("process.topics." + type + "_" + str(rev))
        if dataImport:
            self.data = dataImport.topicData()
        self.settings = settings

    def __del__(self):
        pass

    def __repr__(self):
        return self.data.name

    def getAlias(self, key, sub = True, suf = True):
        alias = ""
        if sub:
            suffix = ""
            if suf:
                if "st_suffix" in self.settings:
                    if self.settings["st_suffix"]:
                        suffix = "_" + self.settings["st_suffix"]
                else:
                    suffix = DEFAULT_STATUS
            if key in self.data.sub:
                if key in list(self.settings.keys()):
                    if self.settings[key]:
                        alias = self.settings[key] + suffix
                    else:
                        alias = key + suffix
                else:
                    alias = key + suffix
        else:
            suffix = ""
            if suf:
                if "cmd_suffix" in self.settings:
                    if self.settings["cmd_suffix"]:
                        suffix = "_" + self.settings["cmd_suffix"]
            if key in self.data.pub:
                if key in list(self.settings.keys()):
                    if self.settings[key]:
                        alias = self.settings[key] + suffix
                    else:
                        alias = key + suffix
                else:
                    alias = key + suffix
        return alias

    def getTopic(self, key):
        topic = key
        suffix = ""
        if "cmd_suffix" in self.settings:
            if self.settings["cmd_suffix"]:
                suffix = "_" + self.settings["cmd_suffix"]
            if not suffix in key:
                key = ""
        key = key.removesuffix(suffix)
        for stopic, alias in self.settings.items():
            if key == alias:
                topic = stopic
                break
        if topic not in self.data.pub:
            topic = ""
        return topic
    
    def getTopics(self):
        topics = []
        for topic in self.data.topics:
            top = {}
            top["name"] = ""
            if topic["cmd_t"]:
                top["cmd_t"] = self.getAlias(topic["cmd_t"], False)
                top["name"] = self.getAlias(topic["cmd_t"], False, False)
            else:
                top["cmd_t"] = ""
            if topic["stat_t"]:
                top["stat_t"] = self.getAlias(topic["stat_t"])
                if top["name"] == "":
                    top["name"] = self.getAlias(topic["stat_t"], True, False)
            else:
                top["stat_t"] = ""
            if top["name"] == "":
                top["name"] = "Unknown"
            top["type"] = topic["type"]
            top["dev_cla"] = topic["dev_cla"]
            topics.append(top)
        return topics

######################### MAIN ##########################
if __name__ == "__main__":
    pass
