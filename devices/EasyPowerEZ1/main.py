from os import path, getcwd
from sys import path as PATH
PATH.append(path.join(getcwd(),"script"))
import logging
from logsetup import d2s, pretty
from json import dumps
from requests import get
from time import sleep

logger = logging.getLogger()
pretty()

class device:
  def __init__(self, config, topic, publisher):
    self.topic = topic
    self.publisher = publisher
    self.buffer = []
    self.workerrunning = False
    self.c = config
    self.url = lambda path:'http://' + self.c["ip"] + ':' + self.c["port"] + '/' + path
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
    res = {}
    while (self.workerrunning):
      responce = None
      try:
        responce = get(self.url('getOutputData'), timeout= int(round(self.c["interval"] / 2)))
      except:
        if 'data' in res:
          res['data']['online'] = False
          self.publisher(self.topic, dumps(res['data']))
        else:
          logger.info("EZ1 on %s:%s is not reatchabel.", self.c["ip"], self.c["port"])
      if responce is not None:
        res = responce.json()
        if res is not None and 'message' in res and (res['message'] == 'SUCCESS'):
          res['data']['online'] = True
          res['data']['deviceId'] = res['deviceId']
          self.publisher(self.topic, dumps(res['data']))
        else:
          logger.warning("Error on EZ1 %s", d2s(res))
      sleep(self.c["interval"]) 
    logger.info("Stopping worker %s", self.topic)
    return True