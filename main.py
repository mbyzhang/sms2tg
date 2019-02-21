#!/usr/bin/env python3
import logging
import at
import json
import datetime
import telegram
import telegram.ext
import sqlite3
import subprocess
import traceback

logging.basicConfig(level=logging.DEBUG)

def send_telegram(message: str):
    for recipient in config['telegram']['whitelist']:
        try:
            bot.send_message(recipient, message)
        except Exception as e:
            logging.error('Failed to send message to {}'.format(recipient))

def on_message(source: str, content: str, timestamp: datetime.datetime, pdu: str):
    logging.info('New message from {} at {}: {}'.format(source, timestamp.strftime('%c'), content))
    message = config['notification_format']['message'].format(source=source, timestamp=timestamp.strftime('%c'), 
        content=content, label=config['sms']['label'])
    dbc.execute('INSERT INTO sms(`from`, `to`, `content`, `timestamp`, `pdu`) VALUES(?, ?, ?, ?, ?)', 
        (source, config['sms']['label'], content, timestamp, pdu))
    dbconn.commit()
    send_telegram(message)

def on_call(source: str):
    logging.info('Incoming call from {}'.format(source))
    message = config['notification_format']['call'].format(source=source, timestamp=datetime.datetime.now(), label=config['sms']['label'])
    #dbc.execute('INSERT INTO sms(`from`, `to`, `content`, `timestamp`, `pdu`) VALUES(?, ?, ?, ?, ?)', 
    #    (source, config['sms']['label'], content, timestamp, pdu))
    #dbconn.commit()
    send_telegram(message)

outbox = dict()

def send_set_recipient(bot, update, args):
    chat_id = update.message.chat_id
    try:
        if str(chat_id) not in config['telegram']['whitelist']:
            raise Exception('Permission denied')
        
        if len(args) != 1:
            bot.send_message(chat_id=chat_id, text='Usage: /send <recipient>')
            return
        
        recipient = args[0]
        outbox[chat_id] = {
            'recipient': recipient,
            'content': None
        }

        bot.send_message(chat_id=chat_id, text='Next, send me the message content you want to send to {}'.format(recipient))


    except Exception as e:
        traceback.print_exc()
        bot.send_message(chat_id=chat_id, text=('Error: {}'.format(e)))

def message_handler(bot, update):
    chat_id = update.message.chat_id
    try:
        if str(chat_id) not in config['telegram']['whitelist']:
            raise Exception('Permission denied')
        
        if chat_id in outbox:
            outbox[chat_id]['content'] = update.message.text

            reply_markup = telegram.InlineKeyboardMarkup(
                [[telegram.InlineKeyboardButton('✅OK', callback_data='send_commit'), 
                telegram.InlineKeyboardButton('❌Cancel', callback_data='cancel')]])
            
            bot.send_message(
                chat_id=chat_id, 
                text='Sending the following message to {}\n\n{}\n\nAre you sure?'.format(
                    outbox[chat_id]['recipient'], outbox[chat_id]['content']), 
                reply_markup=reply_markup)
        else:
            raise Exception('For help, type /help')

    except Exception as e:
        traceback.print_exc()
        bot.send_message(chat_id=chat_id, text=('Error: {}'.format(e)))


def callback_handler(bot, update):
    query = update.callback_query
    chat_id = query.message.chat_id

    try:
        if query.data == 'cancel':
            del outbox[chat_id]
            query.edit_message_text('Cancelled')
        elif query.data == 'send_commit':
            msg = outbox[chat_id]
            bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
            at.send_message(msg['recipient'], msg['content'])
            query.edit_message_text('Finished')
    except KeyError:
        logging.error('No such message in chat {}'.format(chat_id))
        query.edit_message_text('Error: No such message')
    except Exception as e:
        traceback.print_exc()
        query.edit_message_text('Error: {}'.format(e))


if __name__=='__main__':
    logging.info('Starting sms2tg')
    config = json.loads(open('config.json', 'r').read())
    bot = telegram.Bot(token=config['telegram']['token'])
    updater = telegram.ext.Updater(bot=bot)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(telegram.ext.CommandHandler('send', send_set_recipient, pass_args=True))
    dispatcher.add_handler(telegram.ext.MessageHandler(telegram.ext.Filters.text, message_handler))
    dispatcher.add_handler(telegram.ext.CallbackQueryHandler(callback_handler))
    
    dbconn = sqlite3.connect(config['db']['path'])
    dbc = dbconn.cursor()

    updater.start_polling()

    at.init(config['sms']['device_path'], config['sms']['device_baudrate'])
    at.set_callback(on_message, on_call)
    at.set_reply_audio(config['phone']['autoreply_with_audio'], config['phone']['autoreply_audio_exec'])
    at.start()
    
