"""
a free Telegram desktop client (based on the Telethon library) by TrueWatcher 2022-2023
https://github.com/TrueWatcher/telegram_desktop
1.6.0  05.10.2023 cleanup, prepared as git repo
1.7.0  07.10.2023 added Forward command to consoleui.py and cli.py, refactored client.py
1.7.1  08.10.2023 added type annotations to several files
1.7.2  09.10.2023 updated venv to 3.9, code improvements
1.8.0  10.10.2023 fixed rendering of fwd_from
1.8.1  11.10.2023 more annotations and cleaning
1.8.2  11.10.2023 refactored client.py
1.9.0  12.10.2023 added bash scripts and icon
"""
from telethon import TelegramClient, events
import asyncio
import sys
from aiohttp import web, WSMsgType
from aiohttp_index import IndexMiddleware
from myexception import MyException
from consoleui import ConsoleUi
from inventory import Inventory
from cli import Cli
from webbridge import WebBridge
import json
import uuid
from typing import List, Dict, Union, Awaitable

DataType = Union[bool,int,str]

class Client:

  def __init__(self) -> None:
    print('tgtlc, a free Telegram desktop client by TrueWatcher 2022-2023')
    self.inv: Inventory              = Inventory()
    self.params: Dict[str,DataType]  = self.inv.loadParams()
    #print(params) 
    self.cui: ConsoleUi              = ConsoleUi()
    self.client: TelegramClient      = TelegramClient('anon', self.params['apiId'], self.params['apiHash'])
    print("connected to Telegram")
    self.cli: Cli                    = Cli(self.inv, self.params, self.client)
    
  def startUp(self) -> None:  
    print("setting up the main loop...")
    with self.client:
      self.setTGhandlers()
      self.client.loop.create_task(self.loadMessages())
      self.client.loop.create_task(self.webserver())
      self.client.loop.run_until_complete(self.consoleHandler())
    print("Bye!")

  # define keyboard listener

  async def consoleHandler(self) -> int:
    print("console interface started")
    # https://stackoverflow.com/questions/35223896/listen-to-keypress-with-asyncio
    # Create a StreamReader with the default buffer limit of 64 KiB.
    reader = asyncio.StreamReader()
    pipe = sys.stdin
    await self.client.loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), pipe)

    async for line in reader:
      try:
        command = self.cui.inputToCommand(line, self.inv)
        ret = await self.cli.run(self.cui, *command)
        if ret == -1:  
          return 0 # quits the app
      except MyException as err:
        self.cui.presentAlert(str(err))
        
    return 0  # not to get here

  # attach listeners for incoming messages of the Telegram client    

  def setTGhandlers(self) -> None:
    @self.client.on(events.NewMessage)
    async def newMessageHandler(event):
      command = ['consumeMessage', event]
      try:
        ret = await self.cli.run(self.cui, *command)
      except MyException as err:
        self.cui.presentAlert(str(err))
        
    @self.client.on(events.MessageRead)
    async def messageReadHandler(event):
      command = ['consumeMessageRead', event]
      ret = await self.cli.run(self.cui, *command)


  # define listeners for WebUI requests (AJAX and WS)

  async def handlerAjax(self, request: web.Request) -> web.Response:
    print('')
    #print(f"Ajax request:{request}")
    print(f"query str:{request.query_string}")
    #print(f"query:{request.query}")
    #if request.can_read_body:
    #  print(f"body text:{await request.text()}") breaks multipart reader
    
    wb = WebBridge()
    try:
      await wb.parseRequest(request, self.inv)
      command = wb.getCommand()
      print(f"webUi entry mode:{wb.getMode()}, currentDialog:{wb.getCurrentDialog()}")
      ret = await self.cli.run(wb, *command)
      res = wb.getResult()
    except MyException as err:
      res = wb.presentAlert(str(err))
    
    print(f"webUi exit mode:{wb.getMode()}, currentDialog:{wb.getCurrentDialog()}")
    print(f"my response:{res}")
    return web.json_response(res)

  async def handlerWebsocket(self, request: web.Request):
  # https://docs.aiohttp.org/en/stable/web_quickstart.html#websockets
    wsr = web.WebSocketResponse()
    await wsr.prepare(request)
    uid = str(uuid.uuid4())
    inv = self.inv
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
      
    rt = self.client.loop.create_task(resend(wsr))  
    
    async for msg in wsr:
      if msg.type == WSMsgType.TEXT:
        print(f"Ws got {msg.data}")
        if msg.data == 'close':
          await wsr.close()
        else:
          reply = '---' #reply = "ws is up"
          await wsr.send_str('{"alert": "'+reply+'", "wsKey": "'+uid+'"}')
          
      elif msg.type == WSMsgType.ERROR:
        print('ws connection closed with exception %s' % wsr.exception())
    
    #inv.ipc[uid] = None
    if inv.ipc[uid]:  del inv.ipc[uid]
    await wsr.close()
    rt.cancel()
    print(f"websocket connection {uid} closed")
    return wsr

  # put all web appliances together  

  async def webserver(self) -> None:
    port = int(self.params['webUiPort'])
    app = web.Application(middlewares=[IndexMiddleware()])
    dlp = str(self.params['downloadPath'])
    app.add_routes([
      web.get('/a', self.handlerAjax),
      web.post('/a', self.handlerAjax),
      web.get('/ws', self.handlerWebsocket),
      web.static( f'/{dlp}', dlp, show_index=False ),
      web.static( '/', 'http', show_index=False )
    ])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', port)
    await site.start()
    print(f"Web-interface started on http://127.0.0.1:{port}")    
      
  # load messages from the Telegram client (one shot)

  async def loadMessages(self) -> int:
    if self.inv.getMyid() == 0:
      await self.cli.loadData(self.cui)
      self.cui.adoptMode('buddies', self.inv)
    return 0

#------------------------------------------------------

Client().startUp()
