from telethon import TelegramClient, events
import asyncio
import os
import time
import random
from telethon.tl.types import InputPhoneContact
from telethon.tl.functions.contacts import ImportContactsRequest
from telethon.tl.functions.messages import GetPeerDialogsRequest
from myexception import MyException
from typing import Dict, Union, List
from telethon.tl.custom.message import Message
from inventory import Inventory
from uibase import UiBase
from consoleui import ConsoleUi
from webbridge import WebBridge

class Cli:
  
  def __init__(self, inv: Inventory, params: Dict, client: TelegramClient) -> None:
    self.inv = inv
    self.params = params
    self.client = client

  async def loadData(self, ui: Union[ConsoleUi,WebBridge]) -> int:
    me = await self.client.get_me()
    self.inv.setMe(me)
    print(f"You are {ui.presentNames( self.inv.getMe() )}")
    print(f"Downloading your messages, please, wait...")
    await self.client.catch_up()
    async for dialog in self.client.iter_dialogs():
      dn = dialog.name
      if not dn:  # "Deleted account"
        continue
      self.inv.addDialog(dialog)
      fromClient = await self.client.get_messages(dialog.entity, self.params['maxMessages'])
      await self.addAllAuthorNames(fromClient)
      self.inv.addMessageList( dn, fromClient )
    self.inv.um.countUnreadMessages()
    newDelivered = await self.checkUndelivered()
    self.inv.um.saveDeliveredList(newDelivered)
    n = self.inv.mm.loadMediaLinks()
    print(f"found {n} downloaded files in {self.params['downloadPath']}")
    return 0
  
  async def reloadDialog(self, dn: str) -> int:
    assert dn in self.inv.dialogs
    fromClient = await self.client.get_messages(self.inv.getEntity(dn), self.params['maxMessages'])
    await self.addAllAuthorNames(fromClient)
    self.inv.replaceMessages( dn, fromClient )
    self.inv.um.updateAccessTime(dn)
    self.inv.um.countOneDialog(dn)
    return 0
  
  async def checkUndelivered(self) -> Dict:
  # https://stackoverflow.com/questions/66993647/how-to-detect-if-my-messages-on-telegram-is-already-read-using-telethon
    changed = {}
    ul = self.inv.um.getDialogsWithUndelivered()
    #print(ul)
    for dn in ul:
      r = await self.client( GetPeerDialogsRequest(peers=[self.inv.getEntity(dn)]) )
      # print(r.stringify())
      maxId = r.dialogs[0].read_outbox_max_id
      #print(f"{dn}: got max delivered={maxId}, stored={self.inv.um.getMaxDelivered(dn)}")
      if self.inv.um.getMaxDelivered(dn) < maxId:
        #self.inv.um.delivered[dn] = maxId
        print(f"your message has been delivered to {dn}")
        changed[dn] = maxId
    return changed

  async def run(self, ui: Union[ConsoleUi,WebBridge], act: str, arg0=None, arg1=None, arg2=None, arg3=None, arg4=None) -> int:
    if act == '':
      return 0
    
    if act == 'exit': # None | ( 'save', dn )
      if arg0 == 'save' and arg1:
        self.inv.um.onLeaveDialog(arg1) # dn
      return -1
    
    elif act == 'echo':
      ui.presentAlert(f"Hallo")
      return 0
    
    elif act == 'consumeMessage': # msgEvent
      #print("new message")
      event = arg0
      if event.message is None:
        raise MyException(f"Got event without message:{event}")
      msg: Message = event.message
      peerId = 0
      if not hasattr(msg,"peer_id"): 
        raise MyException(f"Got message without peer_id:{msg}")
      if hasattr(msg.peer_id,'user_id'):
        peerId = msg.peer_id.user_id
      elif hasattr(msg.peer_id,'chat_id'):
        peerId = msg.peer_id.chat_id
      else: raise MyException(f"Got message with weird peer_id:{msg}")
      
      await self.addAuthorName(msg)
      found = self.inv.findDialogByPeerId(peerId)
      name = ''
      if found is None:
        sender = await event.get_sender()
        name = ui.presentNames(sender)
        ui.presentNewMessage(event, name, self.inv.getMyid())
        # await sendRead(sender.username, sender, event)
      else:
        if self.inv.isDuplicateId(found, msg):
        # sometimes after sending a new message the server sends it again as new
          return 0
        self.inv.addMessage(found, msg)
        ui.redraw(self.inv)
        openDialog = ui.getCurrentDialog() # for web it is None
        if found == openDialog:
          ret = await self.sendRead(openDialog)
          if ret: self.inv.um.onLeaveDialog(openDialog) # update and save access time
      
      if self.inv.ipc:
        newMsg = ui.repackMessage(msg, self.inv.getMyid(), True)
        if newMsg is None:  return 0
        newMsg["from"] = found if found is not None else name
        kk = self.inv.enqueueIpc( {'newMessage': newMsg} )
        for key in kk:  print(f"queued newMessage {newMsg['id']} to {key}")
      
      return 0
    
    elif act == 'consumeMessageRead': # msgEvent
    # https://telethonn.readthedocs.io/en/latest/telethon.events.html#telethon-events-package
      event = arg0
      #print(event.stringify())
      peer = event.original_update.peer.user_id
      maxId = event.max_id
      found = self.inv.findDialogByPeerId(peer)
      if found:
        self.inv.um.addDelivered(found, maxId)
        kk = self.inv.enqueueIpc( {'messageRead': {'from': found, 'id': maxId} } )
        for key in kk:  print(f"queued messageRead {maxId} to {key}")
      else:
        print(f"messageRead: peer {peer} not found, maxId={maxId}")
            
      return 0
    
    elif act == 'selectDialog': # type, i|dn
      dn = self.getDn(arg0, arg1)
      replaced = ui.getCurrentDialog()
      if replaced and dn != replaced:
        self.inv.um.onLeaveDialog(replaced)
        ui.setReplacedDialog(replaced)
      ui.setCurrentDialog(dn, self.inv)
      ui.adoptMode('dialog', self.inv)
      ret = await self.sendRead(dn)
      if ret:  self.inv.um.onLeaveDialog(dn) # update and save access time
      return 0
    
    elif act == 'listDialogs': # dn
      self.inv.um.onLeaveDialog( arg0 )
      ui.clearCurrentDialog()
      ui.adoptMode('buddies', self.inv)
      return 0
      
    elif act == 'switchToText':
      ui.adoptMode('text', self.inv)
      return 0

    elif act == 'switchToFile':
      ui.adoptMode('file', self.inv)
      return 0
    
    elif act == 'sendMessage' or act == 'sendFile': # dn, text, fileFullName, replyTo
      dn = arg0
      if not dn in self.inv.dialogs:
        raise MyException(f"No dialog selected")
      if (not arg1 and not arg2) or (arg1 == '' and arg2 == ''):
        return 0
      iarg3 = int(arg3) if arg3 else 0
      if arg3 and not iarg3:
        raise MyException(f"Non-number replyTo:{arg3}")
      retMsg = await self.doSend(act, dn, arg1, arg2, iarg3) # on success returns message
      if not str(type(retMsg)).__contains__('.Message'):
        raise MyException(f"Failed to send:{type(retMsg)}!")
      self.inv.addMessage(dn, self.inv.forceMine(retMsg)) #  dn, msg
      ui.adoptMode('dialog', self.inv)
      return 0
    
    elif act == 'forwardMessage': # dn, msgArgType, id|offset, dialogArgType, index|name
      dn = arg0
      if not dn in self.inv.dialogs:
        raise MyException(f"No dialog given")
      if arg1 == '' or arg3 == '':
        return 0
      msg = self.getMessage(arg1, arg2, dn)
      toName = self.getDn(arg3, arg4)
      to = self.inv.getEntity(toName)
      #print(f"About to forward _{msg.raw_text}_ to {toName}")
      #raise MyException(f"break")
      retMsg = await msg.forward_to(to)
      if not str(type(retMsg)).__contains__('.Message'):
        raise MyException(f"Failed to forward:{type(retMsg)}!")
      self.inv.addMessage(toName, retMsg) #  dn, msg
      ui.presentAlert(f"forwarded {msg.id} to {toName}")
      #ui.redraw(self.inv)
      return 0
    
    elif act == 'send2': # name|phone, text
      if not arg0 or not arg1:
        raise MyException(f"Provide name and text")
      try:
        entity = await self.client.get_entity(arg0)
      except:
        raise MyException(f"Unknown recipient: {arg0}")
      if not entity:
        raise MyException(f"Unknown recipient: {arg0}")
      print(entity.stringify())
      retMsg = await self.client.send_message(entity, arg1)
      if not str(type(retMsg)).__contains__('.Message'):
        raise MyException(f"Failed to send:{type(retMsg)}!")
      to = '[not in dialogs]'
      if entity.first_name in self.inv.dialogs:
        to = entity.first_name
        self.inv.addMessage(entity.first_name, retMsg) #  dn, msg
        # ui.adoptMode('dialog', self.inv)
      print(f"sent successfully to {to}")
      ui.redraw(self.inv)
      return 0
    
    elif act == 'printRaw':
      data = ui.getRawData(self.inv)
      ui.presentData(data, self.inv)
      return 0
    
    elif act == 'help':
      if not os.path.exists(self.params['helpFile']):
        raise MyException(f"Failed to find {self.params['helpFile']}")
      with open(self.params['helpFile'], 'r') as hf:
        helpRead = hf.read()
      print(helpRead)
      ui.redraw(self.inv)
      return 0
    
    elif act == 'downloadFile': # dn, type, id|offset, remove
      dn = arg0
      if not dn in self.inv.dialogs:
        raise MyException(f"No dialog selected")
      if arg1 == 'o':
        msg = self.inv.findMediaFromRecent(dn, arg2) # dn, aOffset
      elif arg1 == 'id':
        if not arg2: 
          raise MyException(f"Missing id")
        msg = self.inv.findMessageById(dn, int(arg2)) # dn, msgId
      else:
        raise MyException(f"Invalid type:{arg1}")  
      if arg3:
        self.inv.mm.deleteMediaLink(dn, msg.id, True);
        resPath = ""
      else:
        if msg.file and msg.file.name:
          fn = msg.file.name
        else:
          fn = str(int(time.time()))
        resPath = await msg.download_media(self.params['downloadPath']+fn)
        if not resPath:
          raise MyException(f"download failed") 
        self.inv.mm.addMediaLink(dn, msg.id, resPath)
      ui.presentDownloaded(dn, msg.id, resPath)
      ui.printPrompt()
      return 0
    
    elif act == 'deleteMessage': # dn, type, id|offset, forAll
      dn = arg0
      if not dn in self.inv.dialogs:
        raise MyException(f"No dialog given")
      if arg2 == '':
        return 0
      forAll = True if arg3 else False
      msg = self.getMessage(arg1, arg2, dn)
      #print(msg.raw_text)
      #raise MyException(f"break")
      msgId = msg.id
      res = await msg.delete(revoke=forAll)
      #print(res)
      if not str(type(res)).__contains__(r"<class 'list'>"):
        raise MyException(f"Failed to delete that message ({str(type(res))})")
      self.inv.mm.deleteMediaLink(dn, msgId, True);
      await self.reloadDialog(dn)
      ui.redraw(self.inv)
      return 0
    
    elif act == 'reloadAll':
      self.inv.clearData()
      await self.loadData(ui)
      ui.adoptMode('buddies', self.inv)
      return 0
    
    elif act == 'reloadDialog': # dn
      dn = arg0
      if not dn in self.inv.dialogs:
        raise MyException(f"No dialog selected")
      await self.reloadDialog(dn)
      ui.redraw(self.inv)
      return 0
    
    elif act == 'lookup': # name|phone|id isIntId
      if not arg0:
        raise MyException(f"Provide name, phone or id")
      res = None
      arg: Union[int,str] = int(arg0) if arg1 else arg0 # id is int, others are str
      try:
        res = await self.client.get_entity(arg)
      except Exception as err:
        ui.presentAlert(f"Failure for {arg}: {err}")
      if not res:
        ui.presentAlert(f"No entity found for {arg}")
      else:
        ui.presentData(res.stringify(), self.inv)
      #ui.redraw(self.inv)
      return 0
    
    elif act == 'addPhoneContact': # phone, firstName_no_spaces, lastName
      if not arg0 or not arg1:
        raise MyException(f"Provide phone and name")
      if not arg2:  arg2 = ''
      # https://stackoverflow.com/questions/53436883/add-contact-with-telethon-in-python
      # https://stackoverflow.com/questions/48684915/telethon-library-how-to-add-user-by-phone-number
      contact = InputPhoneContact( client_id=random.randint(0,9999), phone=arg0, 
        first_name=arg1, last_name=arg2 )
      res = await self.client( ImportContactsRequest([contact]) )
      if not res:
        print(f"failed to add {arg0} / {arg1}")
      else:
        print(res.stringify())
      ui.redraw(self.inv)
      return 0
    
    # web
    elif act == 'getDialog': #dn
      if arg0 in self.inv.dialogs:  
        ui.setCurrentDialog(arg0, self.inv)
      if ui.getCurrentDialog() not in self.inv.dialogs:
        raise MyException(f"No dialog selected")
      #ui.adoptMode('dialog', self.inv)
      #ui.mode = 'dialog' # must be set in parseRequest, not here
      ui.redraw(self.inv)
      return 0
    
    elif act == 'ackNewMessage': #dn, id
      if arg0 not in self.inv.dialogs:
        raise MyException(f"Wrong dialog {arg0}")
      dn = arg0
      msgId = int(arg1)
      if not msgId:
        raise MyException(f"Wrong id {arg1}")
      msg = self.inv.findMessageById(dn, msgId)
      ret = await self.sendRead(dn, None, msg)
      if not ret:
        raise MyException(f"Failed ack {arg0} {arg1}")
      self.inv.um.onLeaveDialog(dn) # update and save access time
      ui.presentDialog(self.inv.dialogs[dn], -1, self.inv)
      return 0
    
    elif act == 'getBuddies':
      #ui.adoptMode('buddies', self.inv)
      #ui.mode = 'buddies' # must be set in parseRequest, not here
      ui.redraw(self.inv)
      return 0
    
    elif act == 'mockDelivery': # dn, id
      if arg0 not in self.inv.dialogs:
        raise MyException(f"Wrong dialog {arg0}")
      dn = arg0
      if not arg1 or int(arg1) < self.inv.um.getMaxDelivered(dn):
        raise MyException(f"Too small id {arg1} {self.inv.um.getMaxDelivered(dn)}")
      maxId = int(arg1)
      self.inv.um.addDelivered(dn, maxId)
      kk = self.inv.enqueueIpc( {'messageRead': {'from': dn, 'id': maxId} } )
      for key in kk:  print(f"queued messageRead {arg1} to {key}")
      return 0
    
    else:
      raise MyException(f"run: unknown command:{act}!")
    
    raise MyException(f"Not to get here")

  async def doSend(self, act: str, dn: str, text: str, fileName: str, replyToId: Union[int,None] = None) -> Message:
    if not replyToId:  replyToId = None
    to = self.inv.getEntity( dn )
    if act == 'sendMessage':
      return await self.client.send_message(to, text, reply_to = replyToId, link_preview = self.params['previewLink'])
    elif act == 'sendFile':
      if not os.path.exists(fileName):
        raise MyException(f"No such file:{fileName}!")
      retMsg = await self.client.send_file( to, fileName, caption = text, reply_to = replyToId )
      self.inv.mm.removeTmpUpload(fileName)
      return retMsg
    raise MyException(f"doSend unknown command:{act}!")
    
  async def sendRead(self, dn: str, entity=None, msg: Message=None):
    last = self.inv.um.getLastUnread(dn) if msg is None else msg
    if not last: return False
    to = self.inv.getEntity(dn) if entity is None else entity
    return await self.client.send_read_acknowledge( to, last )
  
  def getDn(self, argType: str, indexOrName: Union[int,str]) -> str:
    if argType == 'i':
      try:
        indexOrName = int(indexOrName)
      except:
        raise MyException(f"Non-integer indexOrName:{indexOrName}")
      if indexOrName < 0 or indexOrName >= self.inv.getDialogCount():
        raise MyException(f"Wrong dialog number:{indexOrName}")
      indexOrName = self.inv.i2dn(indexOrName)
      argType = 'n'
      # fall through
    if argType == 'n':  
      dn = str(indexOrName)
      if dn not in self.inv.dialogs:
        raise MyException(f"Wrong dialog name:{dn}!")
      return dn
    raise MyException(f"Wrong argType:{argType}")
  
  def getMessage(self, argType: str, idOrOoffset: str, dn: str) -> Message:
    msg = None
    if argType == 'o':
      j = self.inv.makeOffset(dn, idOrOoffset) # dn, aOffset
      #print(dn)
      #raise MyException(f"break")
      msg = self.inv.messages[dn][j]
    elif argType == 'id':
      msg = self.inv.findMessageById(dn, int(idOrOoffset)) # dn, msgId
    else:
      raise MyException(f"Invalid type:{argType}")
    if not msg:  raise MyException(f"No such message:{dn} {argType} {idOrOoffset}")
    return msg

  async def addAuthorName(self, msg: Message) -> None:
    def getIdFromForwarded(msg: Message) -> int:
      if hasattr(msg.fwd_from,'from_id') and hasattr(msg.fwd_from.from_id,'user_id'):
        return msg.fwd_from.from_id.user_id
      elif hasattr(msg.fwd_from,'from_id') and hasattr(msg.fwd_from.from_id,'channel_id'):
        return msg.fwd_from.from_id.channel_id
      else:
        return -1
      
    def tryGetIdFromChat(msg: Message, author_id: int) -> int:
      if hasattr(msg,'from_id') and hasattr(msg.from_id,'user_id') and hasattr(msg,'peer_id') and hasattr(msg.peer_id,'chat_id'):
      # in a chat, author is different from dialog
        if msg.from_id.user_id != msg.peer_id.chat_id:
          return msg.from_id.user_id
      return author_id
    
    author_id = 0
    author_name = ''
    if hasattr(msg,'fwd_from') and msg.fwd_from:
      if msg.fwd_from.from_name:
        author_name = msg.fwd_from.from_name
      else:
        author_id = getIdFromForwarded(msg)
        
    author_id = tryGetIdFromChat(msg, author_id)
            
    if author_id:
      #print(f"\nlooking for entity with id {author_id} ")
      found = ''
      if author_id in self.inv.cachedAuthors:
        found = self.inv.cachedAuthors[author_id]
        #print(f" : cached {found}")
      else:
        found = await self.getNamesByPeerId(author_id)
        if found:  
          self.inv.cachedAuthors[author_id] = found
          #print(f" : queried {found}")
      if found:  author_name = found
      
    if author_name:
      setattr(msg, 'x_author_name', author_name)
    if author_id:
      setattr(msg, 'x_author_id', author_id)
  
  async def getNamesByPeerId(self, author_id: Union[str,int]) -> str:
    try:
      entity = await self.client.get_entity(int(author_id)) # search for id requires int argument
      # get_input_entity() does not give names
      if not entity:
        print(f"\nname not found for {author_id}")
        return ''
      if UiBase.mergeNames(entity):
        return UiBase.mergeNames(entity)
      elif entity.username:
        return str(entity.username)
      else:
        return 'noname'
    except Exception as err:
      print(f" error:{err}")
      return ''
  
  async def addAllAuthorNames(self, msgList: List[Message]) -> None:
    for msg in msgList:
      await self.addAuthorName(msg)
