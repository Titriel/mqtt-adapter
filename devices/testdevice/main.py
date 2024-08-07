from os import path, getcwd
from sys import path as PATH
PATH.append(path.join(getcwd(),"script"))
import logging
from logsetup import d2s, pretty
from time import sleep

logger = logging.getLogger()
pretty()

class device:
  def __init__(self, config, topic, publisher):
    self.topic = topic
    self.publisher = publisher
    self.buffer = []
    self.workerrunning = False
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
    while (self.workerrunning):
      self.publisher(self.topic, '{"Plug1":"OFF", "Plug2":"ON"}')
      sleep(2)
      self.publisher(self.topic, '{"Plug1":"ON", "Plug2":"OFF"}')
      sleep(2)
      #self.workerrunning = False   
    logger.info("Stopping worker %s", self.topic)
    return True