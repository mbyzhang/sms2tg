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
    result = execute('AT+CLIP=1')
    assert(result[0] == 'OK')

def listen(on_message, on_call):
    fetch_unread(on_message)
    poll(on_message, on_call)

long_message_sto = dict()

def handle_message(pdu, index, on_message):
    message = cdma.decode(bytearray.fromhex(pdu))
    if message['long_message']:
        lm_ref = message['long_message_ref']
        lm_total = message['long_message_total']
        lm_index = message['long_message_index']
        logging.info('Received long message ({}/{}) with ref number {}'.format(lm_index, lm_total, lm_ref))
        if lm_ref not in long_message_sto:
            long_message_sto[lm_ref] = {
                'length': 0,
                'content': lm_total * [None],
                'indice': list(),
                'pdu': list()
            }
        long_message_sto[lm_ref]['content'][lm_index - 1] = message['content']
        long_message_sto[lm_ref]['length'] += 1
        long_message_sto[lm_ref]['indice'].append(index)
        long_message_sto[lm_ref]['pdu'].append(pdu)
        if long_message_sto[lm_ref]['length'] == lm_total:
            concated_content = ''.join(long_message_sto[lm_ref]['content'])
            concated_pdu = '\n'.join(long_message_sto[lm_ref]['pdu'])
            on_message(source=message['source'], content=concated_content, timestamp=message['timestamp'], pdu=concated_pdu)
            for item in long_message_sto[lm_ref]['indice']:
                execute('AT+CMGD={}'.format(item))

            del long_message_sto[lm_ref]

    else:
        on_message(source=message['source'], content=message['content'], timestamp=message['timestamp'], pdu=pdu)
        execute('AT+CMGD={}'.format(index))

def decode_response(line: str):
    name, args = line.split(' ')
    args = args.split(',')
    name = name.rstrip(':').lstrip('+')
    return (name, args)


def fetch_unread(on_message):
    logging.debug('Fetching unread messages')
    result = execute('AT+CMGL=4')

    p = 0

    while p < len(result):
        line = result[p]
        if line.startswith('+'):
            name, args = decode_response(line)
            assert(name == 'CMGL')
            handle_message(result[p + 1], args[0], on_message)
            p += 1
        p += 1
    

def poll(on_message, on_call):
    logging.debug('Polling new messages')
    while True:
        try: 
            line = read()
            if line.startswith('+'):
                name, args = decode_response(line)
                if name == 'CMTI':
                    index = int(args[1])
                    logging.debug('SMS index is {}'.format(index))
                    result = execute('AT+CMGR={}'.format(index))
                    assert(len(result) == 4 and result[0].startswith('+CMGR'))
                    handle_message(result[1], index, on_message)

                elif name == 'CLIP':
                    number = args[0].strip('"')
                    execute('AT+CHUP')
                    on_call(source=number)

        except TimeoutError:
            pass
        except Exception as e:
            logging.warning(e)
            time.sleep(0.5)

