# -*- coding: utf-8 -*-
#########################################################
# SERVICE : restapi.py                                  #
#           REST API for set/ get relay status          #
#           I. Helwegen 2024                            #
#########################################################

####################### IMPORTS #########################
from threading import Thread, Lock
from json import dumps, loads 
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
import base64
from urllib.parse import urlparse, parse_qs
from common.common import common
#########################################################

####################### GLOBALS #########################
HOSTNAME = "" #"localhost"
DEFAULTPORT = 12465

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : restHandler                                   #
#########################################################
class restHandler(BaseHTTPRequestHandler):
    def __init__(self, base, basename, key, devices):
        self.logger = logging.getLogger('{}.restHandler'.format(basename))
        self.base = base
        self.key = key
        self.devices = devices
        self.values = {}
        self.mutex = Lock()

    def __del__(self):
        del self.mutex
        del self.values
        del self.logger

    def __call__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        message = format % args
        self.logger.debug("%s - - [%s] %s" %
                         (self.address_string(),
                          self.log_date_time_string(),
                          message.translate(self._control_char_table)))
    
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", "Basic realm=\"restapi\"")
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def response(self, success, data = {}, error = ""):
        resp = {}
        resp["success"] = success
        if error:
            resp["error"] = error
        if data:
            resp["data"] = data
        self.wfile.write(bytes(dumps(resp), "utf-8"))

    def doAuth(self):
        isAuth = False
        if not self.key:
            self.do_HEAD()
            isAuth = True
        elif self.headers.get("Authorization") == None:
            self.do_AUTHHEAD()
            self.response(False, error="No auth header received")
        elif self.headers.get("Authorization") == "Basic " + str(self.key):
            self.do_HEAD()
            isAuth = True
        else:
            self.do_AUTHHEAD()
            self.response(False, error="Invalid credentials")
        return isAuth
    
    def getUrl(self):
        device = ""
        tag = ""
        query = {}
        url = urlparse(self.path)
        path = url.path.lstrip("/").split("/")
        if path:
            if len(path) > 1:
                tag = path[1]
            device = path[0]

        query = parse_qs(url.query)
        for key, value in query.items():
            query[key] = value[0]
        return device, tag, query

    def do_GET(self):
        #http://username:password@localhost:port/device[/tag] (?tag1=value1&tag2=value2)
        if self.doAuth():
            device, tag, query = self.getUrl()
            if not device and len(self.devices) == 1:
                device = self.devices[0]
            if not device.lower() in self.devices:
                self.response(False, error="Unknown device")
            elif query:
                if tag:
                    self.response(False, error="Tag not allowed in set request")
                else:
                    self.handleQuery(device, query)
            elif tag:
                value = self.getValue(device, tag)
                if value != None:
                    response = {}
                    response[tag] = value
                    self.response(True, response)
                else:
                    self.response(False, error="Tag not found on this device")
            else:
                response = self.getDevice(device)
                if response:
                    self.response(True, response)
                else:
                    self.response(False, error="Device not found")

    def do_PUT(self):
        #curl -X PUT http://localhost:8080/device -d "{\"tag1\":\"value1\",\"tag2\":\"value2\"}"
        if self.doAuth():
            device, tag, query = self.getUrl()
            if not device and len(self.devices) == 1:
                device = self.devices[0]
            if not device.lower() in self.devices:
                self.response(False, error="Unknown device")
            elif query:
                self.response(False, error="Query data in URL not allowed in put request")
            elif tag:
                self.response(False, error="Tag not allowed in put request")
            else:
                query = {}
                try:
                    length = int(self.headers["Content-Length"])
                    query = loads(self.rfile.read(length).decode("utf-8"))
                except:
                    pass
                if query:
                    self.handleQuery(device, query)
                else:
                    self.response(False, error="Incorrect format of put request")
    
    def handleQuery(self, device, query):
        try:
            response = {}
            error = ""
            success = True
            for tag, value in query.items():
                response[tag] = self.base.set(device, tag, common.gettype(value))
                if response[tag] == None:
                    success = False
            if not success:
                error = "One or more tags not found"
            self.response(success, response, error)
        except:
            self.response(False, error="Incorrect data format")

    def setValue(self, device, tag, value):
        with self.mutex:
            if not device in self.values.keys():
                self.values[device] = {}    
            self.values[device][tag] = value

    def getValue(self, device, tag):
        value = None
        try:
            with self.mutex:
                if len(self.values) == 1 and not device:
                    value = self.values[next(iter(self.values))][tag]
                else:
                    value = self.values[device][tag]
        except:
            pass
        return value
    
    def getDevice(self, device):
        devVal = None
        try:
            with self.mutex:
                if len(self.values) == 1 and not device:
                    devVal = self.values[next(iter(self.values))]
                else:
                    devVal = self.values[device]
        except:
            pass
        return devVal
        
#########################################################
# Class : restapi                                       #
#########################################################
class restapi(Thread):
    def __init__(self, base, basename, settings, devices):
        self.logger = logging.getLogger('{}.restapi'.format(basename))
        self.enabled = common.getsetting(settings, "enable")
        self.base = base
        self.restHandler = None
        self.server = None
        if self.enabled:
            Thread.__init__(self)
            self.serverPort = common.getsetting(settings, "port", DEFAULTPORT)
            self.restHandler = restHandler(base, basename, self.setKey(common.getsetting(settings, "username"), common.getsetting(settings, "password")), devices)
            self.server = HTTPServer((HOSTNAME, self.serverPort), self.restHandler)

    def __del__(self):
        if self.server:
            del self.server
        if self.restHandler:
            del self.restHandler

    def start(self):
        if self.enabled: 
            super().start()

    def terminate(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()

    def setValue(self, device, tag, value):
        if self.enabled and self.restHandler: 
            self.restHandler.setValue(device, tag, value)

    def run(self):
        self.logger.debug("Server started http://%s:%s" % (HOSTNAME, self.serverPort))
        self.base.requestStatus(self.base.RESTAPI)
        try:
            self.logger.info("running")
            self.server.serve_forever()
            self.logger.info("terminating")
        except Exception as e:
            self.logger.exception(e)

    def setKey(self, username, password):
        key = ""
        if username:
            if password:
                key = base64.b64encode(bytes('%s:%s' % (username, password), 'utf-8')).decode('ascii')
            else:
                key = base64.b64encode(bytes(username, 'utf-8')).decode('ascii')
        return key
