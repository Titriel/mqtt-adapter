from time import sleep, time as now
from datetime import date
from datetime import timedelta
from json import loads, dumps
from base64 import b64decode
from math import floor
from sseclient import SSEClient
from requests import exceptions
from os import path, getcwd
from sys import path as PATH
PATH.append(path.join(getcwd(), "script"))
PATH.append(path.join(getcwd(), "devices", "ESPrestMeter"))
import logging
from logsetup import d2s, pretty as logpretty
from SML import check, set_time_offset, getTelegramm, pretty
import ESPrest
import traceback

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
    logger.info("do init the device %s", d2s(config))

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
      if len(self.buffer) == 0:
        return
      
  def worker(self):
    logger.info("This is my worker %s", self.topic)
    ESPmeter = ESPrest.set(self.c["ip"], self.c["token"])

    hadtried = False
    lastdecoded = {}
    while (self.workerrunning):
      ESPmeter.open()
      state = mkreadyformeter(ESPmeter, 9600, self.c["loopback"])
      ESPmeter.close()
      if state == hadtried:
        logger.warning("No Stream vom meter.")
        lastdecoded['online'] = False
        self.publisher(self.topic, dumps(lastdecoded))        
      try:
        messages = SSEClient('http://' + self.c["ip"] + '/events', auth=(self.c["sseUser"],self.c["ssePass"]), timeout=self.c["ssetimeout"])
        for msg in messages:
          if not self.workerrunning:
            break
          if msg.event == "Serial0":
            jetzt = floor(now() + 0.5)
            Serial0data = loads(msg.data)
            Meterdata = b64decode(Serial0data["RxT"].encode('utf-8'))
            #print(Meterdata)
            Telegramms = check(Meterdata)
            for Telegramm in Telegramms:
              logger.info("Telegram: %s", d2s(Telegramm))
              last_Telegramm = getTelegramm(Telegramm['Start'], Meterdata)
              #print(last_Telegramm)
              lastdecoded = last_Telegramm['decoded']
            if self.day != date.today():
              set_time_offset(lastdecoded['Server_ID']['bytes'], now() - lastdecoded['actSensorTime']['raw'])
              self.day = date.today()
            del lastdecoded['Server_ID']['bytes']
            lastdecoded['actSensorTime']['hr'] = str(lastdecoded['actSensorTime']['hr']).split('.')[0]
            lastdecoded['online'] = True
            self.publisher(self.topic, dumps(lastdecoded))
          else:
            logger.info("%s %s %s",msg.id, msg.event, msg.data)
      except TimeoutError:
        logger.warning("No Data from meter while the last %s seconds.", self.c["ssetimeout"])
      except exceptions.HTTPError:
        logger.warning("HTTP Error by establishing the SSE connect.")        
      except Exception as error:
        logger.warning("Unexpected error %s ocures.", type(error).__name__)
        traceback.print_exc()
      hadtried = None

    logger.info("Stopping worker %s", self.topic)
    return True

def mkreadyformeter(ESPmeter, baudrate, loopback=False):
  Ser0set = {"baud": baudrate, "config": "8N1", "loopback": False, "debug": False, "outBufSize": 1000}
  Ser1set = {"useTxT1": True, "baud": baudrate, "config": "8N1", "loopback": loopback, "debug": False, "outBufSize": 1000}
  res = None
  if not ESPmeter.focall('serial', expect=200):
    return False
  if (ESPmeter.responce.json()["Serial0"]["TxTmoved"]):
    if not ESPmeter.focall('serial', 'PATCH', {"move": "TxT"}):
      return False
    res = True
  if (ESPmeter.responce.json()["Serial0"]["swaped"]):
    if not ESPmeter.focall('serial', 'PATCH', {"move": "swap"}):
      return False
    res = True
  if not ESPmeter.responce.json()["Serial1"]["enabeled"] and not ESPmeter.responce.json()["GPIO2used"]: # enabeled zu enabled nach ESP-Update
    if not ESPmeter.focall('serial', 'PATCH', Ser1set):
      return False
    if ESPmeter.responce.status_code != 201:
      logger.error("Status: %s -> Msg: %s", ESPmeter.responce.status_code, ESPmeter.responce.json()["msg"])
      return False
    res = True
  elif not ESPmeter.responce.json()["Serial1"]["enabeled"]: # enabeled zu enabled nach ESP-Update
    logger.error("GPIO2 is used by another component.")
    return False
  if (ESPmeter.responce.json()["Serial1"]["baud"] != baudrate) or (ESPmeter.responce.json()["Serial1"]["loopback"] != loopback):
    if not ESPmeter.focall('serial', 'PATCH', Ser1set):
      return False
    if ESPmeter.responce.status_code != 201:
      logger.error("Status: %s -> Msg: %s", ESPmeter.responce.status_code, ESPmeter.responce.json()["msg"])
      return False
    res = True
  if ((ESPmeter.responce.json()["Serial0"]["baud"] != baudrate) or
      ESPmeter.responce.json()["Serial0"]["loopback"] or
      (ESPmeter.responce.json()["outBufSize"] != 1000)):
    if not ESPmeter.focall('serial', 'PATCH', Ser0set):
      return False
    if ESPmeter.responce.status_code != 201:
      logger.error("Status: %s -> Msg: %s", ESPmeter.responce.status_code, ESPmeter.responce.json()["msg"])
      return False
    res = True
  if not ESPmeter.responce.json()["SSE"]:
    if not ESPmeter.focall('', 'PUT', {}):
      return False
    if ESPmeter.responce.status_code != 201:
      logger.error("Status: %s -> Msg: %s", ESPmeter.responce.status_code, ESPmeter.responce.json()["msg"])
      return False
    res = True
  return res