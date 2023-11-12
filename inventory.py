from collections import namedtuple
from myexception import MyException
import json5 as json5
import json as json
import os
import sys
import platform
from datetime import datetime
from unreadmanager import UnreadManager
from typing import List, Dict, Union
from telethon.tl.custom.message import Message
from telethon.tl.custom.dialog import Dialog
import asyncio

DataType = Union[bool,int,str]
StrStr = Dict[str,str]

class Inventory:
  
  Nme = namedtuple('Nme', 'id username phone')
  defaultParams = {
    'isLinux'      : platform.system() == 'Linux',
    'apiId'        : 0,
    'apiHash'      : '',
    'maxMessages'  : 20,
    'helpFile'     : 'help.txt',
    'downloadPath' : 'Downloads/',
    'uploadTmpPath': 'uploadTmp/',
    'webUiPort'    : 8080,
    'previewLink'  : False
  }
  paramsFile = 'params.json'
  
  def __init__(self) -> None:
    if sys.version_info < (3,6,0):
      raise MyException(f"Python before 3.6 cannot run this")
    # oredered dictionaries
    self.dialogs: Dict[str, Dialog] = {}
    self.messages: Dict[str, List[Message]] = {}
    self.cachedAuthors: Dict[int, str] = {}
    self.me = self.Nme( 0, "Neo", "000000" )
    self.um: UnreadManager = UnreadManager(self)
    self.ipc: Dict[str, asyncio.Queue] = {}
    self.params: Dict[str,DataType] = {}
    self.mm = self.MediaManager(self)
  
  '''
  def addBackwardDependencies(self, um) -> None:
    from unreadmanager import UnreadManager
    #self.um: UnreadManager = um
    assert isinstance(um, UnreadManager)
    setattr(self, 'um', um)
  '''
  def clearData(self) -> None:
    self.dialogs = {}
    self.messages = {}
    self.me = self.Nme( 0, "Neo", "000000" )
    self.um.clear()
  
  def setMe(self, aMe) -> None:
    self.me = aMe
  
  def getMe(self):
    return self.me
  
  def getMyid(self) -> int:
    return self.me.id
  
  def isMine(self, msg: Message) -> bool:
    return hasattr(msg,'from_id') and hasattr(msg.from_id, 'user_id') and msg.from_id.user_id == self.me.id
  
  def forceMine(self, msg: Message) -> Message:
    #print(f">>>{msg.from_id}") # ,{msg.from_id.user_id}
    if not hasattr(msg, 'from_id') or not msg.from_id:  msg.from_id = lambda: None
    #print(f"> >{retMsg.from_id}")
    if not hasattr(msg.from_id, 'user_id') or not msg.from_id.user_id:  msg.from_id.user_id = self.getMyid()
    #print(f"> >{msg.from_id},{msg.from_id.user_id}")
    return msg
  
  def isDuplicateId(self, dn: str, msg: Message) -> bool:
    assert dn in self.messages
    assert not not msg.id
    for m in self.messages[dn]:
      if m.id == msg.id: return True
    return False

  def findDialogByPeerId(self, userId: int) -> Union[str, None]:
    for dn,d in self.dialogs.items():
      if d.entity.id == userId: return dn
    return None
  
  def addDialog(self, dialog: Dialog) -> None:
    self.dialogs[dialog.name] = dialog
    
  def addMessageList(self, dn: str, msgList: List[Message]) -> None:
    assert dn in self.dialogs
    self.messages[dn] = msgList
    
  def addMessage(self, dn: str, msg: Message) -> None:
    assert dn in self.messages 
    self.messages[dn].insert(0, msg)
    
  def getMessageCount(self, dn: str) -> int:
    assert dn in self.messages
    return len(self.messages[dn])
  
  def getLastMessage(self, dn: str) -> Union[Message,None]:
    assert dn in self.messages
    if len(self.messages[dn]) == 0:  return None
    last = self.messages[dn][0] # latest is 0th, earliest is -1th
    return last
  
  def getLastMyMessage(self, dn: str) -> Union[Message,None]:
    assert dn in self.messages
    l = len(self.messages[dn])
    if l == 0:  return None
    for i in range(0, l):  # 0th is the newest
      m = self.messages[dn][i]
      if self.isMine(m) and ( m.message or m.media ):  return m
    return None
  
  def getLastOtherMessage(self, dn: str) -> Union[Message,None]:
    assert dn in self.messages
    l = len(self.messages[dn])
    if l == 0:  return None
    for i in range(0, l):  # 0th is the newest
      m = self.messages[dn][i]
      if not self.isMine(m):  return m # and ( m.message or m.media )
    return None
  
  def getDialogCount(self) -> int:
    return len(self.dialogs)
    
  def getEntity(self, dn: str):
    assert dn in self.messages
    return self.dialogs[dn].entity
  
  def replaceMessages(self, dn: str, msgList: List[Message]) -> None:
    assert dn in self.messages
    assert isinstance(msgList, list)
    self.messages[dn] = msgList
    
  def findMediaFromRecent(self, dn: str, aOffset: int) -> Message:
    assert dn in self.messages
    offset = self.makeOffset(dn, aOffset)
    mm = self.messages[dn]

    for i in range(offset, len(mm)):
      msg = mm[i]
      if hasattr(msg, 'media') and msg.media:
        return msg
    raise MyException(f"No media message found from {offset}")
  
  def makeOffset(self, dn: str, aOffset: Union[int,str]) -> int:
    assert dn in self.messages
    offset = 0
    if isinstance(aOffset, str):
      if len(aOffset) > 0:
        try:
          offset = int(aOffset)
        except:
          raise MyException(f"Wrong offset:{aOffset}!")
      else: 
        offset = 0
    elif isinstance(aOffset, int):
      offset = aOffset
    else:
      raise MyException(f"Wrong offset type:{aOffset}!")
    if offset >= len( self.messages[dn] ) or offset < 0:
      raise MyException(f"Too large or too small offset:{offset}!")
    #print(">>>",aOffset,"/",offset)
    #raise MyException(f"Break")
    return offset
  
  def findMessageById(self, dn: str, msgId: int) -> Union[Message, None]:
    assert dn in self.messages
    if type(msgId) == str:  msgId = int(msgId)
    for m in self.messages[dn]:
      if m.id == msgId:  return m
    return None
      
  def loadParams(self) -> Dict:
    res = {}
    paramsRead = {}
    if not os.path.exists(self.paramsFile):
      raise MyException(f"You must provide real apiId and apiHash in the file {self.paramsFile}")
    with open(self.paramsFile, 'r') as pf:
      paramsRead = json5.loads( pf.read() )
    for i in paramsRead:
      if not i in self.defaultParams:
        raise MyException(f"Unknown key {i} in params file {self.paramsFile}")
    for i in self.defaultParams:
      res[i] = paramsRead[i] if i in paramsRead else self.defaultParams[i]
    if res['apiId'] == 0 or len(res['apiHash']) == 0:
      raise MyException(f"You must provide real apiId and apiHash in the file {self.paramsFile}")
    self.params = res
    return res
  
  def i2dn(self, i: int) -> str:
    assert i >= 0 and i < len(self.dialogs)
    #print(len(self.dialogs), ">>>", list(self.dialogs.items())[i] )
    tuples = list(self.dialogs.items()) # Python >= 3.6 !
    dn = tuples[i][0]
    return dn
  
  def enqueueIpc(self, message: Message) -> List[str]:
    if not self.ipc:  return []
    res: List[str] = []
    for key,q in self.ipc.items():
      if not q:  continue
      q.put_nowait(message)
      res.append(key)
    return res
  
  class MediaManager:
    medialinkFile = 'medialinks.json'
    
    def __init__(self, inv: 'Inventory') -> None:
      self.inv = inv
      self.mediaLinks: Dict[str, StrStr] = {}
  
    def removeTmpUpload(self, fullFileName: str) -> None:
      parts = fullFileName.split('/')
      if parts[-2] and parts[-2]+'/' == self.inv.params['uploadTmpPath']:
        os.remove(fullFileName)
            
    def loadMediaLinks(self) -> int:
      if not os.path.exists(self.medialinkFile):  return 0
      with open( self.medialinkFile, 'r') as f:
        serialized = f.read()
      self.mediaLinks = json.loads(serialized)
      count = 0
      for d,mll in self.mediaLinks.items():
        count += len(mll)
      return count

    def addMediaLink(self, dn: str, msgId: str, fullFileName: str) -> bool:
      if type(msgId) != str: msgId = str(msgId)  
      # str required for json keys
      if not os.path.exists(fullFileName):  return False
      if dn not in self.mediaLinks:  
        self.mediaLinks[dn] = {}
      self.mediaLinks[dn][msgId] = fullFileName
      with open( self.medialinkFile, 'w') as f:
        f.write( json.dumps(self.mediaLinks) )
      return True
        
    def deleteMediaLink(self, dn: str, msgId: str, deleteFile: bool = True) -> bool:
      if type(msgId) != str: msgId = str(msgId)
      if dn not in self.mediaLinks or msgId not in self.mediaLinks[dn]:  return False
      link = self.mediaLinks[dn][msgId]
      if deleteFile and os.path.exists(link):
        os.remove(link)
      self.mediaLinks[dn].pop(msgId, None)
      with open( self.medialinkFile, 'w') as f:
        f.write( json.dumps(self.mediaLinks) )
      return True
        
    def getMediaLink(self, dn: str, msgId: Union[str,int]) -> Union[str,None]:
      if type(msgId) != str: msgId = str(msgId)
      if dn not in self.mediaLinks or msgId not in self.mediaLinks[dn]:  return None
      return self.mediaLinks[dn][msgId]

