from os import path, getcwd
from sys import path as PATH
PATH.append(path.join(getcwd(),"script"))
import logging
from logsetup import d2s, pretty
from json import dumps, loads
from time import sleep

logger = logging.getLogger()
pretty()

class device:
  def __init__(self, config, topic, publisher):
    self.topic = topic
    self.publisher = publisher
    self.buffer = []
    self.res = {}
    self.workerrunning = False
    self.loops = 0
    self.c = config
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

      if retain==1:
        logger.info("This is a retained message")
      try:
        decoded = loads(payload)
      except:
        logger.info("No relevant data in massage %s: %s", topic, payload)
        return
      
      if "online" in decoded and decoded["online"]:
        if self.loops % self.c['summarize'] == 0:
          self.res = loads(payload)
        else:
          for key in self.c['topics']:
            self.res[key]["value"] += decoded[key]["value"]
        if self.loops % self.c['summarize'] == self.c['summarize'] - 1:
          for key in decoded:
            if key in self.c['topics']:
              self.res[key]["value"] /= self.c['summarize']
              digits = len(self.res[key]["hr"].split(" ")[0].split(",")[1])
              self.res[key]["value"] = round(self.res[key]["value"], digits)
              self.res[key]["hr"] = str(self.res[key]["value"]) + " " + self.res[key]["unit"]
            else:
              self.res[key] = decoded[key]
          self.publisher(self.topic, dumps(self.res))
          logger.info("Dump: %s: %s", topic, dumps(self.res))
      elif self.loops % self.c['summarize'] == self.c['summarize'] - 1:
        self.publisher(self.topic, dumps(decoded))
        logger.info("%s: %s", self.topic, dumps(decoded))
      self.loops += 1
      if len(self.buffer) == 0:
        return
      
  def worker(self):
    logger.info("This is my worker %s", self.topic)
    while (self.workerrunning):
      sleep(2)  
    logger.info("Stopping worker %s", self.topic)
    return True