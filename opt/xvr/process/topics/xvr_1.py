# -*- coding: utf-8 -*-
#########################################################
# SERVICE : xvr_1.py                                    #
#           Class containing topic data for             #
#           xvr service, revision 1                     #
#           I. Helwegen 2024                            #
#########################################################

####################### IMPORTS #########################

#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : topicData                                     #
#########################################################
class topicData:
    name = "xvr"
    pub = ["enable", "record"]
    sub = ["recording", "detected", "enable", "record", "detection"]
    topics = [{"cmd_t": "enable", "stat_t": "enable",    "type": "switch",        "dev_cla": ""},
              {"cmd_t": "record", "stat_t": "record",    "type": "switch",        "dev_cla": ""},
              {"cmd_t": "",       "stat_t": "recording", "type": "binary_sensor", "dev_cla": "running"},
              {"cmd_t": "",       "stat_t": "detected",  "type": "binary_sensor", "dev_cla": "motion"},
              {"cmd_t": "",       "stat_t": "detection", "type": "sensor",        "dev_cla": ""}]
    
######################### MAIN ##########################
if __name__ == "__main__":
    pass
