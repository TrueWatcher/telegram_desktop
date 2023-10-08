"""
a free Telegram desktop client (based on the Telethon library) by TrueWatcher 2022-2023
https://github.com/TrueWatcher/telegram_desktop
1.6.0  05.10.2023 cleanup, prepared as git repo
1.7.0  07.10.2023 added Forward command to consoleui.py and cli.py, refactored client.py
1.7.1  08.10.2023 added type annotations to several files
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

# globals that keep async stuff connected
client = None
cli = None
cui = None
inv = None
params = None


def startUp():
  global client, cui, cli, inv, params
  print('tgtlc, a free Telegram desktop client by TrueWatcher 2022-2023')
  inv = Inventory()
  params = inv.loadParams()
  #print(params)    
  client = TelegramClient('anon', params['apiId'], params['apiHash'])
  print("connected to Telegram")
  cui = ConsoleUi()
  cli = Cli(inv, params, client)
  print("setting up the main loop...")
  with client:
    setTGhandlers(cli, cui)
    client.loop.create_task(loadMessages())
    client.loop.create_task(webserver())
    client.loop.run_until_complete(consoleHandler())
  print("Bye!")

# define keyboard listener

async def consoleHandler():
  global inv, cli, cui
  print("console interface started")
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

# attach listeners for incoming messages from the Telegram client    

def setTGhandlers(cli, cui):
  @client.on(events.NewMessage)
  async def newMessageHandler(event):
    command = ['consumeMessage', event]
    ret = await cli.run(cui, *command)
      
  @client.on(events.MessageRead)
  async def messageReadHandler(event):
    command = ['consumeMessageRead', event]
    ret = await cli.run(cui, *command)


# define listeners for WebUI requests (AJAX and WS)

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
    
  rt = client.loop.create_task(resend(wsr))  
  
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

# put all web appliances together  

async def webserver():
  port = 8080
  app = web.Application()
  dlp = params['downloadPath']
  app.add_routes([
    web.get('/a', handlerAjax),
    web.post('/a', handlerAjax),
    web.get('/ws', handlerWebsocket),
    web.static( f'/{dlp}', dlp, show_index=False ),
    web.static( '/', 'http', show_index=False )
  ])
  runner = web.AppRunner(app)
  await runner.setup()
  site = web.TCPSite(runner, 'localhost', port)
  await site.start()
  print(f"Web-interface started on http://127.0.0.1:{port}")    
    
# load messages from the Telegram client (one shot)

async def loadMessages():
  global inv, cli, cui
  if inv.getMyid() == 0:
    await cli.loadData(cui)
    cui.adoptMode('buddies', inv)
  return 0

#------------------------------------------------------

startUp()
