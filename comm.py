import threading
import logging
import serial
from queue import Queue

collect_response = list()
collect_lock = threading.Lock()
collect_lock.acquire()

queue = Queue()

def write(b):
    data = b.encode('ascii')
    ser.write(data)
    ser.flush()
    logging.debug('< {}'.format(data))

def read():
    line = ser.readline()
    if len(line) == 0:
        raise TimeoutError()
    else:
        logging.debug('> {}'.format(line))
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

def execute(cmd: str, check_error: bool = True):
    write(cmd)
    collect()
    write('\r\n')
    response = wait()
    del response[0] # useless newline

    if check_error and response[-1] == 'ERROR':
        raise Exception('Error executing AT command')
    if response[-1] != 'OK' and response[-1] != 'ERROR':
        raise Exception('Unexpected response received')
    
    return response

def poll():
    global collect_enabled
    collect_enabled = False
    while True:
        try:
            line = read()
            if collect_enabled:
                collect_response.append(line)
                if line == 'OK' or line == 'ERROR':
                    # exit collect mode
                    collect_enabled = False
                    collect_lock.release()
            else:
                queue.put(line)
        except TimeoutError:
            pass

