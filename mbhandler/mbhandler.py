import serial
import serial.tools.list_ports
import threading
import warnings
import queue as q

class NoMicrobitError(Exception):
    def __init__(self, message):

        # Call the base class constructor with the parameters it needs
        super(Exception, self).__init__(message)
        

BAUD = 115200
RUNNING = True
DEBUG = False

# Taken (and adapted) from https://github.com/ntoll/microrepl/blob/master/microrepl.py
def get_port():
    ports = list(serial.tools.list_ports.comports())
    for port, desc, opts in ports:
        if 'VID:PID=' in opts:
            s = opts.find('VID:PID=') + 8
            e = opts.find(' ',s)
            vid, pid = opts[s:e].split(':')
            vid, pid = int(vid, 16), int(pid, 16)
            if vid == 0x0D28 and pid == 0x0204:
                return port
    raise NoMicrobitError("No microbits found")
    return None

def __default_worker():

    port = get_port()
    
    s = serial.Serial(port)
    s.baudrate = BAUD
    s.parity = serial.PARITY_NONE
    s.databits = serial.EIGHTBITS
    s.stopbits = serial.STOPBITS_ONE

    state = {'a': False, 'b': False}
    
    while True:
        if not RUNNING:
            break
        try: 
            data = s.readline().decode("ascii").rstrip()
        except:
            continue
        if data == 'None':
            continue
        try:
            v = int(data.split(':')[0],16)
        except:
            continue
        b = (v & 1 == 1)
        v >>= 1
        a = (v & 1 == 1)
        v >>= 1
        z = v & 255
        v >>= 8
        y = v & 255
        v >>= 8
        x = v & 255
        if x > 127:
            x -= 256
        if y > 127:
            y -= 256
        if z > 127:
            z -= 256
        x *= -1
        y *= -1
        name = data.split(':')[1]
        e = {
            'name': name,
            'accelerometer': {
                'x': x,
                'y': y,
                'z': z,
            },
            'button_a': {
                'pressed': a,
                'down': a and not state['a'],
                'up': not a and state['a']
            },
            'button_b': {
                'pressed': b,
                'down': b and not state['b'],
                'up': not b and state['b']
            }
        }
        state['a'] = a
        state['b'] = b
        if DEBUG:
            print(e)
        post(e)

    s.close()

def __raw_worker():

    port = get_port()
    
    s = serial.Serial(port)
    s.baudrate = BAUD
    s.parity = serial.PARITY_NONE
    s.databits = serial.EIGHTBITS
    s.stopbits = serial.STOPBITS_ONE

    while True:
        if not RUNNING:
            break
        try: 
            data = s.readline().decode("ascii").rstrip()
        except:
            continue
        if data == 'None':
            continue
        if DEBUG:
            print(data)
        post(data)

    s.close()

def __pygame_init():
    global pygame
    import pygame
    global post
    global MICROBITEVENT
    MICROBITEVENT = pygame.USEREVENT
    pygame.USEREVENT += 1
    post = __pygame_post

def __pygame_post(e):
    if isinstance(e,str):
        e = {'message': e}
    ev = pygame.event.Event(MICROBITEVENT,**e)
    try:
        pygame.event.post(ev)
    except: # what's the error here if the queue is full/non-existent?
        pass

def __queue_init():
    global post
    global queue
    queue = q.Queue()
    post = __queue_post
    
def __queue_post(e):
    try:
        queue.put(e)
    except q.Full:
        pass

def init(**kwargs):
    global worker
    global DEBUG
    
    method = "queue"
    output = "default"
    worker = __default_worker
    
    if 'method' in kwargs:
        method = kwargs['method']
    if 'output' in kwargs:
        output = kwargs['output']
    if 'debug' in kwargs:
        DEBUG = True

    if output == "raw":
        worker = __raw_worker
    
    if method == "pygame":
        __pygame_init()
    else:
        __queue_init()

    t = threading.Thread(target=worker)
    t.daemon = True
    t.start()

def quit():
    global RUNNING
    RUNNING = False

# Should we clean up after ourselves?
