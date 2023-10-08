import json
import os
from myexception import MyException
from uibase import UiBase
from typing import List, Dict, Union, Coroutine, Any
from telethon.tl.custom.message import Message
#from telethon.tl.custom.dialog import Dialog
import aiohttp
from inventory import Inventory

DataType = Union[bool,int,str]
StrStr = Dict[str,str]
DataDict = Dict[str, DataType]
AnyDict = Dict[str,Any]

class WebBridge(UiBase):
  MODES = ['buddies','dialog']
  
  def __init__(self) -> None:
    self.mode:                       str = 'buddies'
    self.currentDialog:  Union[str,None] = None
    self.replacedDialog: Union[str,None] = None
    self.command:                    str = ''
    self.result:                 AnyDict = {'alert': 'hello'}
    super().__init__()
    
  async def parseRequest(self, req: aiohttp.web.Request, inv: Inventory) -> 'WebBridge':
    self.request: aiohttp.web.Request = req
    self.query = req.query.copy()
    #self.body = {} if not req.can_read_body else await req.json()
    self.body = await self.readMultipart(req, inv)
    
    if 'dialog' in self.query:  self.currentDialog = self.query['dialog']
    elif 'dialog' in self.body:  self.currentDialog = str(self.body['dialog'])
    if self.currentDialog and self.currentDialog not in inv.dialogs:
      raise MyException(f"Wrong dialog name:{self.currentDialog}!")
    
    if self.currentDialog: self.mode = 'dialog'
    if 'mode' in self.query:  self.mode = self.query['mode']
    elif 'mode' in self.body:  self.mode = str(self.body['mode'])
    assert self.mode in self.MODES
    
    cStr = ''
    if 'command' in self.query:  cStr = self.query['command']
    elif 'command' in self.body:  cStr = str(self.body['command'])
    if not cStr:
      print(f"cStr={cStr}")
      raise MyException(f"Cannot find the command")
    self.command = json.loads(cStr)
    #print(f"command:{cStr}=>{self.command}")
    if not self.command or not self.command[0]:
      raise MyException(f"Cannot parse the command")
    return self
  
  async def readMultipart(self, req: aiohttp.web.Request, inv: Inventory) -> DataDict:
    r: DataDict = {}
    if not req.can_read_body: 
      #print(f"multipart: cannot read")
      return r
    reader = await req.multipart()
    #print(f"reader: {reader}")
    while True:
      field = await reader.next()
      if not field:  break;
      if not field.name:  continue
      #fn = field['name'] fails
      fn = field.name
      print(f"multipart field:{fn}")
      if fn == 'file':
        filename = field.filename if field.filename else r['fileName']
        if not filename:
          raise MyException(f"No file name: {field.filename}, {r['fileName']}")
        utp = inv.params['uploadTmpPath']
        if not os.path.exists(utp):
          raise MyException(f"No temporary folder found: {utp}")
        fileTmp = str(utp) + str(filename)
        print(f"reading file {filename} to {fileTmp}")
        with open(fileTmp, 'wb') as uploadingFile:
          size = 0
          while True:
            chunk = await field.read_chunk()  # 8192 bytes by default.
            if not chunk:  break
            size += len(chunk)
            uploadingFile.write(chunk)
        r['file'] = fileTmp
        r['size'] = size
        #print(f"got {size} bytes")
      else:
        bytezz = await field.read(decode=True)
        string = bytezz.decode('utf-8') 
        r[fn] = string
        # https://stackoverflow.com/questions/27657570/how-to-convert-bytearray-with-non-ascii-bytes-to-string-in-python
        print(f"read:{string}")
        if fn == 'dialog':  self.setCurrentDialog(string, inv)
        
    if r['command'] == 'sendFile':
      cmdArr = [ r['command'], r['dialog'], r['text'], r['file'], r['replyTo'] ]
      r['command'] = json.dumps(cmdArr)
    elif r['command'] == 'sendMessage':
      cmdArr = [ r['command'], r['dialog'], r['text'], '', r['replyTo'] ]
      r['command'] = json.dumps(cmdArr)
    return r  
  
  def getCurrentDialog(self) -> Union[str,None]:
    return self.currentDialog
  
  def clearCurrentDialog(self) -> None:
    self.currentDialog = None
    
  def setCurrentDialog(self, dn: str, inv: Inventory) -> None:
    assert dn in inv.dialogs
    self.currentDialog = dn
    
  def setReplacedDialog(self, rd: str) -> None:
    self.replacedDialog = rd
  
  def adoptMode(self, aMode: str, inv: Inventory) -> None:
    assert aMode in self.MODES
    self.mode = aMode
    self.result = self.redraw(inv)
    if self.replacedDialog is not None:
      assert self.replacedDialog in inv.dialogs
      rd = inv.dialogs[self.replacedDialog]
      self.result['replacedDialog'] = super().repackDialog(rd, -1, inv)
      self.replacedDialog = None
    
  def getMode(self) -> str:
    return self.mode
  
  def removeEmptyEntries(self, repackedMsg: DataDict) -> DataDict:
    for key in ['unread','fwdFrom','media','mediaLink','text','action','undelivered','replyToId']:
      if key in repackedMsg and  not repackedMsg[key]:  repackedMsg.pop(key, None)
    return repackedMsg
  
  def repackMessage(self, msg: Message, myid: int, isUnread: bool = False, mediaLink: Union[str,None] = '', isDelivered: bool = True) -> DataDict:
    r = super().repackMessage(msg, myid, isUnread, mediaLink, isDelivered)
    return self.removeEmptyEntries(r)
  
  def repackMessage2(self, mm: Message, dn: str, inv: Inventory) -> DataDict:
    r = super().repackMessage2(mm, dn, inv)
    return self.removeEmptyEntries(r)
  
  def presentMessage(self, msg: Message, myid: int, isUnread: bool = False, mediaLink: Union[str,None] = '', isDelivered: bool = True) -> AnyDict:
    self.result = self.repackMessage(msg, myid, isUnread, mediaLink, isDelivered)
    return self.result
  
  #def presentNames(self, sender):
  #  self.result =  super().presentNames(sender)
  #  return self.result
  
  def presentNewMessage(self, msgEvent, name: str, myid: int) -> None:
    r = self.repackMessage(msgEvent.message, myid, True, '', False)
    r['from'] = name
    self.result =  {'newMessage': r }

  def presentDialog(self, dialog, i, inv) -> None:
    self.result =  super().repackDialog(dialog, i, inv)
  
  def printPrompt(self) -> None:
    pass
  
  def presentDownloaded(self, dn: str, msgId: int, link: str ) -> AnyDict:
    self.result = { 'mediaLink': [ dn, msgId, link ] }
    return self.result
  
  def presentAlert(self, alert: str) -> AnyDict:
    self.result = { 'alert': alert }
    if self.mode: self.result['mode'] = self.mode
    return self.result
  
  def presentData(self, data, inv: Inventory) -> AnyDict:
    self.result = { 'data': data }
    if self.mode: self.result['mode'] = self.mode
    return self.result
  
  def getCommand(self) -> str:
    return self.command
  
  def redraw(self, inv: Inventory) -> AnyDict:
    if self.mode == 'buddies' or not self.currentDialog:
      res = []  
      for i, (dn, dialog) in enumerate(inv.dialogs.items()):
        r = super().repackDialog(dialog, i, inv)
        res.append(r)
      if len(res) == 0:  return {}
      self.result = {'buddies': res}
      
    elif self.mode == 'dialog':
      dn = self.currentDialog
      assert dn is not None and dn in inv.dialogs
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
  
  def getRawData(self, inv: Inventory) -> str:
    r = ''
    if self.mode == 'buddies':
      for i,(dnn,dialog) in enumerate(inv.dialogs.items()):
        r += f"{i} => {dialog.stringify()}"
        
    elif self.mode == 'dialog' or self.currentDialog:
      dn = self.currentDialog
      assert dn is not None and dn in inv.messages
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
