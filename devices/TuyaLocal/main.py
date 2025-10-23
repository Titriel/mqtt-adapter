from os import path, getcwd
from sys import path as PATH
PATH.append(path.join(getcwd(),"script"))
import logging
from logsetup import d2s, pretty
from time import sleep, time as now
from json import loads, dumps
import tinytuya

logger = logging.getLogger()
pretty()

class device:
  def ini_tuyadev(self):
    tuya = {'OutletDevice': tinytuya.OutletDevice, 'CoverDevice': tinytuya.CoverDevice, 'BulbDevice': tinytuya.BulbDevice}
    self.tuya = tuya[self.c['devtype']](self.c['id'], self.c['ip'], self.c['localKey'],
                                        version=self.c['version'],
                                        connection_timeout=self.c['timeout'],
                                        connection_retry_limit=self.c['retry_limit'],
                                        connection_retry_delay=self.c['retry_delay'],
                                        persist=self.c['persist'],
                                        cid=self.c['cid'],
                                        node_id=self.c['node_id'],
                                        parent=self.c['parent']
                                        )
    
  def __init__(self, config, topic, publisher):
    defauls = {'version': 3.3, 'timeout': 5, 'retry_limit': 5, 'retry_delay': 5,
               'persist': False, 'cid': None, 'node_id': None, 'parent': None,
               'interval': 10, 'latest': 300}
    self.topic = topic
    self.publisher = publisher
    self.buffer = []
    self.workerrunning = False
    self.tryset = False
    self.c = config
    self.dps = {'online': False}
    self.dpschanged = {}
    self.name_map = {}
    self.lastsendet = ''
    for dp in self.c["dp_map"]:
      self.name_map[self.c["dp_map"][dp][0]] = dp
    for key in defauls:
      if key not in config:
        self.c[key] = defauls[key]
    self.ini_tuyadev()
    self.gets = {}
    if self.c['devtype'] == 'OutletDevice':
      self.calls = {'dimmer': self.tuya.set_dimmer},
    elif self.c['devtype'] == 'CoverDevice':
      self.calls = {'open_cover': self.tuya.open_cover,
                    'close_cover': self.tuya.close_cover,
                    'stop_cover': self.tuya.stop_cover}
    elif self.c['devtype'] == 'BulbDevice':
      if 'bulb_type' in self.c:
        self.tuya.set_bulb_type(self.c['bulb_type'])
      self.calls = {'colour_rgb': self.tuya.set_colour,
                    'colour_hsv': self.tuya.set_hsv,
                    'white': self.tuya.set_white,                    
                    'colourtemp': self.tuya.set_colourtemp,
                    'brightness': self.tuya.set_brightness,
                    'white_percentage': self.tuya.set_white_percentage,                    
                    'colourtemp_percentage': self.tuya.set_colourtemp_percentage,
                    'brightness_percentage': self.tuya.set_brightness_percentage,                    
                    'scene': self.tuya.set_scene,
                    'mode': self.tuya.set_mode}
      self.gets =  {'colour_rgb': self.tuya.colour_rgb,
                    'colour_hsv': self.tuya.colour_hsv,
                    'colourtemp': self.tuya.colourtemp,
                    'brightness': self.tuya.brightness,
                    'state': self.tuya.state}
    
    logger.info("do init the device %s", d2s(config))

  def publish_status(self, force = False, maxtime = False):
    data = self.tuya.status()
    if type(data) is dict and 'Err' in data and data['Err'] == "914":
      self.ini_tuyadev()
      sleep(1)
      data = self.tuya.status()
    ref = dumps(data)
    if not self.tryset and (maxtime or (self.lastsendet != ref)) or force:
      self.lastsendet = ref
      logger.info("dps %s: %s", force, ref)
      if (data is not None) and ('dps' in data):
        for dp in data['dps']:
          if dp in self.c["dp_map"]:
            dpitem = self.c["dp_map"][dp]
            if dpitem[2] is not None and not dpitem[1]:
              if (type(dpitem[2]) == str) and ((dpitem[2] == "bool") or (dpitem[2] == "str") or (dpitem[2] == "enum")):
                self.dps[dpitem[0]] = data['dps'][dp]
              elif (type(dpitem[2]) == int) and (dpitem[2] > -1):
                self.dps[dpitem[0]] = data['dps'][dp] * 10 ** dpitem[2]
              elif (type(dpitem[2]) == int) and (dpitem[2] < 0):
                scal = dpitem[2] * -1
                self.dps[dpitem[0]] = round(data['dps'][dp] / 10 ** scal, scal)
        for dp in self.c["dp_map"]:
          if (dp in self.gets) and not self.c["dp_map"][dp][1] and (self.c["dp_map"][dp][2] is not None):
            try:
              temp = self.gets[dp]()
              if type(temp) == dict:
                for key in temp:
                  self.dps[key] = temp[key]
              else:
                self.dps[self.c["dp_map"][dp][0]] = temp
            except:
              logger.warning("Can't get data from %s", dp)
        self.dps['online'] = True
      else:
        self.dps['online'] = False
        for lable in self.dpschanged:
          self.dps[lable] = self.dpschanged[lable]
      self.dpschanged = {}
      self.publisher(self.topic, dumps(self.dps))

  def on_busy(self, topic, payload, retain):
    self.buffer.append({"topic": topic, "payload": payload, "retain": retain})

  def on_massage(self, topic, payload, retain):
    if len(self.buffer) > 0:
      self.buffer.append({"topic": topic, "payload": payload, "retain": retain})    
    while True:
      if len(self.buffer) > 0:
        temp = self.buffer.pop(0)
        topic = temp["topic"]
        payload = temp["payload"]
        retain = temp["retain"]

      logger.info("Received message for topic %s: %s", topic, payload)
      if retain==1:
        logger.info("This is a retained message")
      if '"set":' in payload:
        self.dpschanged = {}
        data = loads(payload)["set"]
        for lable in data:
          if lable in self.name_map:
            dp = self.name_map[lable]
            dpitem = self.c["dp_map"][dp]
            if (dpitem[2] is not None) and ((dpitem[1] is None) or dpitem[1]): #None: R/W False: R True: W
              if (type(dpitem[2]) is str) and (dpitem[2] == "enum"):
                if data[lable] not in dpitem[3:]:
                  logger.warning("Wrong value %s for parameter %s.", data[lable], lable)
                  return
              self.tryset = True
              if lable in self.dps:
                self.dpschanged[lable] = self.dps[lable]
                self.dps[lable] = data[lable]
              if type(dpitem[2] ) == int:          
                if dpitem[2] > 0:
                  data[lable] = round(data[lable] / 10 ** dpitem[2])
                elif dpitem[2] < 0:
                  data[lable] = round(data[lable] * 10 ** dpitem[2])
                if len(dpitem) > 3:
                  if (data[lable] < dpitem[3][0]) or (data[lable] > dpitem[3][1]):
                    logger.warning("Wrong value %s for parameter %s.", data[lable], lable)
                    return
                                        
              logger.info("Set property")
              #sleep(0.1)
              #self.publisher(self.topic, dumps(self.dps))
              if dp.isnumeric():
                self.tuya.set_value(dp, data[lable])
              else:
                if dp in self.calls:
                  value = []
                  if (type(dpitem[2]) is str) and (dpitem[2] == "list"):
                    i = 3
                    for item in data[lable]:
                      if (item >= dpitem[i][0]) and (item <= dpitem[i][1]):
                        value.append(item)
                      else:
                        logger.warning("Wrong value %s for parameter %s.", data[lable][i-3], lable)
                        return 
                      i += 1                     
                  else:
                    value.append(data[lable])
                  if len(value) == 1:
                    self.calls[dp](value[0])
                  elif len(value) == 2:
                    self.calls[dp](value[0], value[1])
                  elif len(value) == 3:
                    self.calls[dp](value[0], value[1], value[2])
              self.lastsendet = ''              
              self.tryset = False
            else:
              logger.warning("Setting parameter %s is not alowed.", lable)
        sleep(0.1)      
        self.publish_status(True)
      if len(self.buffer) == 0:
        return
      
  def worker(self):
    logger.info("This is my worker %s", self.topic)
    next = now()
    lastsend = 0
    self.lastsendet = ''
    while (self.workerrunning):
      next += self.c["interval"]
      if not self.tryset:
        self.publish_status(maxtime = next - lastsend > self.c["latest"])
        #if self.dps['online']:
        lastsend = next
      wait = next - now()
      if wait > 0:
        sleep(wait)
      else:
        next = now() + self.c["interval"]
    logger.info("Stopping worker %s", self.topic)
    return True