import json
import os
from myexception import MyException
from uibase import UiBase

class WebBridge(UiBase):
  MODES = ['buddies','dialog']
  
  def __init__(self):
    self.mode = 'buddies'
    self.currentDialog = None
    self.replacedDialog = None
    self.command = ''
    self.result = {'alert': 'hello'}
    super().__init__()
    
  async def parseRequest(self, req, inv):
    self.request = req
    self.query = req.query.copy()
    #self.body = {} if not req.can_read_body else await req.json()
    self.body = await self.readMultipart(req, inv)
    
    if 'dialog' in self.query:  self.currentDialog = self.query['dialog']
    elif 'dialog' in self.body:  self.currentDialog = self.body['dialog']
    if self.currentDialog and self.currentDialog not in inv.dialogs:
      raise MyException(f"Wrong dialog name:{self.currentDialog}!")
    
    if self.currentDialog: self.mode = 'dialog'
    if 'mode' in self.query:  self.mode = self.query['mode']
    elif 'mode' in self.body:  self.mode = self.body['mode']
    assert self.mode in self.MODES
    
    cStr = ''
    if 'command' in self.query:  cStr = self.query['command']
    elif 'command' in self.body:  cStr = self.body['command']
    if not cStr:
      print(f"cStr={cStr}")
      raise MyException(f"Cannot find the command")
    self.command = json.loads(cStr)
    #print(f"command:{cStr}=>{self.command}")
    if not self.command or not self.command[0]:
      raise MyException(f"Cannot parse the command")
    return self
  
  async def readMultipart(self, req, inv):
    if not req.can_read_body: 
      #print(f"multipart: cannot read")
      return {}
    reader = await req.multipart()
    #print(f"reader: {reader}")
    r = {}
    while True:
      field = await reader.next()
      if not field:  break;
      fn = field.name
      print(f"multipart field:{fn}")
      if fn == 'file':
        filename = field.filename if field.filename else r['fileName']
        if not filename:
          raise MyException(f"No file name: {field.filename}, {r['fileName']}")
        utp = inv.params['uploadTmpPath']
        if not os.path.exists(utp):
          raise MyException(f"No temporary folder found: {utp}")
        fileTmp = utp + filename
        print(f"reading file {filename} to {fileTmp}")
        with open(fileTmp, 'wb') as f:
          size = 0
          while True:
            chunk = await field.read_chunk()  # 8192 bytes by default.
            if not chunk:  break
            size += len(chunk)
            f.write(chunk)
        r['file'] = fileTmp
        r['size'] = size
        #print(f"got {size} bytes")
      else:
        r[fn] = await field.read(decode=True)
        r[fn] = r[fn].decode('utf-8')
        # https://stackoverflow.com/questions/27657570/how-to-convert-bytearray-with-non-ascii-bytes-to-string-in-python
        print(f"read:{r[fn]}")
        if fn == 'dialog':  self.setCurrentDialog(r[fn], inv)
        
    if r['command'] == 'sendFile':
      cmdArr = [ r['command'], r['dialog'], r['text'], r['file'], r['replyTo'] ]
      r['command'] = json.dumps(cmdArr)
    elif r['command'] == 'sendMessage':
      cmdArr = [ r['command'], r['dialog'], r['text'], '', r['replyTo'] ]
      r['command'] = json.dumps(cmdArr)
    return r  
  
  def getCurrentDialog(self):
    return self.currentDialog
  
  def clearCurrentDialog(self):
    self.currentDialog = None
    
  def setCurrentDialog(self, dn, inv):
    assert dn in inv.dialogs
    self.currentDialog = dn
    
  def setReplacedDialog(self, rd):
    self.replacedDialog = rd
  
  def adoptMode(self, aMode, inv):
    assert aMode in self.MODES
    self.mode = aMode
    self.result = self.redraw(inv)
    if self.replacedDialog:
      assert self.replacedDialog in inv.dialogs
      rd = inv.dialogs[self.replacedDialog]
      self.result['replacedDialog'] = super().repackDialog(rd, -1, inv)
      self.replacedDialog = None
    
  def getMode(self):
    return self.mode
  
  def removeEmptyEntries(self, repackedMsg):
    for key in ['unread','fwdFrom','media','mediaLink','text','action','undelivered','replyToId']:
      if key in repackedMsg and  not repackedMsg[key]:  repackedMsg.pop(key, None)
    return repackedMsg
  
  def repackMessage(self, msg, myid, isUnread = False, mediaLink = '', isDelivered = True):
    r = super().repackMessage(msg, myid, isUnread, mediaLink, isDelivered)
    return self.removeEmptyEntries(r)
  
  def repackMessage2(self, mm, dn, inv):
    r = super().repackMessage2(mm, dn, inv)
    return self.removeEmptyEntries(r)
  
  def presentMessage(self, msg, myid, isUnread = False, mediaLink = '', isDelivered = True):
    self.result = self.repackMessage(msg, myid, isUnread, mediaLink, isDelivered)
    return self.result
  
  def presentNames(self, sender):
    self.result =  super().presentNames(sender)
  
  def presentNewMessage(self, msgEvent, name, myid):
    r = self.repackMessage(msgEvent.message, myid, True, '', False)
    r['from'] = name
    self.result =  {'newMessage': r }

  def presentDialog(self, dialog, i, inv):
    self.result =  super().repackDialog(dialog, i, inv)
  
  def printPrompt(self):
    pass
  
  def presentDownloaded(self, dn, msgId, link ):
    self.result = { 'mediaLink': [ dn, msgId, link ] }
    return self.result
  
  def presentAlert(self, alert):
    self.result = { 'alert': alert }
    if self.mode: self.result['mode'] = self.mode
    return self.result
  
  def presentData(self, data, inv):
    self.result = { 'data': data }
    if self.mode: self.result['mode'] = self.mode
    return self.result
  
  def getCommand(self):
    return self.command
  
  def redraw(self, inv):
    if self.mode == 'buddies' or not self.currentDialog:
      res = []  
      for i, (dn, dialog) in enumerate(inv.dialogs.items()):
        r = super().repackDialog(dialog, i, inv)
        res.append(r)
      if len(res) == 0:  return res
      self.result = {'buddies': res}
      
    elif self.mode == 'dialog':
      dn = self.currentDialog
      assert dn in inv.dialogs
      d = super().repackDialog(inv.dialogs[dn], -1, inv)
      mmm = []
      for j,m in enumerate(inv.messages[dn]):
        l = len(inv.messages[dn])
        mm = inv.messages[dn][l-j-1]
        mmm.append( self.repackMessage2(mm, dn, inv) )
      self.result = {'dialog': d, 'messages': mmm }
      
    else: 
      self.result = {}
    
    return self.result
  
  def getRawData(self, inv):
    r = ''
    if self.mode == 'buddies':
      for i,(dn,dialog) in enumerate(inv.dialogs.items()):
        r += f"{i} => {dialog.stringify()}"
        
    elif self.mode == 'dialog' or self.currentDialog:
      dn = self.currentDialog
      for j,m in enumerate(inv.messages[dn]):
        l = len(inv.messages[dn])
        mm = inv.messages[dn][l-j-1]
        r += f"{l-j-1} => {mm.stringify()}"

    return r
  
  def getResult(self):
    return self.result
  
'''
http://127.0.0.1:8080/a?command=["getDialog","rosc71"]
http://127.0.0.1:8080/a?command=["getBuddies"]
http://127.0.0.1:8080/a?command=["echo"]
'''
