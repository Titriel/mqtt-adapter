from os import path, getcwd
from sys import path as PATH
PATH.append(path.join(getcwd(),"script"))
import logging
from logsetup import d2s, pretty
from json import loads
from time import sleep
import mysql.connector

logger = logging.getLogger()
pretty()

class device:
  def __init__(self, config, topic, publisher):
    self.topic = topic
    self.publisher = publisher
    self.buffer = []
    self.workerrunning = False
    self.c = config
    self.loops = 1
    self.dbconnect = self.initdb()
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
      self.loops += 1
      if "Key" in decoded and "online" in decoded and decoded["online"]:
        self.entry(decoded["Key"].replace(' ', ''),
          (decoded['actSensorTime']['hr'],
            decoded['Total_Work']['value']*10000,
            decoded['Work_T1']['value']*10000,
            decoded['Work_T2']['value']*10000,
            decoded['Total_Power']['value']*100,
            decoded['Power_L1']['value']*100,
            decoded['Power_L2']['value']*100,
            decoded['Power_L3']['value']*100,
            decoded['Voltage_L1']['value']*10,
            decoded['Voltage_L2']['value']*10,
            decoded['Voltage_L3']['value']*10), (self.loops % 60 == 0))
      else:
        logger.info("No relevant data in massage %s: %s", topic, payload)
      if len(self.buffer) == 0:
        return
      
  def worker(self):
    logger.info("This is my worker %s", self.topic)
    while (self.workerrunning):
      sleep(2)  
    logger.info("Stopping worker %s", self.topic)
    return True
  
  def initdb(self):
    try:
      self.db = mysql.connector.connect(
      host=self.c['host'],
      user=self.c['user'],
      password=self.c['password'],
      database=self.c['database']
      )
      logger.info("Connectet to db on %s", self.c['host'])
      return True
    except:
      return False
    
  def entry(self, meter, val, commit):
    try:
      cursor = self.db.cursor()
      sql = "INSERT INTO " + meter + " (actSensorTime, Total_Work, Work_T1, Work_T2, Total_Power, Power_L1, Power_L2, Power_L3, Voltage_L1, Voltage_L2, Voltage_L3) "
      sql += "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
      cursor.execute(sql, val)
      if commit:
        #print('commit')
        self.db.commit()
        self.loops = 1
    except:
      logger.warning("Connectet to db on %s is lost, try reconnect", self.c['host'])
      self.initdb()