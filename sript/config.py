import json
from os import path, environ

def config():
  CONFIG = {} 
  tempfile = "config/settings.json"
  if path.exists(tempfile):
    with open(tempfile,'r') as file:
      CONFIG = json.load(file)

  return CONFIG