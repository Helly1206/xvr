XVR - v0.8.1

XVR - Simple but eXtended Network Video Recorder
=== = ====== === ======== ======= ===== ========

For home cameras using RTSP and ONVIF a lot of NVR applications are available. Disadvantages are:
* Many times advanced services need to be paid for
* Internal camera detection is not used, but AI detectors which cost a lot of processing power

XVR uses ONVIF events for detections and records a stream using FFMPEG. Very lightweight and customizable.
The current version doesn't have a GUI, and must be configured via the yaml file.
A GUI can be provided by an external service, like homeassistant:
* Use an RTSP camera for live view
* Via MQTT detections/ recordings can be triggered
* Recorded videos can be linked to the homeassistant media folder to be viewed there
I may post a more detailed instruction in the future.

features:
---------
* 24/7 recording (maximum file duration can be set)
* recording when event triggered (with ending offset)
* Event triggering with debouncing (multiple events close after each other are seen as single event)
* Motion, person, vehicle and pet detection if supported by the camera
* JSON or CSV file containing trigger log and position in file
* External enable (e.g. do not record if person is at home)
* File cleanup on age or maximum folder size
* restapi interface for external enable, trigger and status readout
* MQTT interface for external enable, trigger and status readout

XVR:
----

XVR is a service, so no user interaction is required. 

To communicate with XVR, 2 options are implemented:

restapi:
--------

Via http a command can be send to the service. The service then gives a response in JSON format.

Status requests are done by a http get in the following format:
http://username:password@localhost:port/[camera][/tag]
Replace [camera] with camera name given in yaml settings file
The status response is then given in JSON. If the service doesn't run on the localhost, the IP address of that system must 
be entered.
The get request can be entered in a browser or placed by a tool like curl:
curl -X get http://username:password@localhost:port/[camera][/tag]

command requests are done by a http put in the following format:
http://username:password@localhost:port/[camera]
The payload is in JSON format: {"tag1": "value1", "tag2": "value2"}
The put request can be placed by curl:
curl -X PUT http://localhost:8080/[camera] -d "{\"tag1\":\"value1\",\"tag2\":\"value2\"}"
To test/ use the system without the availability of curl (but only a browser), as faultback commands can also be entered by
a http get in the following format:
http://username:password@localhost:port/[camera]?tag1=value1&tag2=value2

mqtt:
-----

As lot of smarthome platforms support MQTT, this is the prefered way to interact with the relays.
commands needs to be published and status needs to be received (subscribed) in the following format:
[maintopic]/[camera]/tag1
For use with home assistant, device discovery can be used. 

Available tags:
--------- -----
general: (use general as camera)
restart: (command) restart the xvr application
online: (status) boolean - high when xvr is online and running

Per camera:
recording: (status) boolean - high when the camera stream is being recorded
detected: (status) boolean - high when event detected or debouncing
enable: (command, status) boolean - enable recording (if enabled in settings)
record: (command, status) boolean - trigger extenral recording
detection: (status) string - type of detection

