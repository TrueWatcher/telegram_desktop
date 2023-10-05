tgtlc is a free desktop Telegram client,
written in Python and based on Telethon and asincio libraries.

It provides two user interfaces:
- console interface, with basic message handling from a terminal window and keyboard, intented for rapid sharing of files and links over Telegram
- web interface, exposed at http://localhost:8080/index.html is more colourful and supports also features like read receipts and reply-to

The app has been tested with Python 3.8 and 3.9 on Ubuntu 20.04 and Linux Mint DE. Web UI tested on Chromium and Firefox, recent as of 2023. Not tested (yet) on Windows or MacOS.

Installation:
- make sure you have Python >= 3.8 installed
        sudo apt install python3.8 python3.8-venv
  
- download the app folder with files

- create a virtual environment and install dependencies
        cd telegram_desktop
        python3.8 -m venv venv
        source venv/bin/activate
        python --version      # 3.8.*
        python -m pip install --upgrade pip
        python -m pip --version       # >= 22.3
        python -m pip install -r freeze.txt
        deactivate

- get API ID and API hash from Telegram, as I cannot share mine here :( ,
  enter them into example_params_json.txt, rename it to params.json
  
- now run it !
        cd telegram_desktop
        venv/bin/python3.8 client.py
  in the terminal window you will be prompted to enter your phone number, confirmation code (sent to your other Telegram device), and password (if you have 2FA). After successful login, your credentials will be stored in a file and not asked for agatn. To logout, just delete the session file.
  
Instructions for the console UI [here](help.txt).

The web UI is exposed at http://localhost:8080/index.html and also uses WebSockets ws://localhost:8080 . 
It works, but is all experimental and has no help page yet.

---------------
This app is a free software under GPL 3.0 license.
[Telethon library](https://docs.telethon.dev/en/stable/) is under MIT license.

