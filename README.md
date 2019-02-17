# sms2tg

Forward SMS messages received from a CDMA module to Telegram.

## Features

* Forward incoming SMS instantly to your Telegram
* Local SQLite database for SMS backup

## Requirements

* Python 3
* Telegram bot token

## Supported Devices

* SIM2000C
* other CDMA modules

## Installation

```
pip3 install -r requirements
cp data.db.sample data.db
cp config.json.sample config.json
```

and edit `config.json` according to your own configuration.

## Run

```
python3 main.py
```

## TODO

* Multiple device support
* Forward SMS to Mail, Slack, IRC, etc.
* Long message support
* GSM module support
