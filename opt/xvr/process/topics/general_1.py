# -*- coding: utf-8 -*-
#########################################################
# SERVICE : generic_1.py                                #
#           Class containing general topic data for     #
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
    name = "general"
    pub = ["restart"]
    sub = ["restart", "online"]
    topics = [{"cmd_t": "restart", "stat_t": "",       "type": "button", "dev_cla": "restart"},
              {"cmd_t": "",        "stat_t": "online", "type": "event",  "dev_cla": ""}]
    
######################### MAIN ##########################
if __name__ == "__main__":
    pass
