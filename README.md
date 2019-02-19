# sms2tg

Forward SMS messages received from a CDMA module to Telegram.

## Features

* Forward incoming SMS instantly to your Telegram
* Forward incoming call notification to your Telegram
* Auto-reply incoming call with prerecorded audio
* Local SQLite database for SMS backup

## Requirements

* Python 3
* Telegram bot token

## Supported Devices

* SIM2000C (tested)
* other CDMA modules (not tested)

## Installation

```
pip3 install -r requirements.txt
cp data.db.sample data.db
cp config.json.sample config.json
```

and edit `config.json` according to your own configuration.

## Run

```
python3 main.py
```

## TODO

* Message sending support
* Autoreply on incoming SMS
* Multiple device support
* Forward SMS to Mail, Slack, IRC, etc.
* GSM module support
