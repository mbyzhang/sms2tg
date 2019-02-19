import logging
import time
import subprocess
import threading
import traceback
import comm
import sms

def init(port: str, baudrate: int):
    comm.init(port, baudrate)

    # test device
    comm.execute('AT')

    # disable echo
    comm.execute('ATE0')

    # enable call indication
    comm.execute('AT+CLIP=1')

def set_callback(on_message, on_call = None, on_call_end = None):
    global message_callback, call_callback, call_end_callback
    message_callback = on_message
    call_callback = on_call
    call_end_callback = on_call_end

def set_reply_sms(enabled: bool = False, content: str = ''):
    pass

def set_reply_audio(enabled: bool = False, exec: list = []):
    global reply_audio_enabled, reply_audio_exec
    reply_audio_enabled = enabled
    reply_audio_exec = exec

def start():
    fetch_unread_messages()
    poll()

def handle_message(pdu, index):
    result = sms.decode(pdu, index)
    if result is not None:
        message_callback(source=result['source'], content=result['content'], timestamp=result['timestamp'], pdu=result['pdu'])
        for item in result['indice']:
            comm.execute('AT+CMGD={}'.format(item))

def decode_response(line: str):
    name, args = line.split(' ')
    args = args.split(',')
    name = name.rstrip(':').lstrip('+')
    return (name, args)

def fetch_unread_messages():
    logging.info('Fetching unread messages')
    result = comm.execute('AT+CMGL=4')
    p = 0

    while p < len(result):
        line = result[p]
        if line.startswith('+'):
            name, args = decode_response(line)
            assert(name == 'CMGL')
            handle_message(result[p + 1], args[0])
            p += 1
        p += 1

def end_call():
    comm.execute('ATH')
    if call_end_callback is not None: 
        call_end_callback(False)

reply_audio_terminated = False

def wait_audio_end(reply_audio_proc):
    global reply_audio_terminated
    reply_audio_proc.communicate()
    if not reply_audio_terminated:
        logging.info('Audio playback finished, ending the call')
        end_call()

def poll():
    global reply_audio_terminated
    logging.info('Polling new messages')
    while True:
        try: 
            line = comm.getline()
            if line.startswith('+'):
                name, args = decode_response(line)
                if name == 'CMTI':
                    logging.debug('Incoming SMS')
                    index = int(args[1])
                    logging.debug('SMS index is {}'.format(index))
                    result = comm.execute('AT+CMGR={}'.format(index))
                    assert(len(result) == 4 and result[0].startswith('+CMGR'))
                    handle_message(result[1], index)

                elif name == 'CLIP':
                    logging.debug('Incoming call')
                    reply_audio_terminated = False

                    number = args[0].strip('"')
                    if reply_audio_enabled:
                        comm.execute('ATA')
                        logging.info('Playing autoreply audio')
                        reply_audio_proc = subprocess.Popen(reply_audio_exec)
                        reply_audio_th = threading.Thread(target=wait_audio_end, args=(reply_audio_proc, ))
                        reply_audio_th.start()
                    else:
                        comm.execute('AT+CHUP')
                    if call_callback is not None:
                        call_callback(source=number)
                    
            elif line == "NO CARRIER":
                logging.info('Partner ended the call')
                reply_audio_terminated = True
                reply_audio_proc.terminate()
                if call_end_callback is not None: 
                    call_end_callback(True)
        
        except TimeoutError:
            pass
        except Exception as e:
            logging.warning(e)
            traceback.print_exc()
