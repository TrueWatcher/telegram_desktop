"""
a free Telegram desktop client (based on the Telethon library) by TrueWatcher 2022 
1.1.1 20.09.2022 workable file transfers
1.1.2 21.09.2022 workable message deletion
1.1.3 22.09.2022 workable unread count
1.2.0 26.09.2022 refactoring currentDialog
1.2.1 27.09.2022 refactoring i > dn
1.2.2 28.09.2022 workable read_ack
1.2.3 28.09.2022 added dates
1.3.0 29.09.2022 added addPhoneContact
1.4.0 03.10.2022 factored Cli to own module
1.5.0 04.10.2022 workable web ajax handler
1.5.1 04.10.2022 added html and js code, not run
1.5.2 05.10.2022 added passing messages from Telethon event to aiohttp handler
1.5.3 08.10.2022 basic web interface
1,5,4 10,10,2022 improved file upload
1.5.5 11.10.2022 workable file download for web
1.5.6 13.10.2022 workable unread counter for web
1.5.7 13.10.2022 messageRead handler
1.5.8 18.10.2022 workable delivery botification
1.5.9 20.10.2022 fixws and improvements
1.5.10 21.10.2022 unreadManager.rtf  refactoring
1.5.11 22.10.2022 extensive refactoring
1.5.12 22.10.2022 refactoring and improvements
1.5.14 28.10.2022 added the replyTo feature
1.5.15 11.11.2022 fixed exception in cli.py::send2
1.5.16 17.11.2022 added inventory::params::previewLink
1.5.17 09.04.2023 added hasattr to uibase.py
1.6.0  05.10.2023 cleanup, prepared as git repo
"""
from telethon import TelegramClient, events
import asyncio
import sys
from aiohttp import web, WSMsgType
from myexception import MyException
from consoleui import ConsoleUi
from inventory import Inventory
from cli import Cli
from webbridge import WebBridge
import json
import uuid

print('tgtlc is a free Telegram desktop client by TrueWatcher 2022')
inv = Inventory()
params = inv.loadParams()
#print(params)    
client = TelegramClient('anon', params['apiId'], params['apiHash'])
#print("client created")
print("connected to Telegram")
loop = client.loop

cui = ConsoleUi()
cli = Cli(inv, params, client)

async def handlerAjax(request):
  print('')
  #print(f"Ajax request:{request}")
  print(f"query str:{request.query_string}")
  #print(f"query:{request.query}")
  #if request.can_read_body:
  #  print(f"body text:{await request.text()}") breaks multipart reader
  
  try:
    wb = WebBridge()
    await wb.parseRequest(request, inv)
    command = wb.getCommand()
    print(f"webUi entry mode:{wb.getMode()}, currentDialog:{wb.getCurrentDialog()}")
    ret = await cli.run(wb, *command)
    res = wb.getResult()
  except MyException as err:
    res = wb.presentAlert(str(err))
  
  print(f"webUi exit mode:{wb.getMode()}, currentDialog:{wb.getCurrentDialog()}")
  print(f"my response:{res}")
  return web.json_response(res)

async def handlerWebsocket(request):
# https://docs.aiohttp.org/en/stable/web_quickstart.html#websockets
  wsr = web.WebSocketResponse()
  await wsr.prepare(request)
  uid = str(uuid.uuid4())
  inv.ipc[uid] = asyncio.Queue()
  
  async def resend(wsr): # wsr is required, uid is not
    #print("run resend")
    await asyncio.sleep(1)
    while True:
      #print(f"cycle resend {wsr} {uid}")
      if not inv.ipc or not inv.ipc[uid]:  
        #print(f"finishing resend {uid}")
        wsr = None
        return 0
      if wsr is None or wsr.closed: # not ws is True!!!
        #print(f"broken resend {wsr} {uid}")
        wsr = None
        return 0
      msg = await inv.ipc[uid].get()
      act = list(msg.keys())[0]
      print(f"ws sent {act} {msg[act]['id']} to {uid}")
      await wsr.send_json(msg)
    
  rt = loop.create_task(resend(wsr))  
  
  async for msg in wsr:
    if msg.type == WSMsgType.TEXT:
      print(f"Ws got {msg.data}")
      if msg.data == 'close':
        await wsr.close()
      else:
        reply = "ws is up"
        await wsr.send_str('{"alert": "'+reply+'", "wsKey": "'+uid+'"}')
        
    elif msg.type == WSMsgType.ERROR:
      print('ws connection closed with exception %s' % wsr.exception())
  
  inv.ipc[uid] = None
  await wsr.close()
  rt.cancel()
  print(f"websocket connection {uid} closed")
  return wsr
  

async def webserver():
  port = 8080
  app = web.Application()
  dlp = params['downloadPath']
  app.add_routes([
    web.get('/a', handlerAjax),
    web.post('/a', handlerAjax),
    web.get('/ws', handlerWebsocket),
    web.static( f'/{dlp}', dlp, show_index=False ),
    web.static( '/', 'http', show_index=True )
  ])
  runner = web.AppRunner(app)
  await runner.setup()
  site = web.TCPSite(runner, 'localhost', port)
  await site.start()
  print(f"Web-interface started on http://127.0.0.1:{port}")


async def main():
  print("console interface started")
  if inv.getMyid() == 0:
    await cli.loadData(cui)
    cui.adoptMode('buddies', inv)
  
  # https://stackoverflow.com/questions/35223896/listen-to-keypress-with-asyncio
  # Create a StreamReader with the default buffer limit of 64 KiB.
  reader = asyncio.StreamReader()
  pipe = sys.stdin
  await client.loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), pipe)

  async for line in reader:
    try:
      command = cui.inputToCommand(line, inv)
      ret = await cli.run(cui, *command)
      if ret == -1:  
        return 0 # quits the app
    except MyException as err:
      cui.presentAlert(err)
    
@client.on(events.NewMessage)
async def newMessageHandler(event):
  command = ['consumeMessage', event]
  ret = await cli.run(cui, *command)
    
@client.on(events.MessageRead)
async def messageReadHandler(event):
  command = ['consumeMessageRead', event]
  ret = await cli.run(cui, *command)

       
with client:
  client.loop.create_task(webserver())
  client.loop.run_until_complete(main())
  print("Bye!")
