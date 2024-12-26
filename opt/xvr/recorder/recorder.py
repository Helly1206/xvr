# -*- coding: utf-8 -*-
#########################################################
# SERVICE : recorder.py                                 #
#           Records streams to a file                   #
#                                                       #
#           I. Helwegen 2024                            #
#########################################################

####################### IMPORTS #########################
import ffmpeg
import os
import logging
from datetime import datetime
from common.common import common
#########################################################

####################### GLOBALS #########################
VIDEOEXTENSION = ".mp4"
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : recorder                                      #
#########################################################
class recorder(object):
    def __init__(self, basename, camname, settings, recpath, cbRecording = None):
        self.logger = logging.getLogger('{}.recorder [{}]'.format(basename, camname))
        self.camname = camname
        self.settings = settings
        self.path = recpath
        self.cbRecording = cbRecording
        self.clearData()
        self.process = None
        self.stoptime = 0

    def __del__(self):
        del self.data
        del self.logger

    def poll(self):
        poll = None
        if self.process:
            poll = self.process.poll()
            try:
                buf = self.process.stderr.read1().decode("utf-8").replace("\r","")
                if buf:
                    error = []
                    lines = buf.split("\n")
                    for line in lines:
                        if not self.decodeData(line):
                            error.append(line)
                    if error:
                        self.logger.error("\n".join(error))
            except:
                pass
            if poll != None:
                self.process = None
                self.callback(False)
            elif self.stoptime > 0:
                if self.data["time_s"] >= self.stoptime:
                    self.stop()
                    # keep poll = None to not print errorcode
        return poll

    def start(self):
        self.clearData()
        if not common.getsetting(self.settings, "rtsprecord", True):
            self.logger.debug("No recording as rtsprecord is not enabled")
            return False
        if self.process:
            self.logger.error("Cannot start recording, as another recording runnning")
            return False
        if not self.path:
            self.logger.error("Cannot start recording, as no path available")
            return False
        self.setFilename()
        stream = self.setStream()
        if not stream:
            self.logger.error("Cannot start recording, as no stream available")
            return False
        outputname = os.path.join(self.path, self.data["filename"])
        try:
            self.process = (
                ffmpeg
                    .input(stream)
                    .output(outputname, **self.getCodecs())
                    .global_args(*self.getGlobalArgs())
                    .overwrite_output()
                    .run_async(pipe_stderr=True)
                )
        except Exception as e:
            self.logger.error("Error starting video stream")
            self.logger.error(e)
            self.process = None
        if self.process:
            os.set_blocking(self.process.stderr.fileno(), False)
            self.logger.debug("Recording started")
            self.callback(True)

        return (self.process != None)

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
            self.process = None
            self.logger.debug("Recording stopped")
            self.callback(False)
        self.clearData()

    def delayedStop(self, times):
        if times == 0:
            self.stoptime = 0
            self.logger.debug("Stop recording reset")
        else:
            if self.process:
                self.stoptime = self.data["time_s"] + times
                self.logger.debug(f"Stop recording @ {self.stoptime}s")

    def restart(self):
        self.stop()
        return self.start()
    
    def recording(self):
        return self.process != None
    
    def callback(self, isRecording):
        if self.cbRecording:
            self.cbRecording(isRecording)

    def getData(self): 
        return self.data

    def clearData(self):
        self.data = {
            "filename": "",
            "size_kb": 0,
            "time_s": 0,
            "bitrate_kbs": 0
        }

    def decodeData(self, line): #size=    1009kB time=00:00:06.75 bitrate=1223.2kbits/s speed=1.46x
        result = False
        if "size=" in line:
            try:
                vals = line.split("=")
                i = 0
                data = {}
                for val in vals:
                    if i<3:
                        data[val.strip()] = vals[i+1].strip().split()[0]
                        vals[i+1] = vals[i+1].strip().split()[1]
                    i += 1
                for key, value in data.items():
                    if key == "size":
                        try: 
                            val = float(value[:-2])
                        except:
                            val = 0
                        self.data["size_kb"] = val
                    elif key == "time":
                        pt = datetime.strptime(value,"%H:%M:%S.%f")
                        self.data["time_s"] = pt.microsecond/1000000 + pt.second + pt.minute*60 + pt.hour*3600
                    elif key == "bitrate":
                        try: 
                            val = float(value[:-7])
                        except:
                            val = 0
                        self.data["bitrate_kbs"] = val
                result = True
            except:
                self.logger.error("Failed to parse stream data")
        return result

    def setFilename(self): #20241209-155315.mp4
        datetime_current = datetime.now()
        datetime_fmt = datetime_current.strftime("%Y%m%d-%H%M%S")
        self.data["filename"] = datetime_fmt + VIDEOEXTENSION

    def setStream(self): #"rtsp://username:password@192.168.x.y/stream1"
        stream = ""
        uname = common.getsetting(self.settings, "username")
        pword = common.getsetting(self.settings, "password")
        if uname:
            if pword:
                upass = uname + ":" + pword + "@"
            else:
                upass = uname + "@"
        else:
            upass = ""
        host = common.getsetting(self.settings, "host")
        if host:
            stream = "rtsp://" + upass + host
            port = common.getsetting(self.settings, "rtspport", 554)
            if port != 554:
                stream += ":" + str(port)
            rtspstream = common.getsetting(self.settings, "rtspstream")
            if rtspstream:
                stream += "/" + rtspstream
        return stream

    def getCodecs(self): 
        vcodec = common.getsetting(self.settings, "vcodec", "copy")
        acodec = common.getsetting(self.settings, "acodec", "aac")
        codecs = {}
        if vcodec:
            if vcodec.lower() == "none":
                codecs["vn"] = None
            else:    
                codecs["vcodec"] = vcodec
        else:
            codecs["vcodec"] = "copy"
        if acodec:
            if acodec.lower() == "none":
                codecs["an"] = None
            else:    
                codecs["acodec"] = acodec
        else:
            codecs["acodec"] = "aac"
        name = common.getsetting(self.settings, "friendlyname")
        if not name:
            name = self.camname
        codecs["metadata"] = 'title=' + name
        return codecs

    def getGlobalArgs(self):
        return "-stats", "-hide_banner", "-loglevel", "error"

######################### MAIN ##########################
if __name__ == "__main__":
    pass