Installation:
-------------
Manual installation can be done as follows:
- Browse to: https://github.com/Helly1206/xvr
- Click the 'Clone or Download' button
- Click 'Download Zip'
- Unzip the zip file to a temporary location
- Open a terminal at this location
- Enter: 'sudo ./install.sh'
- Wait and answer the questions:
	Do you want to install an automatic startup service for iotusb (Y/n)?
   		Default = Y
   		If you want to automatically start iotusb during startup (or don't know), answer Y to this question.
   		If you do not want to install an automatic startup script, answer N to this question.

Installer options:
--------- --------
sudo ./install.sh    --> Installs iotusb
sudo ./install.sh -u --> Uninstalls iotusb
sudo ./install.sh -c --> Deletes compiled files in install folder (only required when copying or zipping the install folder)
sudo ./install.sh -d --> Builds debian packages

Package install:
------- --------
iotusb installs automatically from deb package/ apt repository (only for debian based distros like debian or ubuntu).
Just enter: 'sudo apt install iotusb' after adding the repository
see: https://github.com/Helly1206/hellyrepo for installing the repository

Docker:
-------

XVR can also be installed as docker image.
The image needs to be build from the docker folder.
- Browse to: https://github.com/Helly1206/xvr
- Click the 'Clone or Download' button
- Click 'Download Zip'
- Unzip the zip file to a temporary location
- Open a terminal at this location
- Navigate to docker
- Enter: 'build.sh'

In the future the docker image might be stored somewhere online (Docekrhub) for more convenience.

Docker configuration example (docker compose):

version: '3'
services:
  xvr:
    image: 'xvr:v0.8.0'
    container_name: xvr
    restart: unless-stopped
    ports:
      - 8081:8081
    environment:
      TZ: 'Europe/Amsterdam'
    volumes:
      - /opt/xvr/config:/data/config
      - /opt/xvr/log:/data/log
      - /mynas/cameras:/cameras

Configuration:
--------------
In /etc/xvr.yml, the configuration file is found. (/data/config/xvr.yml for docker implementation)

# xvr settings file
#
#general:                 # general settings
#  logging:               # critical, error, info or debug, default = info
#  videofolder:           # folder to store videos, default = /cameras (cannot change on docker)
#  timelineformat:        # json or csv, default = json
#
#restapi:                 # restapi settings
#  enable:                # true enables restapi
#  port:                  # restapi port, default 8081 (cannot change on docker)
#  username:              # restapi username, no username if not entered or empty
#  password:              # restapi password, no password if not entered or empty. Username is required for password.
#
#mqtt:                    # mqtt settings
#  enable:                # true enables mqtt
#  broker:                # mqtt broker ip-address or url
#  port:                  # mqtt port, default = 1883
#  username:              # mqtt username, no username if not entered or empty
#  password:              # mqtt password, no password if not entered or empty. Username is required for password.
#  maintopic:             # mqtt main topic for all cameras, default = xvr
#  hatopic:               # home assistaant auto discovery topic. No discovery if empty or not entered, default = homeassistant
#  qos:                   # quality of service, default = 0
#  retain:                # retain published messages, default = true

#cameras:                 # settings for cameras
#  camera1:               # the name of the first camera (used for detection of device hardware and in restapi and mqtt topic)
#    friendlyname:        # friendly name for camera, e.g."Livingroom Camera"
#    alias:               # aliases (names) for commands and status (if not entered defaults are used)
#      cmd_suffix:        # suffix for commands over mqtt. default empty
#      st_suffix:         # suffix for status over mqtt. default status
#      enable:            # enable input, rename if required
#      record:            # record input, rename if required
#      recording:         # recording output, rename if required
#      detected:          # detected output, rename if required
#    host:                # hostname or ip-address of camera
#    username:            # username to login to camera
#    password:            # password for camera
#    rtsprecord:          # record video via rtsp, default = true
#    rtspport:            # rtsp port, default = 554
#    rtspstream:          # rtsp stream (added to url), default = stream1
#    onvifdetect:         # use onvif to detect motion, default = true
#    onvifport:           # onvif port, default = 2020
#    onviftype: []        # detection type array, choose from: [motion, person, pet, vehicle]
#    detectpost:          # number of seconds to extend tetection (for debouncing), default = 5
#    extrecord:           # use external record input, default = false
#    extenable:           # use external enable input, default = true
#    continuerec:         # record 24/7, default = false
#    vcodec:              # video codec, choose from: none, copy, <codec>, default = copy
#    acodec:              # audio codec, choose from: none, copy, <codec>, default = aac
#    maxfilesize:         # number of seconds filesize to start new file, defualt = 3600
#    recordpost:          # number of seconds to record if motion finished, default = 20
#    keepdays:            # number of days to keep recordings, 0 = keep always, default = 28
#    maxsizemb:           # maximum size of video folder in MB, 0 = no limit, default = 0 
#    timeline:            # write detections in timeline, default = true

After changing the yaml configuration, the service needs to be restarted.

Home assistant examples:
---- --------- ---------

Automation to switch on or off enable of a camera (e.g. disable recording when someone is home)

- id: '<enter your id here>'
  alias: Record Livingroom camera
  description: ''
  mode: single
  triggers:
    - trigger: state
      entity_id:
        - binary_sensor.record_camera #<sensor to e.g. detect someone is home>
      from: "off"
      to: "on"
      id: record_on
    - trigger: state
      entity_id:
        - binary_sensor.record_camera #<sensor to e.g. detect someone is home>
      from: "on"
      to: "off"
      id: record_off
    - trigger: state
      entity_id:
        - binary_sensor.general_online
      to: "on"
      id: online
  conditions: []
  actions:
    - if:
        - condition: or
          conditions:
            - condition: trigger
              id:
                - record_on
            - condition: and
              conditions:
                - condition: trigger
                  id:
                    - online
                - condition: state
                  entity_id: binary_sensor.record_camera #<sensor to e.g. detect someone is home>
                  state: "on"
      then:
        - action: switch.turn_on
          metadata: {}
          data: {}
          target:
            entity_id: switch.livingroom_enable #camera is called livingroom
      else:
        - action: switch.turn_off
          metadata: {}
          data: {}
          target:
            entity_id: switch.livingroom_enable #camera is called livingroom

Example of adding video folder to media folder in home assistant:

Take care that video folder can be accessed in home assistant. e.g. in docker (core) add as volume:
      - /<path to videos>/cameras:/cameras

add in configuration.yaml:
homeassistant:
  allowlist_external_dirs:
    - /cameras
  media_dirs:
    media: /media
    camera: /cameras

Example of dashboard containing generic gamera for live view:

views:
  - title: Home
    sections:
      - type: grid
        cards:
          - type: heading
            heading: Livingroom Camera
            heading_style: title
            icon: mdi:webcam
          - show_state: false
            show_name: false
            camera_view: live
            type: picture-entity
            entity: camera.livingroomcamera
          - type: history-graph
            show_names: false
            entities:
              - entity: binary_sensor.livingroom_detected
            hours_to_show: 48
            logarithmic_scale: false
          - type: history-graph
            show_names: false
            entities:
              - entity: sensor.livingroom_detection
            hours_to_show: 48
            logarithmic_scale: false
          - show_name: false
            show_icon: true
            type: button
            icon: mdi:webcam
            tap_action:
              haptic: heavy
              action: navigate
              navigation_path: >-
                /media-browser/browser/app%2Cmedia-source%3A%2F%2Fmedia_source/%2Cmedia-source%3A%2F%2Fmedia_source%2Fcamera%2Flivingroom
        column_span: 1

That's all for now ...

Have fun

Please send Comments and Bugreports to hellyrulez@home.nl
