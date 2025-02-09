# -*- coding: utf-8 -*-
#########################################################
# SERVICE : wiper.py                                    #
#           cleaning up and removing old files          #
#                                                       #
#           I. Helwegen 2024                            #
#########################################################

####################### IMPORTS #########################
import logging
import os 
from datetime import datetime
from common.common import common

#########################################################

####################### GLOBALS #########################
VIDEOEXTENSION = ".mp4"
MB2B           = 1024*1024
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : wiper                                         #
#########################################################
class wiper(object):
    def __init__(self, basename, camname, settings, path):
        self.logger = logging.getLogger('{}.wiper [{}]'.format(basename, camname))
        self.camname = camname
        self.settings = settings
        self.path = path

    def __del__(self):
        del self.logger

    def cleanup(self):
        if not self.path:
            self.logger.error("Cannot cleanup, as no path available")
        else:
            days = common.getsetting(self.settings, "keepdays", 28)
            if days > 0:
                self.logger.debug("Cleaning up files on max time")
                self.wipeFilesTime(days)
            mbs = common.getsetting(self.settings, "maxsizemb", 0)
            if mbs > 0:
                self.logger.debug("Cleaning up files on max folder size")
                self.wipeFilesSize(days)

    def wipeFilesTime(self, days):
        try:
            list_of_files = os.listdir(self.path) 
            current_time = datetime.now()

            for file in list_of_files: 
                file_location = os.path.join(self.path, file)
                ext = os.path.splitext(file_location)[1]
                if ext == VIDEOEXTENSION:
                    file_time = datetime.fromtimestamp(os.stat(file_location).st_mtime)
                    if (current_time - file_time).days > days:
                        os.remove(file_location)
                        self.logger.debug(f"Cleanup video files: deleted {file_location}")
        except:
            self.logger.error("Cannot remove files on max time")

    def wipeFilesSize(self, fsize):
        try:
            list_of_files = os.listdir(self.path) 
            maxsize = fsize * MB2B
            files = []
            totalsize = 0
            for file in list_of_files:
                file_location = os.path.join(self.path, file) 
                ext = os.path.splitext(file_location)[1]
                if ext == VIDEOEXTENSION:
                    fdata = {}
                    fdata["fname"] = file_location
                    fdata["time"] = os.stat(file_location).st_mtime
                    fdata["size"] = os.stat(file_location).st_size
                    totalsize += fdata["size"]
                    files.append(fdata)
            if totalsize > maxsize:
                files.sort(key = self.sortfunc)
                dellist = []
                for i, file in enumerate(files):
                    if totalsize > maxsize:
                        totalsize -= file["size"]
                        dellist.append(i)
                for i in dellist:
                    os.remove(files[i]["fname"])
                    self.logger.debug("Cleanup video files: deleted {}".format(files[i]["fname"]))
        except:
            self.logger.error("Cannot remove files on max folder size")

    def sortfunc(self, e):
        return e['time']

######################### MAIN ##########################
if __name__ == "__main__":
    pass
