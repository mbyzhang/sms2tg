import logging
import at
import json
import datetime
import telegram
import sqlite3

logging.basicConfig(level=logging.DEBUG)

def on_message(source: str, content: str, timestamp: datetime.datetime, pdu: str):
    logging.info("New message from {} at {}: {}".format(source, timestamp.strftime('%c'), content))
    message = config['message_format'].format(source=source, timestamp=timestamp.strftime('%c'), 
        content=content, label=config['sms']['label'])
    dbc.execute('INSERT INTO sms(`from`, `to`, `content`, `timestamp`, `pdu`) VALUES(?, ?, ?, ?, ?)', 
        (source, config['sms']['label'], content, timestamp, pdu))
    dbconn.commit()
    for recipient in config['telegram']['whitelist']:
        try:
            bot.send_message(recipient, message)
        except Exception as e:
            logging.error("Failed to send message to {}".format(recipient))

if __name__=='__main__':
    logging.info("Starting sms2tg")
    config = json.loads(open('config.json', 'r').read())
    bot = telegram.Bot(token=config['telegram']['token'])
    dbconn = sqlite3.connect(config['db']['path'])
    dbc = dbconn.cursor()
    at.init(config['sms']['device_path'], config['sms']['device_baudrate'])
    at.listen(on_message)
    