from crccheck.crc import Crc16X25
from time import mktime
from datetime import datetime

SMLtable= {
  'timeoffset': {
    b'\t\x01ESY\x11\x03\xa1\x1aw': mktime((2018, 5, 17, 16, 43, 32, 1, 48, 0))
  },
  'tag': {
    'Escape': b'\x1B\x1B\x1B\x1B',
    'V1Start': b'\x01\x01\x01\01',
    'End': b'\x00',
    'Close': b'\x1A'
  },
  'commands': {
    0x0101: 'getOpenResponse',
    0x0201: 'getCloseResponse',    
    0x0701: 'getListResponse'
  },
  'OBIS': {
    b'\x81\x81\xC7\x82\x03\xFF': 'Manufactor',
    b'\x81\x81\xC7\x82\x05\xFF': 'Public_Key',
    b'\x01\x00\x00\x00\x09\xFF': 'Server_ID',
    b'\x01\x00\x01\x08\x00\xFF': 'Total_Work',
    b'\x01\x00\x01\x08\x01\xFF': 'Work_T1',
    b'\x01\x00\x01\x08\x02\xFF': 'Work_T2',
    b'\x01\x00\x02\x08\x00\xFF': 'Total_Work_Inj',
    b'\x01\x00\x02\x08\x01\xFF': 'Work_T1_Inj',
    b'\x01\x00\x02\x08\x02\xFF': 'Work_T2_Inj',
    b'\x01\x00\x10\x07\x00\xFF': 'Total_Power',
    b'\x01\x00\x24\x07\x00\xFF': 'Power_L1',
    b'\x01\x00\x38\x07\x00\xFF': 'Power_L2',
    b'\x01\x00\x4C\x07\x00\xFF': 'Power_L3',
    b'\x01\x00\x20\x07\x00\xFF': 'Voltage_L1',
    b'\x01\x00\x34\x07\x00\xFF': 'Voltage_L2',
    b'\x01\x00\x48\x07\x00\xFF': 'Voltage_L3'
  },
  'unit': {
    0x1B: 'W',
    0x1E: 'Wh',
    0x23: 'V'
  },
  'mainframe':[
    'transactionId',
    'groupNo',
    'abortOnError',
    ['msg', -1, 0],
    'crc16',
    'end'
  ],
  'msg': {
    0x0101: [
      'codepage',
      'clientId',
      'reqFileId',
      'serverID',
      'refTime',
      'smlVersion'
    ],
    0x0201:[
      'globalSignature'
    ],
    0x0701:[
      'clientId',
      'serverID',
      'ListName',
      ['actSensorTime', 1, 0],
      ['OBISlist', 1, 0],
      'listSignature',
      'actGatewayTime'
    ]
  },
  'list': {
    'actSensorTime': [
      'choice',
      'secIndex'
    ],
    'OBISlist': [
      ['OBIS',0 , 0]
    ],
    'OBIS':[
      'OBISkey',
      'status',
      'valTime',
      'unit',
      'scaler',
      'value',
      'valueSignature',
    ]
  }
}


def check(data):
  t = SMLtable['tag']
  res = []
  End = 0
  while End != 6:
    Start = data.find(t['Escape']+t['V1Start'][0:1], End)
    End = data.find(t['End'] + t['Escape'] + t['Close'], Start) + 7
    if (Start < End) and (Start > -1):
      crccalc = Crc16X25.calc(data[Start:(End)])
      crc = int.from_bytes(data[End:(End+2)], 'little', signed=False)  
      res.append({'Start': Start, 'CRC_Ok': (crc==crccalc)})
  return res

def tryFindOBISkeys(c, data):
  while True:
    c = data.find(b'\x77\x07', c)
    if c == -1:
      break
    if data[c + 7] == 0xFF:
      f = SMLtable['list']['OBIS']
      OBIS = data[c + 2:c + 8]
      if OBIS in SMLtable['OBIS']:
        print('OBIS Kennzahl: ' + SMLtable['OBIS'][OBIS], end = ' -> Key: ')
      else:
        print('*** Die OBIS Kennzahl ist unbekannt ***', end = ' -> Key: ')
      c = c + 1
      res = {}
      for i in range(0, 7):
        decdata = decodedata(c, data)
        if not decdata['Ok']:
          return  decdata
        if i == 0:
          print (decdata['value'])
        else:
          res[f[i]] = decdata['value']
        c = decdata['c']
      print(res)
      if res['scaler'] is None:
        print(res['value'])
      else:
        if res['unit'] in SMLtable['unit']:
          unit = SMLtable['unit'][res['unit']]
        else:
          unit = '[unbekannte Einheit]'
        temp = str(res['value'])
        temp = temp[:res['scaler']] + ',' + temp[res['scaler']:] + ' ' + unit
        print(temp)
      print()

def getTelegramm(c, data):
  res = {'Ok': 'True', 'c': c, 'decoded':{}}
  t = SMLtable['tag']
  if data[c:c+4] == t['Escape']:
    if data[c+4:c+8] == t['V1Start']:
      res['Version'] = 'V1'
    else:
      res['Version'] = 'V2'
    c = c + 8

    flat = []
    while dformat(c, data)['h'] == 7:
      msg = getMsg(c, data)
      if not msg['Ok']:
        res['failed'] = msg
        res['Ok'] = False
        break
      if Crc16X25.calc(data[c:msg['c'] - 4]) != msg['data']['crc16']:
        res['failed'] = {'Ok': 'False', 'error': "Cheksummenfehler in der Nachricht"}
        res['Ok'] = False
      flat = flat + msg['flat']
      res[msg['data']['transactionId']] = msg['data']
      c = msg['c']
    res['c'] = c
    for satz in flat:
      for key in satz:
        res['decoded'][key] = satz[key]
  return res

