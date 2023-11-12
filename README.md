tgtlc, a free desktop Telegram client,
written in Python and based on Telethon and asyncio libraries.

It provides two user interfaces:
- console interface, with basic message handling from a terminal window and keyboard, intended for rapid sharing of files and links over Telegram ([screnshot 1](screenshots/tgtlc_1_8_2_dialog_message.png))
- web interface, exposed at http://localhost:8080/index.html is more colourful and supports also features like read receipts and reply-to

The app has been tested with Python 3.9 on Ubuntu 20.04, Linux Mint DE 5 and Windows 10.
Web UI tested with Chromium and Firefox, recent as of 2023. Not tested (yet) on Windows < 10 or MacOS.

Installation:
- make sure you have Python >= 3.8 installed

        sudo apt install software-properties-common
        sudo add-apt-repository ppa:deadsnakes/ppa
        sudo apt update
        sudo apt install python3.9 python3.9-venv

- download the app folder with files

- create a virtual environment and install dependencies

        cd telegram_desktop
        python3.9 -m venv venv
        source venv/bin/activate
        python --version      # 3.9.*
        python -m pip install --upgrade pip
        python -m pip --version       # >= 23.2
        python -m pip install -r freeze.txt
        deactivate

- obtain your API ID and hash from Telegram, because I cannot share mine here :( ,
  enter them into _example_params_json.txt_, rename it to _params.json_

- create the _Downloads_ folder

        mkdir Downloads
        mkdir uploadTmp

  if you later decide to remove its content, remove also _medialinks.json_

- now run it !

        cd telegram_desktop
        venv/bin/python3.9 client.py

  in the terminal window you will be prompted to enter your phone number, confirmation code (sent to your other Telegram device), and password (if you have 2FA). After successful login, your credentials will be stored in a file and not asked for agatn. To logout, just delete the session file.

Instructions for the console UI [here](help.txt).

The web UI is exposed at http://localhost:8080/index.html and also uses WebSockets ws://localhost:8080 .
It works, but is all experimental and has no help page yet.

---------------
This app is a free software under the GPL 3.0 license.
[Telethon library](https://docs.telethon.dev/en/stable/) is under the MIT license.

