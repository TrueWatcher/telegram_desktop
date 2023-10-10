import datetime
from typing import List, Dict, Union
from telethon.tl.custom.message import Message
from telethon.tl.custom.dialog import Dialog
from inventory import Inventory

DataType = Union[bool,int,str]
DataDict = Dict[str, DataType]

class UiBase():
  def __init__(self) -> None:
    self.localTimeZone = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
    # https://stackoverflow.com/questions/1111056/get-time-zone-information-of-the-system-in-python
    self.year = datetime.datetime.now(self.localTimeZone).year
    self.dateFormat2 = '%-H:%M'
    self.dateFormat1 = '%b %-d %-H:%M'
    self.dateFormat0 = '%Y %b %-d %-H:%M'
  
  @staticmethod
  def mergeNames(entity) -> str:
    if entity and hasattr(entity,'first_name') and hasattr(entity,'last_name') and (entity.first_name or entity.last_name):
      f = '' if not entity.first_name else str(entity.first_name) # None -> ''
      l = '' if not entity.last_name else str(entity.last_name)
      return f + l
    return ''
  
  def presentNames(self, user) -> str:
    firstAndLast = self.mergeNames(user)
    #fn = '' if not hasattr(user,'first_name') or not user.first_name else user.first_name
    un = '' if not hasattr(user,'username') or not user.username else user.username
    ph = '' if not hasattr(user,'phone') or not user.phone else user.phone
    return f"{firstAndLast} / {un} / {ph}"   
  
  def repackMessage(self, msg: Message, myid: int, isUnread: bool = False, mediaLink: Union[str,None] = None, isDelivered: bool = True) -> DataDict:
    #if msg is None: return None
    assert not not msg
    r: DataDict = {}
    r['isMine']  = hasattr(msg,'from_id') and hasattr(msg.from_id, 'user_id') and msg.from_id.user_id == myid
    r['prefix']  = '>' if r['isMine'] else '<'
    r['unread']  = False if r['isMine'] else isUnread
    r['fwdFrom'] = ''
    if hasattr(msg,'x_author_name') :
      r['fwdFrom'] = msg.x_author_name
    elif hasattr(msg,'x_author_id') :
      r['fwdFrom'] = str(msg.x_author_id)
    r['id']      = msg.id
    media = ''
    if msg.file:
      fn = 'unknown' if not hasattr(msg.file,"name") or not msg.file.name else msg.file.name
      media = f"-file: {fn}- "
    elif hasattr(msg,'media') and msg.media:
      media = f"-media: {type(msg.media)}- "
    r['media']     = media
    r['mediaLink'] = '' if not mediaLink else mediaLink
    text = ''
    if hasattr(msg,'message') and isinstance(msg.message, str) and msg.message == '': 
      text = '-empty-'
    elif msg.message is None: 
      text = '-none-'
    else: 
      text = msg.message.replace("\n",' ').replace("\r",' ')
    r['text'] = text
    action = ''
    if hasattr(msg,'action') and msg.action:
      action = f"-action: {type(msg.action)}- "
    r['action'] = action  
    date = ''
    if hasattr(msg,'date') and msg.date:
      date = self.localize(msg.date)
    r['date'] = date
    r['undelivered'] = False if not r['isMine'] else not isDelivered
    r['replyToId'] = '' if not hasattr(msg,"reply_to") or not msg.reply_to or not hasattr(msg.reply_to,"reply_to_msg_id") or not msg.reply_to.reply_to_msg_id else msg.reply_to.reply_to_msg_id
    return r
  
  def repackMessage2(self, msg: Message, dn: str, inv: Inventory) -> DataDict:
    r = self.repackMessage( msg, inv.getMyid(), inv.um.isUnread(dn, msg), inv.mm.getMediaLink(dn, msg.id), inv.um.isDelivered(dn, msg) )
    return r
  
  def localize(self, date) -> str:
    assert date is not None
    dateToLocal = date.astimezone(self.localTimeZone)
    return dateToLocal.strftime(self.getDateFormat(dateToLocal))
  
  def getDateFormat(self, dateToLocal) -> str:
    if dateToLocal.year != self.year:
      return self.dateFormat0
    else:
      now = datetime.datetime.now(self.localTimeZone)
      if dateToLocal.month == now.month and dateToLocal.day == now.day:
        return self.dateFormat2
      else:
        return self.dateFormat1
      
  def repackDialog(self, dialog: Dialog, index: int, inv: Inventory) -> DataDict:
    r: DataDict = {}
    r['i'] = index
    e = dialog.entity
    dn = dialog.name
    r['name'] = dn
    r['username'] = '' if not hasattr(e,"username") or not e.username else e.username
    r['count'] = inv.getMessageCount(dn)
    r['unreadCount'] = inv.um.getUnreadCount(dn)
    r['hasUndelivered'] = inv.um.hasUndelivered(dn)
    r['phone'] = '' if not hasattr(e,"phone") or not e.phone else e.phone
    return r