def getMsg(c, data, d = 0, obj = []):
  res = {'Ok': 'True', 'data': {}, 'flat': [], 'c': c}
  if d == 0:
    f = SMLtable['mainframe']
  elif obj[1] == -1:
    f = SMLtable[obj[0]][obj[2]]
  elif obj[1] == 0:
    f = SMLtable['list'][obj[0]]
  else:
    f = SMLtable['list'][obj[0]]

  idf = dformat(c, data)
  c = idf['c']
  if idf['h'] == 7:
    j = 0
    for i in range(0, idf['l']):
      if type(f[i - j]) == str:
        decdata = decodedata(c, data, f[i - j])
        if not decdata['Ok']:
          return  decdata        
        res['data'][f[i - j]] = decdata['value']
        c = decdata['c']
      else:
        if f[i - j][1] == -1:
          decdata = decodedata(c + 1, data)
          if not decdata['Ok']:
            return  decdata
          f[i - j][2] = decdata['value']
          names = SMLtable['commands'][decdata['value']]
          block = getMsg(decdata['c'], data, d + 1, obj = f[i - j])
          if not block['Ok']:
            return block
          res['data'][names] = block['data']
          c = block['c']          
        elif f[i - j][1] == 0:
          decdata = decodedata(c + 1, data)
          if not decdata['Ok']:
            return  decdata          
          names = f[i - j][0]
          if decdata['value'] in SMLtable[names]:          
            block = getMsg(c, data, d + 1, obj = f[i - j])
            if not block['Ok']:
              return block
            res['data'][SMLtable[names][decdata['value']]] = block['data']
            c = block['c']
            j = j + 1
          else:
            i = i - 1
            j = j - 1
        else:
          block = getMsg(c, data, d + 1, obj = f[i])
          if not block['Ok']:
            return block
          names = f[i - j][0]
          res['data'][f[i - j][0]] = block['data']
          c = block['c']
  else: 
    res = {'Ok': 'False', 'error': "Unerwartete Blockstruktur"}
  res['c'] = c
  try:
    res['flat'] = block['flat'] + calcflat(block['data'], names)
  except:
    pass
  return res

def dformat (c, data):
  res ={'h': (data[c] // 16) & 7, 'l': 0}
  while True:
    res['l'] = res['l'] * 16 + (data[c] & 15)
    c = c + 1
    if data[c - 1] < 128:
      break
  res['c'] = c
  return res

def decodedata(c, data, names = ''):
  res = {'Ok': 'False'}
  idf = dformat(c, data)
  c = idf['c']
  if idf['h'] == 0:
    if idf['l'] == 0:
      res['value'] = True
      c = c + 1 
    elif idf['l'] == 1:
      res['value'] = None
    else:
      res['value'] = data[c:(c+idf['l']-1)]
  elif idf['h'] == 4:
    pass
  elif idf['h'] == 5:
    res['value'] = int.from_bytes(data[c:(c+idf['l']-1)], 'big', signed=True)
  elif idf['h'] == 6:
    if names == 'crc16':
      res['value'] = int.from_bytes(data[c:(c+idf['l']-1)], 'little', signed=False)
    else:
      res['value'] = int.from_bytes(data[c:(c+idf['l']-1)], 'big', signed=False)
  elif idf['h'] == 7:
    pass
  else:
    pass
  if 'value' in res:
    res['Ok'] = True
    res['c'] = c+idf['l']-1
  else:
    res['error': 'Unerwarteter Datentyp']
  return res

def calcflat(data, names):
  res = []
  if names == 'OBISlist':
    for key in data:
      if key == 'Manufactor':
        res.append({key: data[key]['value'].decode('utf8')})
      elif key == 'Server_ID':
        b = data[key]['value']
        if res[0]['Manufactor'] == 'ESY':
          temp = str(int.from_bytes(b[6:], 'big', signed=False))
          temp = ' ' + temp[:4] + ' ' + temp[4:]
          temp = hex(b[1]).replace('0x', '')+ ' ' + b[2:5].decode('utf8') + hex(b[5]).replace('0x', ' ') + temp
          res.append({'Key': temp})
        hexd = ''
        for byte in b:
          hexd = hexd + (hex(byte).replace('x', '')+ ' ')[-3:]
        res.append({key: {"hr": hexd, "bytes": b}})
      #elif d['scaler'] is None:
        #res.append({key: d['value']})
      else:
        d = data[key]
        #temp = str(d['value'] * pow(10, d['scaler'])) + ' ' + SMLtable['unit'][d['unit']]
        temp = str(d['value'])
        if d['scaler'] < 0:
          temp = temp[:d['scaler']] + ',' + temp[d['scaler']:]
          ddec = round(d['value'] * pow(10, d['scaler']), - d['scaler'])
        else:
          temp += '0' * d['scaler']
          ddec = d['value'] * pow(10, d['scaler']) 
        temp += ' ' + SMLtable['unit'][d['unit']]
        res.append({key: {"hr": temp, "value": ddec, "unit": SMLtable['unit'][d['unit']]}})
  elif names == 'getListResponse':
    res.append({'actSensorTime': {"hr": datetime.fromtimestamp(data['actSensorTime']['secIndex'] + SMLtable['timeoffset'][data['serverID']]),
                                  "raw": data['actSensorTime']['secIndex'], "offset": SMLtable['timeoffset'][data['serverID']]}})
  return res

def set_time_offset(serverID, offset):
  SMLtable['timeoffset'][serverID] = offset

def pretty(d, indent=0):
  for key, value in d.items():
    print('\t' * indent, end = '')
    print(key, end = ': ')
    if isinstance(value, dict):
      print()
      pretty(value, indent+1)
    else:
      #print('\t' * (indent+1), end = '')
      print(value)