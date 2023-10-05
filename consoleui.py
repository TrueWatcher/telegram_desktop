import os
from uibase import UiBase
from myexception import MyException

class ConsoleUi(UiBase):
  SEP = '~'
  MODES = ['buddies','dialog','text','file']
  PROMPTS = [ 'number | reload | help | exit', 'm | f | df | del | reload | return', 'message', 'file' ]
  D_HEADER = 'number === name / username / phone === total / unread'
  def __init__(self):
    self.mode = ''
    self.currentDialog = None
    super().__init__()
    print(f"Your timezone:{self.localTimeZone}") 

  def inputToCommand(self, line, inv):
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
      if line2 == '':
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
        forAll = True if len(parts) > 2 and parts[2] else False
        return ['deleteMessage', dn, 'o', offset, forAll]
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
  
  def defaultCommand(self, line):
    parts = line.split(self.SEP)
    return parts[0:4]
  
  def isPath(self, s):
    stripped = s.strip("'\" ")
    #return stripped.startswith('/')
    return os.path.exists(stripped)
  
  def detectCaption(self, line2):
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
    
    
  def getCurrentDialog(self):
    return self.currentDialog
  
  def clearCurrentDialog(self):
    self.currentDialog = None
    
  def setCurrentDialog(self, dn, inv):
    if isinstance(dn, int):
      dn = inv.i2dn(dn)
    assert dn in inv.dialogs
    self.currentDialog = dn
    
  def setReplacedDialog(self, rd):
    pass
  
  def adoptMode(self, aMode, inv):
    assert aMode in self.MODES, f"unknown mode {aMode}" 
    self.mode = aMode
    self.drawNewMode(inv)
    
  def modeEquals(self, m):
    return m == self.mode
      
  def presentMessage(self, msg, myid, isUnread = False):
    r = self.repackMessage(msg, myid, isUnread = False)
    if r is None: return
    prefix = f"\033[1;96m{r['prefix']}\033[0m" if isUnread else r['prefix']
    if r['fwdFrom']:  prefix = prefix + r['fwdFrom'] + prefix 
    re = '' if not r['replyToId'] else f"Re:{r['replyToId']} "
    print(f"{prefix} {re}{r['media']}{r['action']}{r['text']} [{r['date']}]")
      
  def presentDialog(self, dialog, i, inv):
    r = self.repackDialog(dialog, i, inv)
    prefix = '   'if i < 0 else f"{r['i']:3d}"
    postfix = f" === {r['count']} / {r['unreadCount']}" if r['count'] else ''
    print(f"{prefix} === {r['name']} / {r['username']} / {r['phone']}{postfix}")

  def presentNewMessage(self, msgEvent, name, myid):
    print()
    print(f"New from {name}")
    self.presentMessage(msgEvent.message, myid, True)

  def printPrompt(self):
    i = self.MODES.index(self.mode)
    print( self.PROMPTS[i], end ='>', flush=True)
  
  def drawNewMode(self, inv):
    assert self.mode in self.MODES, f"unknown mode {self.mode}" 
    if self.mode == 'buddies' or self.mode == 'dialog':
      self.redraw(inv)
    else:
      self.printPrompt()
  
  def redraw(self, inv):
    assert self.mode in self.MODES, f"unknown mode {self.mode}" 
    if self.mode == 'buddies':
      print()
      #print(inv.dialogs)
      print(self.D_HEADER)
      print()
      for i, (dn, dialog) in enumerate(inv.dialogs.items()):
        self.presentDialog(dialog, i, inv)
      self.printPrompt()
      
    elif self.mode == 'dialog':
      print()
      print()
      dn = self.currentDialog
      self.presentDialog(inv.dialogs[dn], -1, inv)
      for j,m in enumerate(inv.messages[dn]):
        l = len(inv.messages[dn])
        mm = inv.messages[dn][l-j-1]
        self.presentMessage(mm, inv.getMyid(), inv.um.isUnread(dn, mm))    
      self.printPrompt()
      
    else: 
      pass  # user is typing a message -- don't bother with printing
  
  def presentDownloaded(self, dn, msgId, link):
    print(f"downloaded:{link}")
  
  def presentAlert(self, alert):
    print()
    print(alert)
    self.printPrompt()
    
  def presentData(self, data, inv):
    print()
    print(data)
    self.redraw(inv)
    
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

