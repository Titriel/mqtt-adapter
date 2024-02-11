from time import sleep

class device:
  def __init__(self, config, topic, publisher):
    self.topic = topic
    self.publisher = publisher
    self.workerrunning = False
    print("do init the device", config)

  def on_massage(self, topic, payload, retain):
    print("This is my worker", self.topic)
    sleep(2)
    print("Received message for topic", topic, ":", payload)
    if retain==1:
      print("This is a retained message")

  def worker(self):
    print("This is my worker", self.topic)
    while (self.workerrunning):
      self.publisher(self.topic, '{"Plug1":"OFF", "Plug2":"ON"}')
      sleep(2)
      self.publisher(self.topic, '{"Plug1":"ON", "Plug2":"OFF"}')
      sleep(2)
      #self.workerrunning = False   
    print("Stopping worker", self.topic)
    return True