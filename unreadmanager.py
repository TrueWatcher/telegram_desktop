import json as json
import os
from datetime import datetime
from myexception import MyException
from typing import Dict, Union, List, Tuple, Any
from telethon.tl.custom.message import Message

from typing import TYPE_CHECKING
# https://stackoverflow.com/questions/39740632/python-type-hinting-without-cyclic-imports
if TYPE_CHECKING:
  from inventory import Inventory # circuler import
else: Inventory = Any

Int2 = List[int]

class UnreadManager():
    def __init__(self, inv: 'Inventory') -> None:
      self.dialogsAccessed: Dict[str,Int2] = {}
      self.accessFile: str = 'access.json'
      self.inv = inv
      self.lastRead: Dict[str,int] = {}
      self.delivered: Dict[str,int] = {}
      
    def clear(self) -> None:
      self.dialogsAccessed = {}
      self.lastRead = {}
      self.delivered = {}
      
    def countUnreadMessages(self) -> None:
      self.readSavedData()
      for dn, msgList in self.inv.messages.items():
        lri = self.findLastReadId(dn)
        self.lastRead[dn] = lri if lri >= 0 else 0
        self.delivered[dn] = self.dialogsAccessed[dn][1]
    
    def readSavedData(self) -> None:
      isFresh = not os.path.exists(self.accessFile)
      if not isFresh:
        with open(self.accessFile, 'r') as af:
          accRead = json.loads( af.read() )
        for dn, d in self.inv.dialogs.items():
          self.dialogsAccessed[dn] = [0,0] if dn not in accRead else accRead[dn]
      else:
        for dn, d in self.inv.dialogs.items():
          self.dialogsAccessed[dn] = [0,0]

    def countOneDialog(self, dn: str) -> None: # used: cli.reloadDialog / cli: deleteMessage, cli: reloadDialog
      assert dn in self.dialogsAccessed
      lri = self.findLastReadId(dn)
      if lri > self.lastRead[dn]:  self.lastRead[dn] = lri
    
    def isUnreadByTs(self, dn: str, msg: Message) -> bool:
      assert dn in self.dialogsAccessed
      messageTs = msg.date.timestamp()
      dialogTs = self.dialogsAccessed[dn][0]
      return messageTs > dialogTs and not self.inv.isMine(msg)
    
    def findLastReadId(self, dn: str) -> int:
      if dn not in self.inv.messages:  return -1
      l = len(self.inv.messages[dn])
      if l == 0:  return -1
      for i in range(0, l):  # 0th is the newest
        m = self.inv.messages[dn][i]
        if not self.isUnreadByTs(dn, m) and not self.inv.isMine(m):  return int(m.id)
      return 0
    
    def getLastReadId(self, dn: str) -> int:
      if dn in self.lastRead:  return self.lastRead[dn]
      return 0
      
    def clearUnread(self, dn: str) -> None:
      if not dn in self.dialogsAccessed: return
      lm = self.inv.getLastMessage(dn) # self.inv.getLastOtherMessage(dn)
      if not lm:  return
      if lm.id > self.lastRead[dn]:
        self.lastRead[dn] = lm.id
      
    def isUnread(self, dn: str, msg: Message) -> bool: # used: consoleui.repackMessage2, redraw
      if self.inv.isMine(msg):  return False
      lri = self.getLastReadId(dn)
      # print(f"{dn} last read={lri}")
      if lri < 0:  raise MyException(f"No any messages in {dn}")
      if lri == 0:  return True
      return msg.id > lri
  
    def getLastUnread(self, dn: str) -> Union[int,None]:  # used: cli.sendRead
      lm = self.inv.getLastMyMessage(dn)
      if lm is None:  return None
      if self.isUnread(dn, lm):  return lm
      return None
      
    def getUnreadCount(self, dn: str) -> int:  # used: consoleui.repackDialog
      assert dn in self.inv.dialogs
      lri = self.getLastReadId(dn)
      if lri < 0:  return 0
      count = 0
      for i in range(0, len(self.inv.messages[dn])):  # 0th is the newest
        m = self.inv.messages[dn][i]
        if m.id <= lri:  break
        if not self.inv.isMine(m):  count += 1
      return count
    
    def isDelivered(self, dn: str, msg: Message) -> bool:  # used: consoleui.repackMessage2
      if not dn in self.delivered:  return False
      if not msg.message and not msg.media:  return True
      return msg.id <= self.delivered[dn]
  
    def getMaxDelivered(self, dn: str) -> int:
      if not dn in self.delivered:  return 0
      return self.delivered[dn]
    
    def _setMaxDelivered(self, dn: str, maxId: int) -> None:
      assert dn in self.delivered
      if maxId > self.delivered[dn]:  self.delivered[dn] = maxId
    
    def getDialogsWithUndelivered(self):  # used: cli.checkUndelivered
      res = []
      for dn in self.inv.dialogs:
        if self.hasUndelivered(dn):  res.append(dn)
      return res
    
    def hasUndelivered(self, dn: str) -> bool:  # used: consoleui.repackDialog
      assert dn in self.inv.dialogs
      lm = self.inv.getLastMyMessage(dn)
      if lm is None or self.isDelivered(dn, lm):  return False
      return True
    
    def addDelivered(self, dn: str, maxId: int) -> None:
      assert dn in self.dialogsAccessed
      if type(maxId) != int:  maxId = int(maxId)
      if self.delivered[dn] >= maxId:  return
      self.delivered[dn] = maxId
      self.dialogsAccessed[dn][1] = maxId
      self.saveAccessData()
    
    def saveDeliveredList(self, dl):
      if not dl:  return
      for dn,maxId in dl.items():
        assert dn in self.dialogsAccessed
        self.delivered[dn] = maxId
        self.dialogsAccessed[dn][1] = maxId
      self.saveAccessData()
                
    def saveAccessData(self) -> None:
      with open(self.accessFile, 'w') as af:
        af.write( json.dumps(self.dialogsAccessed) )
        
    def updateAccessTime(self, dn: str) -> None:
      assert dn in self.dialogsAccessed
      self.dialogsAccessed[dn][0] = int(datetime.now().timestamp()+0.5)
      
    def onLeaveDialog(self, dn: str) -> None:
      if not dn or (dn not in self.dialogsAccessed): 
        print(f"trying to leave empty dialog {dn}")
        return
      self.clearUnread(dn)
      self.updateAccessTime(dn)
      self.saveAccessData()
