from os import path, getcwd
from sys import path as PATH
PATH.append(path.join(getcwd(),"script"))
import logging
from logsetup import d2s, pretty
from requests import get, post, delete, put, patch
from time import time as now
from hashlib import md5 as md5byte
from json import dumps
from math import floor
from typing import Any, Union, Literal

logger = logging.getLogger()
md5 = lambda text:md5byte(text.encode('utf8')).hexdigest()

class set:
  """
  Setting up the class for an ESPrest.
  Warning: Don't use over public networks. 

  Args:
    ip (str): The IP-adress of the ESP, if an DNS has a name so it is also possible.
    token (str): Default in ESP is admin@admin the token must have an @ on any place.

  Returns:
    The instance of the class for the given ESPrest
  """  
  def __init__(self, ip:str, token:str):
    self.ip = ip
    self.hash = md5(token)
    self.hdfrom = ""
    self.rq = {'GET': get, 'POST': post, 'PUT': put, 'PATCH': patch, 'DELETE': delete}
    self.auth = ""
    self.url = lambda path:'http://' + self.ip + '/' + path
    self.isOpen = False
    self.responce = None

  def call(self, path:str = "", methode:Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET", content:dict = {}):
    """
    Sends a RESTcall to the ESP.
    - Creats the autorisation depending on the RESTcall.
    - Adds a Timestamp of the call in the header.

    Args:
      path (str): Only the path to the object, without leading and ending /.
      methode (Literal): The http-methode "GET", "POST", "PUT", "PATCH" or "DELETE"
      content (dict): A json compatieble dict for "POST", "PUT", "PATCH"
      
    Returns:
      see in .responce
    """
    headers = {"From": self.hdfrom}
    headers["X-UTC"] = str(floor(now()))
    if (path == "") and (methode == "GET"):
      headers["X-Auth"] = md5(self.hash + self.hdfrom)
    else:
      headers["X-Auth"] = self.auth
    if (methode == "POST") or (methode == "PUT") or (methode == "PATCH"):
      headers["Content-Type"] = "application/json"
      self.responce = self.rq[methode](self.url(path), data=dumps(content), headers=headers)
    else:
      self.responce = self.rq[methode](self.url(path), headers=headers)
    try:
      self.auth = md5(self.responce.json()['UUID'] + self.hash)
      logger.info("%s", self.responce.json()["msg"])
      if (self.responce.json()['msg'] == "Session deleted.") or (self.responce.json()['msg'] == "From is peregistert.") or (self.responce.status_code == 401):
        self.isOpen = False
      if self.responce.json()['msg'] == "Session established.":
        self.isOpen = True
    except:
      self.auth = ""

  def focall(self, path:str = "", methode:Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET", content:dict = {}):
    """
    Sends a RESTcall to the ESP and force openeing a session.
    - If a session is open, the call will be immediately executed.
    - If no session is estblished, one will be open and will be closed after execution.
    - If a session should be open, but the ESP had closed, it will be reopened.

    Args:
      path (str): Only the path to the object, without leading and ending /.
      methode (Literal): The http-methode "GET", "POST", "PUT", "PATCH" or "DELETE"
      content (dict): A json compatieble dict for "POST", "PUT", "PATCH"

    Returns:
      see in .responce
    """    
    if self.isOpen:
      self.call(path, methode, content)
      if self.responce.status_code == 401:
        self.open()
        if self.responce.status_code == 201:
          self.call(path, methode, content)
        else:
          logger.warning("Can not open ESP: %s Status: %s", self.responce.json()['msg'], self.responce.status_code)
    else:
      self.open()
      if self.responce.status_code == 201:
        self.call(path, methode, content)
        self.close()         
      else:
        logger.warning("Can not open ESP: %s Status: %s", self.responce.json()['msg'], self.responce.status_code)

  def open(self):
    """
    Open a session on the ESP.

    Returns:
      see in .responce
    """
    self.call()
    if self.hdfrom == "":
      self.hdfrom = self.responce.json()['UUID'][:8]
      self.call()
    else:
      if self.responce.status_code == 401:
        self.hdfrom = ""
        self.open()
    if self.responce.status_code != 201:
      logger.warning("Can not open ESP: %s Status: %s", self.responce.json()['msg'], self.responce.status_code)

  def close(self):
    """
    Close the aktive session on the ESP.

    Returns:
      see in .responce
    """    
    self.call(methode = 'DELETE')
    self.hdfrom = ""

  def LSI(self, status:Union[int, bool]):
    """
    Sets the LED-Status-Indicator (LSI).
    - Byte (0-255) Blink coded output (three Digits build by adding 'long' + 5, 'short' + 1 . Dubbel long means 0 ).
    - False LSI goes permanently off.
    - True LSI goes permanently on

    Args:
      status (int, bool): The status what should shown.

    Returns:
      see in .responce
    """
    if type(status) == int:
      if status < 0:
        status = 0
      elif status > 255:
        status = 255
      self.focall('digital', 'PATCH', {"LSI": status})
    elif type(status) == bool:
      self.focall('digital', 'PATCH', {"LSIon": status})