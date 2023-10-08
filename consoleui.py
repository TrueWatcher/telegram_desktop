import os
from uibase import UiBase
from myexception import MyException
from typing import List, Dict, Sequence, Union
from telethon.tl.custom.message import Message
from telethon.tl.custom.dialog import Dialog
from inventory import Inventory

class ConsoleUi(UiBase):
  
  SEP = '~'
  MODES = ['buddies','dialog','text','file']
  PROMPTS = [ 'number | reload | help | exit', 'm | f | df | del | fw | reload | return', 'message', 'file' ]
  D_HEADER = 'number === name / username / phone === total / unread'
  def __init__(self) -> None:
    self.mode: str = ''
    self.currentDialog: Union[str,None] = None
    super().__init__()
    print(f"Your timezone:{self.localTimeZone}") 

  def inputToCommand(self, line: bytearray, inv: Inventory) -> Sequence[Union[str,int]]:
    assert self.mode in self.MODES, f"unknown mode {self.mode}" 
    dn = self.getCurrentDialog()
    line2 = line.decode().rstrip('\n')
    line3 = line2.lower()
    if line3 == 'exit': # works in all modes
      return  (['exit'] if self.modeEquals('buddies') else ['exit','save', dn])
    dc = self.defaultCommand(line2)
    
    if self.mode == 'buddies':
      if line2 == 'raw':
        return ['printRaw']
      
      elif line2 == 'reload':
        return ['reloadAll']
      
      i = None
      try: 
        i = int(line2)
      except:
        return dc
      return ['selectDialog','i',i]
    
    elif self.mode == 'dialog':
      if line2 == '' or line2 == 'return':
        return ['listDialogs', dn]
      
      elif line2 == 'm' or line2 == 'ь':
        return ['switchToText']
      
      elif line2 == 'f':
        return ['switchToFile']
      
      elif line2 == 'raw':
        return ['printRaw']
      
      elif line2.startswith('df'):
        parts = line2.split(' ')
        if parts[0] != 'df':
          return dc
        offset = '' if len(parts) <= 1 else parts[1]
        return ['downloadFile', dn, 'o', offset]
      
      elif line2.startswith('del'):
        parts = line2.split(' ')
        if parts[0] != 'del':
          return dc
        offset = '' if len(parts) <= 1 else parts[1]
        forAll = "yes" if len(parts) > 2 and parts[2] else ""
        return ['deleteMessage', dn, 'o', offset, forAll]
      
      elif line2.startswith('fw'):
        parts = line2.split(' ')
        if parts[0] != 'fw':
          return dc
        if len(parts) < 3:
          return dc
        offset = parts[1]
        targetDialogIndex = parts[2]
        return ['forwardMessage', dn, 'o', offset, 'i', targetDialogIndex]
      
      elif line2 == 'reload':
        return ['reloadDialog', dn]
      
      else: 
        return dc
    
    elif self.mode == 'text':
      if line2 == '':
        self.adoptMode('dialog', inv)
        return ['']
      return ['sendMessage', dn, line2]
    
    elif self.mode == 'file':
      if line2 == '':
        self.adoptMode('dialog', inv)
        return ['']
      caption, fileName = self.detectCaption(line2)
      return ['sendFile', dn, caption, fileName]
    
    return dc
  
  def defaultCommand(self, line: str) -> List[str]:
    parts = line.split(self.SEP)
    return parts[0:4]
  
  def isPath(self, s: str) -> bool:
    stripped = s.strip("'\" ")
    #return stripped.startswith('/')
    return os.path.exists(stripped)
  
  def detectCaption(self, line2: str) -> List[str]:
    if not line2.__contains__(self.SEP):
      if line2.endswith("' ") or line2.endswith('" '):
        line2 = line2.rstrip(' ')
      if line2.startswith(" '") or line2.startswith(' "'):
        line2 = line2.lstrip(' ')
      if line2.__contains__(" '") or line2.__contains__("' ") or line2.__contains__(' "') or line2.__contains__('" '):
        raise MyException(f"No spaces, separator is {self.SEP}")
      caption = ''
      fileName = line2
    else:  
      parts = line2.split(self.SEP)
      if self.isPath(parts[0]):
        fileName = parts[0]
        caption = parts[1]
      elif self.isPath(parts[1]):
        fileName = parts[1]
        caption = parts[0]
      else:  raise MyException("Cannot guess which part is the file")
    return [ caption, fileName.strip("'\" ") ]
    
    
  def getCurrentDialog(self) -> Dialog:
    return self.currentDialog
  
  def clearCurrentDialog(self) -> None:
    self.currentDialog = None
    
  def setCurrentDialog(self, dn: Union[str,int], inv: Inventory) -> None:
    if isinstance(dn, int):
      dn = inv.i2dn(dn)
    assert dn in inv.dialogs
    self.currentDialog = dn
    
  def setReplacedDialog(self, rd: Dialog) -> None:
    pass
  
  def adoptMode(self, aMode: str, inv: Inventory) -> None:
    assert aMode in self.MODES, f"unknown mode {aMode}" 
    self.mode = aMode
    self.drawNewMode(inv)
    
  def modeEquals(self, m: str) -> bool:
    return m == self.mode
      
  def presentMessage(self, msg: Message, myid: int, isUnread: bool = False) -> None:
    r = self.repackMessage(msg, myid, isUnread = False)
    if r is None: return
    prefix: str = f"\033[1;96m{r['prefix']}\033[0m" if isUnread else str(r['prefix'])
    if isinstance(r['fwdFrom'],str) and r['fwdFrom']:
      prefix = prefix + r['fwdFrom'] + prefix 
    re: str = '' if not r['replyToId'] else f"Re:{r['replyToId']} "
    print(f"{prefix} {re}{r['media']}{r['action']}{r['text']} [{r['date']}]")
      
  def presentDialog(self, dialog: Dialog, index: int, inv: Inventory) -> None:
    r = self.repackDialog(dialog, index, inv)
    prefix = '   'if index < 0 else f"{r['i']:3d}"
    postfix = f" === {r['count']} / {r['unreadCount']}" if r['count'] else ''
    print(f"{prefix} === {r['name']} / {r['username']} / {r['phone']}{postfix}")

  def presentNewMessage(self, msgEvent: Message, name: str, myid: int) -> None:
    print()
    print(f"New from {name}")
    self.presentMessage(msgEvent.message, myid, True)

  def printPrompt(self) -> None:
    i = self.MODES.index(self.mode)
    print( self.PROMPTS[i], end ='>', flush=True)
  
  def drawNewMode(self, inv: Inventory) -> None:
    assert self.mode in self.MODES, f"unknown mode {self.mode}" 
    if self.mode == 'buddies' or self.mode == 'dialog':
      self.redraw(inv)
    else:
      self.printPrompt()
  
  def redraw(self, inv: Inventory) -> None:
    assert self.mode in self.MODES, f"unknown mode {self.mode}" 
    if self.mode == 'buddies':
      print()
      #print(inv.dialogs)
      print(self.D_HEADER)
      print()
      for i, (dnn, dialog) in enumerate(inv.dialogs.items()):
        self.presentDialog(dialog, i, inv)
      self.printPrompt()
      
    elif self.mode == 'dialog':
      print()
      print()
      dn = self.currentDialog
      assert isinstance(dn, str)
      self.presentDialog(inv.dialogs[dn], -1, inv)
      for j,m in enumerate(inv.messages[dn]):
        l = len(inv.messages[dn])
        mm = inv.messages[dn][l-j-1]
        self.presentMessage(mm, inv.getMyid(), inv.um.isUnread(dn, mm))    
      self.printPrompt()
      
    else: 
      pass  # user is typing a message -- don't bother with printing
  
  def presentDownloaded(self, dn: str, msgId: int, link: str) -> None:
    print(f"downloaded:{link}")
  
  def presentAlert(self, alert: str) -> None:
    print()
    print(alert)
    self.printPrompt()
    
  def presentData(self, data: str, inv: Inventory) -> None:
    print()
    print(data)
    self.redraw(inv)
    
  def getRawData(self, inv: Inventory) -> str:
    r: str = ''
    if self.mode == 'buddies':
      for i,(dnn,dialog) in enumerate(inv.dialogs.items()):
        r += f"{i} => {dialog.stringify()}"
        
    elif self.mode == 'dialog' or self.currentDialog:
      dn = self.currentDialog
      assert isinstance(dn, str) and dn in inv.messages
      for j,m in enumerate(inv.messages[dn]):
        l = len(inv.messages[dn])
        mm = inv.messages[dn][l-j-1]
        r += f"{l-j-1} => {mm.stringify()}"

    return r

