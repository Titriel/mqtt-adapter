from modbus_crc import add_crc, check_crc
from json import dumps, loads

class XY6020L:
  def __init__(self, slaveadr = 1, rstart = 0, rcount = 6):
    self.slaveadr = slaveadr
    self.rstart = rstart
    self.lastrstart = rstart
    self.rcount = rcount
    self.lastdata = {}
    self.lastTS = None
    self.wanted = ['V-SET', 'I-SET', 'VOUT', 'IOUT', 'POWER', 'UIN']
    self.FC = {'read': 3, 'write': 6, 'writemore': 16}
    self.REG = {'V_SET': {'adr': 0, 'we': True,  'bytes': 2, 'dec': 2, 'signed': False, 'unit': 'V'}, #Soll Ausgangsspannung max
                'I_SET': {'adr': 1, 'we': True,  'bytes': 2, 'dec': 2, 'signed': False, 'unit': 'A'}, #Soll Ausgangsstrom max
                'VOUT':  {'adr': 2, 'we': False, 'bytes': 2, 'dec': 2, 'signed': False, 'unit': 'V'}, #Ist Ausgangsspannung
                'IOUT':  {'adr': 3, 'we': False, 'bytes': 2, 'dec': 2, 'signed': False, 'unit': 'A'}, #Ist Ausgangsstrom
                'POWER': {'adr': 4, 'we': False, 'bytes': 2, 'dec': 1, 'signed': False, 'unit': 'W'}, #Ist Ausgangsleistung
                'UIN':   {'adr': 5, 'we': False, 'bytes': 2, 'dec': 2, 'signed': False, 'unit': 'V'}, #Ist Eingangsspannung
                'AH_LOW':  {'adr': 6, 'we': False, 'bytes': 2, 'dec': 0, 'signed': False, 'unit': 'maH'},
                'AH_HIGH': {'adr': 7, 'we': False, 'bytes': 2, 'dec': 0, 'signed': False, 'unit': 'maH'},
                'WH_LOW':  {'adr': 8, 'we': False, 'bytes': 2, 'dec': 0, 'signed': False, 'unit': 'mwH'},
                'WH_HIGH': {'adr': 9, 'we': False, 'bytes': 2, 'dec': 0, 'signed': False, 'unit': 'mwH'},
                'OUT_H': {'adr': 10, 'we': False, 'bytes': 2, 'dec': 0, 'signed': False, 'unit': 'H'},
                'OUT_M': {'adr': 11, 'we': False, 'bytes': 2, 'dec': 0, 'signed': False, 'unit': 'M'},
                'OUT_S': {'adr': 12, 'we': False, 'bytes': 2, 'dec': 0, 'signed': False, 'unit': 'S'},
                'T_IN':  {'adr': 13, 'we': False, 'bytes': 2, 'dec': 1, 'signed': True, 'unit': 'F_C'},
                'T_EX':  {'adr': 14, 'we': False, 'bytes': 2, 'dec': 1, 'signed': True, 'unit': 'F_C'},
                'LOCK':  {'adr': 15, 'we': True,  'bytes': 2, 'dec': 0, 'signed': False, 'unit': [False, True]},
                'PROTECT': {'adr': 16, 'we': True, 'bytes': 2, 'dec': 0, 'signed': False, 'unit': [False, 'OVP', 'OCP', 'OPP', 'LVP', 'OAH', 'OHP', 'OTP', 'OEP', 'OWH', 'ICP']},
                'CVCC':  {'adr': 17, 'we': False, 'bytes': 2, 'dec': 0, 'signed': False, 'unit': ['CV', 'CC']},
                'ONOFF': {'adr': 18, 'we': True,  'bytes': 2, 'dec': 0, 'signed': False, 'unit': ['OFF', 'ON']},
                'F_C':   {'adr': 19, 'we': True,  'bytes': 2, 'dec': 0, 'signed': False, 'unit': ['C', 'F']},
                'B_LED': {'adr': 20, 'we': True,  'bytes': 2, 'dec': 0, 'signed': False, 'unit': None},
                'SLEEP': {'adr': 21, 'we': True,  'bytes': 2, 'dec': 0, 'signed': False, 'unit': 'M'},
                'MODEL': {'adr': 22, 'we': False, 'bytes': 2, 'dec': 0, 'signed': False, 'unit': None},
                'VERSION': {'adr': 23, 'we': False, 'bytes': 2, 'dec': 0, 'signed': False, 'unit': None},
                'SLAVE-ADD': {'adr': 24, 'we': True, 'bytes': 2, 'dec': 0, 'signed': False, 'unit': None},
                'BAUDRATE_L': {'adr': 25, 'we': True, 'bytes': 2, 'dec': 0, 'signed': False, 'unit': 'BAUD'},
                'T_IN_OFFSET': {'adr': 26, 'we': True, 'bytes': 2, 'dec': 1, 'signed': True, 'unit': 'F_C'},
                'T_EX_OFFSET': {'adr': 27, 'we': True, 'bytes': 2, 'dec': 1, 'signed': True, 'unit': 'F_C'},
                'BUZZER': {'adr': 28, 'we': True, 'bytes': 2, 'dec': 0, 'signed': False, 'unit': [False, True]},
                'EXTRACT-M': {'adr': 29, 'we': True, 'bytes': 2, 'dec': 0, 'signed': False, 'unit': None},
                'DEVICE': {'adr': 30, 'we': True, 'bytes': 2, 'dec': 0, 'signed': False, 'unit': None}
              }
    mmask = {'V_SET': {'pos': 0, 'dec': 2, 'signed': False, 'unit': 'V'},
             'I_SET': {'pos': 1, 'dec': 2, 'signed': False, 'unit': 'A'},
             'S_LVP': {'pos': 2, 'dec': 2, 'signed': False, 'unit': 'V'},
             'S_OVP': {'pos': 3, 'dec': 2, 'signed': False, 'unit': 'V'},
             'S_OCP': {'pos': 4, 'dec': 2, 'signed': False, 'unit': 'A'},
             'S_OPP': {'pos': 5, 'dec': 0, 'signed': False, 'unit': 'W'},
             'S_OHP_H': {'pos': 6, 'dec': 0, 'signed': False, 'unit': 'H'},
             'S_OHP_M': {'pos': 7, 'dec': 0, 'signed': False, 'unit': 'M'},
             'S_OAH_L': {'pos': 8, 'dec': 0, 'signed': False, 'unit': 'maH'},
             'S_OAH_H': {'pos': 9, 'dec': 0, 'signed': False, 'unit': 'maH'},
             'S_OWH_L': {'pos': 10, 'dec': -1, 'signed': False, 'unit': 'mwH'},
             'S_OWH_H': {'pos': 11, 'dec': -1, 'signed': False, 'unit': 'mwH'},
             'S_OTP': {'pos': 12, 'dec': 0, 'signed': True, 'unit': 'ForC'},
             'S_INI': {'pos': 13, 'dec': 0, 'signed': False, 'unit': None}
             }
    for i in range(0,10):
      for reg in mmask:
        self.REG[('M' + str(i) + '_' + reg)] = {'adr': (i * 16 + 80 + mmask[reg]['pos']), 'we': True, 'bytes': 2, 'dec': mmask[reg]['dec'], 'dec': mmask[reg]['signed'], 'unit': mmask[reg]['unit']}

    self.REGlabel = list(range(0,238))
    for reg in self.REG:
      self.REGlabel[self.REG[reg]['adr']] = reg
      if self.REG[reg]['we'] and type(self.REG[reg]['unit']) is list:
        self.REG[reg]['values'] = {}
        pos = 0
        for value in self.REG[reg]['unit']:
          self.REG[reg]['values'][value] = pos
          pos += 1
    self.wants = []
    wants = []
    for reg in self.REGlabel:
      if type(reg) is int:
        if len(wants) > 0:
          self.wants.append(wants)
          wants = []
      else:
        wants.append(reg)
    self.wants.append(wants)

  def getvalue(self, reg, value):  
    if 'values' in self.REG[reg]:
      if value not in self.REG[reg]['values']:
        return 0
      value = self.REG[reg]['values'][value]
    elif type(self.REG[reg]['unit']) is str:
      value = int(value * 10 ** self.REG[reg]['dec'])
    return value

  def set(self, data):
    if len(data) > 1:
      regs = list(range(0,239))
    for reg in data:
      if reg in self.REG and self.REG[reg]['we']:
        if len(data) > 1:
          regs[self.REG[reg]['adr']] = [reg, self.getvalue(reg, data[reg])]
        else:
          return [add_crc(bytes([self.slaveadr, self.FC['write']]) + self.REG[reg]['adr'].to_bytes(2, 'big') + self.getvalue(reg, data[reg]).to_bytes(2, 'big'))]
    startreg = 0
    commands = []
    command = b''
    for reg in regs:
      if type(reg) is list:
        if command == b'':
          command = startreg.to_bytes(2, 'big')
        command += reg[1].to_bytes(2, 'big')
      elif command == b'':
        pass
      else:
        if len(command) == 4:
          commands.append(add_crc(bytes([self.slaveadr, self.FC['write']]) + command))
        else:
          commands.append(add_crc(bytes([self.slaveadr, self.FC['writemore']]) + command[:2] + (int(len(command) / 2) - 1).to_bytes(2, 'big') + (len(command) - 2).to_bytes(1, 'big') + command[2:]))
        command = b''
      startreg += 1
    return commands
    
  def want(self, wanted = True):
    wantsets = {'HOLDING': 0, 'M0': 1, 'M1': 2, 'M2': 3, 'M3': 4, 'M4': 5, 'M5': 6, 'M6': 7, 'M7': 8, 'M8': 9, 'M9': 10}
    self.wanted = []
    maxreg = 0
    minreg = 238
    unitfc = False
    if wanted == True:
      wanted = self.REG
    elif type(wanted) == str:
      wanted = self.wants[wantsets[wanted]]
    for reg in wanted:
      self.wanted.append(reg)
      if type(self.REG[reg]['unit']) is str and self.REG[reg]['unit'] == 'F_C':
        unitfc = True
      if self.REG[reg]['adr'] > maxreg:
        maxreg = self.REG[reg]['adr']
      if self.REG[reg]['adr'] < minreg:
        minreg = self.REG[reg]['adr']
    if unitfc and 19 > maxreg:
      maxreg = 19
    if unitfc and 19 < minreg:
      minreg = 19
    self.rstart = minreg
    self.rcount = maxreg - minreg + 2

  def readcode(self, rstart = None, rcount = None, reini = False):
    if rstart is None:
      rstart = self.rstart
    if rcount is None:
      rcount = self.rcount
    if reini:
      self.rstart = rstart
      self.rcount = rcount
    self.lastrstart = rstart
    return add_crc(bytes([self.slaveadr, self.FC['read']]) + rstart.to_bytes(2, 'big') + rcount.to_bytes(2, 'big'))
  
  def todict(self, data, rstart = None):
    if rstart is None:
      rstart = self.lastrstart
    if not check_crc(data):
      return {}
    if data[0] == self.slaveadr:
      if data[1] == self.FC['read']:
        readpos = 3
        responce = {}
        unit = None
        while readpos < len(data) - 5:
          register = self.REGlabel[rstart]
          byts2get = self.REG[register]['bytes']
          if register in self.wanted:
            if self.REG[register]['dec'] == 0:
              responce[register] = {'value': int.from_bytes(data[readpos:(readpos + byts2get)], 'big', signed=self.REG[register]['signed'])}
            else:
              responce[register] = {'value': round(int.from_bytes(data[readpos:(readpos + byts2get)], 'big', signed=self.REG[register]['signed']) * 0.1 ** self.REG[register]['dec'], self.REG[register]['dec'])}
            if type(self.REG[register]['unit']) is str:
              responce[register]['unit'] = self.REG[register]['unit']
          if register == 'F_C':
            if int.from_bytes(data[readpos:(readpos + byts2get)], 'big', signed=self.REG[register]['signed']) == 0:
              unit = '°C'
            else:
              unit = '°F'            
          readpos += byts2get
          rstart += 1
        if unit is not None:
          for reg in responce:
            if 'unit' in responce[reg] and responce[reg]['unit'] == 'F_C':
              responce[reg]['unit'] = unit
        for reg in responce:
          if type(self.REG[reg]['unit']) is list:
            value = responce[reg]['value']
            responce[reg] = self.REG[reg]['unit'][value]
          elif self.REG[reg]['unit'] is None:
            value = responce[reg]['value']
            responce[reg] = value
        if 'OUT_H' in responce and 'OUT_M' in responce and 'OUT_S' in responce:
          responce['OUT'] = str(responce['OUT_H']['value']) + ':' + str(responce['OUT_M']['value']) + ':' + str(responce['OUT_S']['value'])
          self.lastTS = responce['OUT_H']['value'] * 3600 + responce['OUT_M']['value'] * 60 + responce['OUT_S']['value']
          del responce['OUT_H'], responce['OUT_M'], responce['OUT_S']
        else:
          self.lastTS = None
        if 'AH_LOW' in responce and 'AH_HIGH' in responce:
          responce['AH'] = responce['AH_LOW']
          responce['AH']['value'] += responce['AH_HIGH']['value'] * 2 ** 16
          del responce['AH_LOW'], responce['AH_HIGH']
        if 'WH_LOW' in responce and 'WH_HIGH' in responce:
          responce['WH'] = responce['WH_LOW']
          responce['WH']['value'] += responce['WH_HIGH']['value'] * 2 ** 16
          del responce['WH_LOW'], responce['WH_HIGH']
        return responce
      else:
        return {}  
    else:
      return {}
  
  def issame(self, datanew, withTS=False, update=True, dataold=None):
    if dataold is None: 
      dataold = self.lastdata
      
    if withTS == False and 'OUT' in dataold:
      dataoldc = loads(dumps(dataold))
      del dataoldc['OUT']
      jdataold = dumps(dataoldc)
    else:
      jdataold = dumps(dataold)

    if withTS == False and 'OUT' in datanew:
      datanewc = loads(dumps(datanew))
      del datanewc['OUT']
      jdatanew = dumps(datanewc)
    else:
      jdatanew = dumps(datanew)

    if update:
      self.lastdata = loads(dumps(datanew))
    #print(jdataold)
    #print(jdatanew)
    #print(jdataold == jdatanew)
    return (jdataold == jdatanew)