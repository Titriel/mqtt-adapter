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
import traceback

logger = logging.getLogger()
md5 = lambda text:md5byte(text.encode('utf8')).hexdigest()
Tmethode = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
Tpath = Literal["", "config", "digital", "serial", "ds18b20"]

class set:
  """
  Setting up the class for an ESPrest.
  Warning: Don't use over public networks. 

  Args:
    ip (str): The IP-adress of the ESP, if an DNS has a name so it is also possible.
    token (str): Default in ESP is admin@admin the token must have an @ on any place.
    timeout (int): timeout for request, default is 10 seconds.
  Returns:
    The instance of the class for the given ESPrest
  """  
  def __init__(self, ip:str, token:str, timeout:int=10):
    self.ip = ip
    self.hash = md5(token)
    self.timeout = timeout
    self.hdfrom = ""
    self.rq = {'GET': get, 'POST': post, 'PUT': put, 'PATCH': patch, 'DELETE': delete}
    self.auth = ""
    self.url = lambda path:'http://' + self.ip + '/' + path
    self.isOpen = False
    self.responce = None

  def reqesp(self, methode:Tmethode, path:Tpath, headers:dict, content:dict):
    """
    Sends the given REST request to the ESP.

    Args:
      methode (Literal): The http-methode "GET", "POST", "PUT", "PATCH" or "DELETE".
      path (Literal): Only the path to the object, without leading and ending / eg. "", "config", "digital", "serial", "ds18b20".
      headers (dict): The http headers for the request.
      content (dict): A json compatieble dict for "POST", "PUT", "PATCH".
      
    Returns:
      see in .responce.
      Itself is True if success else is False.
    """    
    try:
      if (methode == "POST") or (methode == "PUT") or (methode == "PATCH"):
        headers["Content-Type"] = "application/json"
        self.responce = self.rq[methode](self.url(path), data=dumps(content), headers=headers, timeout=self.timeout)
      else:
        self.responce = self.rq[methode](self.url(path), headers=headers, timeout=self.timeout)
      return True
    except Exception as error:
      logger.warning(type(error).__name__)
      return False

  def call(self, path:Tpath = "", methode:Tmethode = "GET", content:dict = {}):
    """
    Sends a RESTcall to the ESP.
    - Creats the autorisation depending on the RESTcall.
    - Adds a Timestamp of the call in the header.

    Args:
      path (Literal): Only the path to the object, without leading and ending / eg. "", "config", "digital", "serial", "ds18b20".
      methode (Literal): The http-methode "GET", "POST", "PUT", "PATCH" or "DELETE".
      content (dict): A json compatieble dict for "POST", "PUT", "PATCH".
      
    Returns:
      see in .responce and .isOpen.
      Itself is True if success else is False.
    """
    headers = {"From": self.hdfrom}
    headers["X-UTC"] = str(floor(now()))
    if (path == "") and (methode == "GET"):
      headers["X-Auth"] = md5(self.hash + self.hdfrom)
    else:
      headers["X-Auth"] = self.auth
    if not self.reqesp(methode, path, headers, content):
      self.responce = None
      return False
    try:
      self.auth = md5(self.responce.json()['UUID'] + self.hash)
      logger.info("%s", self.responce.json()["msg"])
      if (self.responce.json()['msg'] == "Session deleted.") or (self.responce.json()['msg'] == "From is peregistert.") or (self.responce.status_code == 401):
        self.isOpen = False
      if self.responce.json()['msg'] == "Session established.":
        self.isOpen = True
      return True
    except:
      self.auth = ""
      return False
    
  def focall(self, path:Tpath = "", methode:Tmethode = "GET", content:dict = {}, expect:Union[None, int]=None):
    """
    Sends a RESTcall to the ESP and force openeing a session.
    - If a session is open, the call will be immediately executed.
    - If no session is estblished, one will be open and will be closed after execution.
    - If a session should be open, but the ESP had closed, it will be reopened.

    Args:
      path (Literal): Only the path to the object, without leading and ending / eg. "", "config", "digital", "serial", "ds18b20".
      methode (Literal): The http-methode "GET", "POST", "PUT", "PATCH" or "DELETE"
      content (dict): A json compatieble dict for "POST", "PUT", "PATCH"
      expect (None, int): If it is not None, returns False if given value matchts not the statuscode  

    Returns:
      see in .responce and .isOpen.
      Itself is True if success else is False.
    """
    try:    
      if self.isOpen:
        if not self.call(path, methode, content):
          return False
        if self.responce.status_code == 401:
          if not self.open():
            return False
          if self.responce.status_code == 201:
            if not self.call(path, methode, content):
              return False
            if expect is not None and (self.responce.status_code != expect):
              return False
          else:
            logger.warning("Can not open ESP: %s Status: %s", self.responce.json()['msg'], self.responce.status_code)
            return False
      else:
        if not self.open():
          return False
        if self.responce.status_code == 201:
          if not self.call(path, methode, content):
            return False
          if expect is not None and (self.responce.status_code != expect):
            return False        
          self.close()         
        else:
          logger.warning("Can not open ESP: %s Status: %s", self.responce.json()['msg'], self.responce.status_code)
          return False
      self.responce.json()
      return True
    except Exception as error:
      logger.warning("Unexpected error %s ocures.", type(error).__name__)
      traceback.print_exc()
      return False

  def open(self):
    """
    Open a session on the ESP.

    Returns:
      see in .responce.
      Itself is True if success else is False.      
    """
    if not self.call():
      return False
    if self.hdfrom == "":
      self.hdfrom = self.responce.json()['UUID'][:8]
      if not self.call():
        return False
    else:
      if self.responce.status_code == 401:
        self.hdfrom = ""
        if not self.call():
          return False
    if self.responce.status_code != 201:
      logger.warning("Can not open ESP: %s Status: %s", self.responce.json()['msg'], self.responce.status_code)
    return True

  def close(self):
    """
    Close the aktive session on the ESP.

    Returns:
      see in .responce.
      Itself is True if success else is False.      
    """    
    if not self.call(methode = 'DELETE'):
      return False
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
      Itself is True if success else is False.
    """
    if type(status) == int:
      if status < 0:
        status = 0
      elif status > 255:
        status = 255
      return self.focall('digital', 'PATCH', {"LSI": status})
    elif type(status) == bool:
      return self.focall('digital', 'PATCH', {"LSIon": status})