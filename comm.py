import threading
import logging
import serial
import time
from queue import Queue

collect_response = list()
collect_lock = threading.Lock()
collect_lock.acquire()

queue = Queue()

def write(b):
    data = b.encode('ascii')
    ser.write(data)
    ser.flush()
    logging.debug('> {}'.format(data))

def read():
    line = ser.readline()
    if len(line) == 0:
        raise TimeoutError()
    else:
        logging.debug('< {}'.format(line))
        return line.decode('ascii').rstrip()

def getline():
    return queue.get()

def init(port: str, baudrate: int, timeout: int = 10):
    global ser
    ser = serial.Serial(port, baudrate, timeout=timeout)
    th = threading.Thread(target=poll)
    th.start()

def collect():
    global collect_enabled, collect_response
    collect_enabled = True
    collect_response = list()

def wait():
    global collect_enabled
    collect_lock.acquire()
    collect_enabled = False
    return collect_response

def execute(cmd: str, body: str = None, check_error: bool = True):
    write(cmd)
    collect()
    write('\r\n')
    if body is not None:
        time.sleep(0.5) # ugly workaround
        write(body + '\x1A')
    response = wait()
    del response[0] # useless newline
    
    if body is not None:
        del response[0] # useless > character

    if check_error and response[-1] != 'OK':
        raise Exception('Error executing AT command')
    
    return response

def poll():
    global collect_enabled, collect_response
    collect_enabled = False
    while True:
        try:
            line = read()
            if collect_enabled:
                collect_response.append(line)
                if line == 'OK' or line == 'ERROR' or line.startswith('+CMS ERROR') or line.startswith('+CME ERROR'):
                    # exit collect mode
                    collect_enabled = False
                    collect_lock.release()
            else:
                queue.put(line)
        except TimeoutError:
            pass

