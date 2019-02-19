#!/usr/bin/env python3
import logging
import at
import json
import datetime
import telegram
import sqlite3
import subprocess

logging.basicConfig(level=logging.DEBUG)

def send_telegram(message: str):
    for recipient in config['telegram']['whitelist']:
        try:
            bot.send_message(recipient, message)
        except Exception as e:
            logging.error("Failed to send message to {}".format(recipient))

def on_message(source: str, content: str, timestamp: datetime.datetime, pdu: str):
    logging.info("New message from {} at {}: {}".format(source, timestamp.strftime('%c'), content))
    message = config['notification_format']['message'].format(source=source, timestamp=timestamp.strftime('%c'), 
        content=content, label=config['sms']['label'])
    dbc.execute('INSERT INTO sms(`from`, `to`, `content`, `timestamp`, `pdu`) VALUES(?, ?, ?, ?, ?)', 
        (source, config['sms']['label'], content, timestamp, pdu))
    dbconn.commit()
    send_telegram(message)

def on_call(source: str):
    logging.info("Incoming call from {}".format(source))
    message = config['notification_format']['call'].format(source=source, timestamp=datetime.datetime.now(), label=config['sms']['label'])
    #dbc.execute('INSERT INTO sms(`from`, `to`, `content`, `timestamp`, `pdu`) VALUES(?, ?, ?, ?, ?)', 
    #    (source, config['sms']['label'], content, timestamp, pdu))
    #dbconn.commit()
    send_telegram(message)


if __name__=='__main__':
    logging.info("Starting sms2tg")
    config = json.loads(open('config.json', 'r').read())
    bot = telegram.Bot(token=config['telegram']['token'])
    dbconn = sqlite3.connect(config['db']['path'])
    dbc = dbconn.cursor()
    at.init(config['sms']['device_path'], config['sms']['device_baudrate'])
    at.set_callback(on_message, on_call)
    at.set_reply_audio(config['phone']['autoreply_with_audio'], config['phone']['autoreply_audio_exec'])
    at.start()
    
