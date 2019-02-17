import logging
import serial
import cdma
import time

def write(b):
    out = (b + '\r\n').encode('ascii')
    ser.write(out)
    ser.flush()
    logging.debug('< {}'.format(out))


def read():
    line = ser.readline()
    if len(line) == 0:
        raise TimeoutError()
    else:
        logging.debug('> {}'.format(line))
        return line.decode('ascii').rstrip()

def execute(cmd: str):
    write(cmd)
    line = read()
    assert(line == cmd)
    result = list()
    while line != 'ERROR' and line != 'OK':
        line = read()
        result.append(line)
    if line == 'ERROR':
        raise Exception('Error executing AT command: {}'.format(cmd))
    return result

def init(port: str, baudrate: int):
    global ser
    ser = serial.Serial(port, baudrate, timeout=10)
    result = execute('AT')
    assert(result[0] == 'OK')

def listen(callback):
    fetch_unread(callback)
    poll(callback)

def fetch_unread(callback):
    logging.debug('Fetching unread messages')
    result = execute('AT+CMGL=4')

    for item in result:
        if item != '' and item != 'OK' and not item.startswith('+CMGL'):
                message = cdma.decode(bytearray.fromhex(item))
                callback(source=message['source'], content=message['content'], timestamp=message['timestamp'], pdu=item)
    
    execute('AT+CMGD=,2')

def poll(callback):
    logging.debug('Polling new messages')
    while True:
        try: 
            line = read()
            if line.startswith('+CMTI'):
                _, args = line.split(' ')
                index = args.split(',')[1]
                logging.debug('SMS index is {}'.format(index))
                result = execute('AT+CMGR={}'.format(index))
                assert(len(result) == 4 and result[0].startswith('+CMGR'))
                pdu = result[1]
                message = cdma.decode(bytearray.fromhex(pdu))
                callback(source=message['source'], content=message['content'], timestamp=message['timestamp'], pdu=pdu)
                execute('AT+CMGD={}'.format(index))
        except TimeoutError:
            pass
        except Exception as e:
            logging.warning(e)
            time.sleep(0.5)
            ser.flushinput()



    