from time import sleep, time as now
from datetime import date
from datetime import timedelta
from json import loads, dumps
from base64 import b64decode
from math import floor
from sseclient import SSEClient
from requests import exceptions
from os import path, getcwd
from threading import Thread
from sys import path as PATH
PATH.append(path.join(getcwd(), "script"))
PATH.append(path.join(getcwd(), "devices", "ESPrestXY6020L"))
import logging
from logsetup import d2s, pretty as logpretty
import ESPrest
import traceback
from XY6020L import XY6020L

logger = logging.getLogger()
logpretty()

class device:
  def __init__(self, config, topic, publisher):
    self.topic = topic
    self.publisher = publisher
    self.buffer = []
    self.workerrunning = False
    self.syncmetertime = False
    self.c = config
    self.day = date.today() - timedelta(days = 2)
    self.ESPxy6020l = ESPrest.set(self.c["ip"], self.c["token"])
    self.XY6020L = XY6020L(self.c['slaveadr'])
    self.XY6020L.want(self.c['want']) #self.c['want']
    self.timeing = Thread(name="timer", target=self.timer)
    self.timeingwait = False
    self.aktion = []
    logger.info("do init the device %s", d2s(config))

  def timer(self):
    sleeping = True
    sleep(1)
    towait = self.c['interval']
    while (self.workerrunning):
      while self.timeingwait and self.workerrunning and towait > 0.1:
        towait -= 0.1
        sleep(0.1)
      while towait > 0 and len(self.aktion) == 0 and sleeping:
        towait -= 0.05
        sleep(0.05)      
      if len(self.aktion) == 0:
        sleeping = True
        self.timeingwait = True
        towait = self.c['interval']
        self.ESPxy6020l.toTXT(self.XY6020L.readcode())
      else:
        self.timeingwait = True
        sleeping = False
        towait = 0.4
        self.ESPxy6020l.toTXT(self.aktion.pop(0))

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
        self.aktion.extend(self.XY6020L.set(loads(payload)["set"]))

      if len(self.buffer) == 0:
        return
      
  def worker(self):
    logger.info("This is my worker %s", self.topic)

    hadtried = False
    last = now()
    lastdecoded = {}
    self.timeing.start()
    while (self.workerrunning):
      self.ESPxy6020l.open()
      state = mkreadyforxy6020l(self.ESPxy6020l, self.c['baud'])
      if state == hadtried:
        logger.warning("No Stream vom XY6020L.")
        lastdecoded['online'] = False
        self.publisher(self.topic, dumps(lastdecoded))        
      try:
        messages = SSEClient('http://' + self.c["ip"] + '/events', auth=(self.c["sseUser"],self.c["ssePass"]), timeout=self.c["ssetimeout"])
        self.timeingwait = False
        for msg in messages:
          if not self.workerrunning:
            break
          if msg.event == "Serial0":
            Serial0data = loads(msg.data)
            if "RxT" in Serial0data:
              xy6020ldata = b64decode(Serial0data["RxT"].encode('utf-8'))
              print(xy6020ldata)
              if xy6020ldata[1] == self.XY6020L.FC['write'] or xy6020ldata[1] == self.XY6020L.FC['writemore']:
                self.timeingwait = False
              elif xy6020ldata[1] == self.XY6020L.FC['read']:
                self.timeingwait = False
                lastdecoded = self.XY6020L.todict(xy6020ldata)
                if not self.XY6020L.issame(lastdecoded) or (now() - 120 > last):
                  lastdecoded['online'] = True
                  self.publisher(self.topic, dumps(lastdecoded))
                  last = now()
          else:
            logger.info("%s %s %s",msg.id, msg.event, msg.data)
            self.publisher(self.topic, dumps(lastdecoded))
      except TimeoutError:
        logger.warning("No Data from XY6020L while the last %s seconds.", self.c["ssetimeout"])
      except exceptions.HTTPError:
        logger.warning("HTTP Error by establishing the SSE connect.")        
      except Exception as error:
        logger.warning("Unexpected error %s ocures.", type(error).__name__)
        traceback.print_exc()
      hadtried = None
    self.ESPxy6020l.close()
    if self.timeing.is_alive():
      self.timeingwait = False
      self.timeing.join()
      logger.info("Stopping timer %s", self.topic)
    logger.info("Stopping worker %s", self.topic)
    return True

def mkreadyforxy6020l(ESPxy6020l, baudrate, loopback=False):
  Ser0set = {"baud": baudrate, "config": "8N1", "loopback": False, "debug": False, "outBufSize": 2000}
  res = None
  if not ESPxy6020l.focall('serial', expect=200):
    return False
  if (ESPxy6020l.responce.json()["Serial0"]["TxTmoved"]):
    if not ESPxy6020l.focall('serial', 'PATCH', {"move": "TxT"}):
      return False
    res = True
  if (ESPxy6020l.responce.json()["Serial0"]["swaped"]):
    if not ESPxy6020l.focall('serial', 'PATCH', {"move": "swap"}):
      return False
    res = True
  if ((ESPxy6020l.responce.json()["Serial0"]["baud"] != baudrate) or
      ESPxy6020l.responce.json()["Serial0"]["loopback"] or
      (ESPxy6020l.responce.json()["outBufSize"] != 2000)):
    if not ESPxy6020l.focall('serial', 'PATCH', Ser0set):
      return False
    if ESPxy6020l.responce.status_code != 201:
      logger.error("Status: %s -> Msg: %s", ESPxy6020l.responce.status_code, ESPxy6020l.responce.json()["msg"])
      return False
    res = True
  if not ESPxy6020l.responce.json()["SSE"]:
    if not ESPxy6020l.focall('', 'PUT', {}):
      return False
    if ESPxy6020l.responce.status_code != 201:
      logger.error("Status: %s -> Msg: %s", ESPxy6020l.responce.status_code, ESPxy6020l.responce.json()["msg"])
      return False
    res = True
  return res