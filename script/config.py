from json import load
from os import path, getcwd, environ

def config():
  CONFIG = {} 
  tempfile = path.join(getcwd(),"config", "settings.json")
  if path.exists(tempfile):
    with open(tempfile,'r') as file:
      CONFIG = load(file)

  return CONFIG

def secrets():
  SECRETS = {} 
  tempfile = path.join(getcwd(),"config", "secrets.json")
  if path.exists(tempfile):
    with open(tempfile,'r') as file:
      SECRETS = load(file)
      
  return SECRETS