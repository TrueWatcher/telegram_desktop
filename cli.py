from telethon import TelegramClient, events
import asyncio
import os
import time
import random
from telethon.tl.types import InputPhoneContact
from telethon.tl.functions.contacts import ImportContactsRequest
from telethon.tl.functions.messages import GetPeerDialogsRequest
from myexception import MyException

class Cli:
  
  def __init__(self, inv, params, client):
    self.inv = inv
    self.params = params
    self.client = client

  async def loadData(self, ui):
    me = await self.client.get_me()
    self.inv.setMe(me)
    print(f"You are {ui.presentNames( self.inv.getMe() )}")
    await self.client.catch_up()
    async for dialog in self.client.iter_dialogs():
      dn = dialog.name
      assert not not dn # if "Deleted account" triggers this, just comment out this line
      self.inv.addDialog(dialog)
      fromClient = await self.client.get_messages(dialog.entity, self.params['maxMessages'])
      self.inv.addMessageList( dn, fromClient )
    self.inv.um.countUnreadMessages()
    newDelivered = await self.checkUndelivered()
    self.inv.um.saveDeliveredList(newDelivered)
    n = self.inv.mm.loadMediaLinks()
    print(f"found {n} downloaded files in {self.params['downloadPath']}")
    return 0
  
  async def reloadDialog(self, dn):
    assert dn in self.inv.dialogs
    fromClient = await self.client.get_messages(self.inv.getEntity(dn), self.params['maxMessages'])
    self.inv.replaceMessages( dn, fromClient )
    self.inv.um.updateAccessTime(dn)
    self.inv.um.countOneDialog(dn)
    return 0
  
  async def checkUndelivered(self):
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

  async def run(self, ui, act, arg0=None, arg1=None, arg2=None, arg3=None):
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
      peer = event.message.peer_id.user_id
      found = self.inv.findDialogByPeerId(peer)
      if found is None:
        sender = await event.get_sender()
        name = ui.presentNames(sender)
        ui.presentNewMessage(event, name, self.inv.getMyid())
        # await sendRead(sender.username, sender, event)
      else:
        if self.inv.isDuplicateId(found, event.message):
        # sometimes after sending a new message the server sends it again as new
          return 0
        self.inv.addMessage(found, event.message)
        ui.redraw(self.inv)
        openDialog = ui.getCurrentDialog() # for web it is None
        if found == openDialog:
          ret = await self.sendRead(openDialog)
          if ret: self.inv.um.onLeaveDialog(openDialog) # update and save access time
      
      if self.inv.ipc:
        newMsg = ui.repackMessage(event.message, self.inv.getMyid(), True)
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
      if arg0 == 'i':
        try:
          arg1 = int(arg1)
        except:
          raise MyException(f"Non-integer arg1:{arg1}")
        if arg1 < 0 or arg1 >= self.inv.getDialogCount():
          raise MyException(f"Wrong dialog number:{arg1}")
        arg1 = self.inv.i2dn(arg1)
        arg0 = 'n'
        # fall through
      if arg0 == 'n':  
        dn = arg1
        if dn not in self.inv.dialogs:
          raise MyException(f"Wrong dialog name:{dn}!")
        replaced = ui.getCurrentDialog()
        if replaced and dn != replaced:
          self.inv.um.onLeaveDialog(replaced)
          ui.setReplacedDialog(replaced)
        ui.setCurrentDialog(dn, self.inv)
        ui.adoptMode('dialog', self.inv)
        ret = await self.sendRead(dn)
        if ret:  self.inv.um.onLeaveDialog(dn) # update and save access time
        return 0
      raise MyException(f"Wrong select code:{arg0}")
    
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
      iarg3 = int(arg3) if arg3 else None
      if arg3 and not iarg3:
        raise MyException(f"Non-number replyTo:{arg3}")
      retMsg = await self.doSend(act, dn, arg1, arg2, iarg3) # on success returns message
      if not str(type(retMsg)).__contains__('.Message'):
        raise MyException(f"Failed to send:{type(retMsg)}!")
      self.inv.addMessage(dn, self.inv.forceMine(retMsg)) #  dn, msg
      ui.adoptMode('dialog', self.inv)
      return 0
    
    elif act == 'send2': # name|phone, text_no_spaces
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
        resPath = False
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
      if arg2 == '':
        return 0
      forAll = True if arg3 else False
      if not dn in self.inv.dialogs:
        raise MyException(f"No dialog selected")
      if arg1 == 'o':
        j = self.inv.makeOffset(dn, arg2) # dn, aOffset
        #print(dn)
        #raise MyException(f"break")
        msg = self.inv.messages[dn][j]
      elif arg1 == 'id':
        msg = self.inv.findMessageById(dn, int(arg2)) # dn, msgId
      else:
        raise MyException(f"Invalid type:{arg1}")
      if not msg:  raise MyException(f"No such message:{dn} {arg1} {arg2}")
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
    
    elif act == 'lookup': # name|phone|id
      if not arg0:
        raise MyException(f"Provide name, phone or id")
      res = None
      try:
        res = await self.client.get_entity(arg0)
      except:
        ui.presentAlert(f"Failure for {arg0}")
      if not res:
        ui.presentAlert(f"No entity found for {arg0}")
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

  async def doSend(self, act, dn, text, fileName, replyToId = None):
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
    
  async def sendRead(self, dn, entity=None, msg=None):
    last = self.inv.um.getLastUnread(dn) if msg is None else msg
    if not last: return False
    to = self.inv.getEntity(dn) if entity is None else entity
    return await self.client.send_read_acknowledge( to, last )

