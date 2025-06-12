from concurrent import futures
from Xlib.display import Display
from Xlib.ext import record
from Xlib import X, protocol
import Xlib, pyautogui, os
import cv2, numpy as np
from fuzzywuzzy import fuzz
from concurrent.futures import ThreadPoolExecutor
from concurrent import futures
from timeit import default_timer as timer
import tesserocr
import json
import copy
import time

with open('dpln/clues.json', 'r') as file:
    clues_data = json.load(file)

clues = {}
for clue in clues_data['clues']:
    clues[clue['clueid']] = clue['hinten']

maps = {}
for map in clues_data['maps']:
    maps[map['x']+','+map['y']] = map['clues']

def find_next_clue_map(x,y,direction,clue_name):
    current_x = copy.copy(x)
    current_y = copy.copy(y)

    direction_clues = {}

    for _ in range(10):
        if direction == 'up':
            current_y -= 1

        if direction == 'down':
            if current_x == -25 and current_y == 30:
                current_x -= 1

            elif current_x == -29 and current_y == -53:
                current_x += 1
            
            elif current_x == -28 and current_y == -52:
                current_x += 1
            
            elif current_x == 13 and current_y == -58:
                current_x += -1

            current_y += 1

        if direction == 'left':
            if current_x == -28 and current_y == -52:
                current_y -= 1

            elif current_x == -27 and current_y == -51:
                current_y -= 1

            elif current_x == -26 and current_y == -50:
                current_y -= 1

            elif current_x == -25 and current_y == -49:
                current_y -= 1

            elif current_x == -29 and current_y == -61:
                current_y += 1

            elif current_x == -26 and current_y == 37:
                current_y -= 1
                current_x -= 1

            elif current_x == -25 and current_y == 40:
                current_y += 1

            current_x -= 1

        if direction == 'right':
            if current_x == -26 and current_y == 31:
                current_y -= 1

            elif current_x == -27 and current_y == -51:
                current_y += 1

            elif current_x == -26 and current_y == -50:
                current_y += 1

            elif current_x == -30 and current_y == -60:
                current_y -= 1

            elif current_x == -28 and current_y == 36:
                current_y += 1
                current_x += 1

            elif current_x == 12 and current_y == -57:
                current_y -= 1

            elif current_x == -26 and current_y == 41:
                current_y -= 1
            
            current_x += 1

        map_key = str(current_x)+','+str(current_y)

        if map_key not in maps:
            continue

        for clue in maps[map_key]:
            if clues[clue] == clue_name:
                return 100, current_x, current_y, clue_name
            if clues[clue] not in direction_clues:
                direction_clues[clues[clue]] = (current_x,current_y)

    best_match = (0, None, None, None)
    for key in direction_clues:
        ratio = fuzz.ratio(clue_name, key)
        if ratio > best_match[0]:
            best_match = (ratio, direction_clues[key], key)

    if best_match[1] is None:
        return (0, None, None, None)
    
    return best_match[0], best_match[1][0], best_match[1][1], best_match[2]

def is_dofus_window(window):
    wm_class = window.get_wm_class()
    return wm_class and wm_class[0] == 'Dofus.x64'

def get_dofus_window(display: Display):
    root = display.screen().root
    window = root.get_full_property(display.intern_atom('_NET_ACTIVE_WINDOW'), Xlib.Xatom.WINDOW).value[0]
    window = display.create_resource_object('window', window)

    if is_dofus_window(window):
        return window

    # window_ids = root.get_full_property(display.intern_atom('_NET_CLIENT_LIST'),Xlib.Xatom.WINDOW).value
    #
    # for window_id in window_ids: 
    #     window = display.create_resource_object('window', window_id)
    #     if is_dofus_window(window):
    #         return window

    return None

def imread(path):
    img = cv2.imread(path)

    height, width, channels = img.shape

    lst = np.array([[255,255,255]])

    for x in range(0, width):
        for y in range(0, height):
            if img[y, x] not in lst:
                img[y, x] = [0,0,0]

    return img

def locateAll(a,b):
    boxes = []
    try:
        g = pyautogui.locateAll(a,b)
        while True:
            try:
                box = next(g)
                if isinstance(box, pyautogui.ImageNotFoundException):
                    break
                boxes.append(box)
            except: break

        
    except pyautogui.ImageNotFoundException: pass

    return boxes
    
up = imread('up.png')
right = imread('right.png')
down = imread('down.png')
left = imread('left.png')

def get_next_clue_position():
    start = timer()

    try:
        os.remove('position.png')
    except: pass

    img = pyautogui.screenshot('position.png', region=(0,140,260,25))
    text = tesserocr.image_to_text(img, path='./tessdata')

    try:
        [x,y] = text.split(',')[:2]
        [y] = y.rsplit('-', 1)[:1]
        [y] = y.strip().split(' ')[:1]
        x = int(x.strip())
        y = int(y.strip())
    except:
        print('Error while getting map position: ', text)
        [x,y] = pyautogui.prompt(title='Enter map position [x y]').split(' ')[:2]
        x = int(x.strip())
        y = int(y.strip())

    end = timer()
    print('get_next_clue_position: ', end - start)
    
    return x, y

def get_next_clue_direction():
    start = timer()

    try:
        os.remove('direction.png')
    except: pass

    pyautogui.screenshot('direction.png', region=(10,400,25,400))
    img = imread('direction.png')

    current_top = 0
    direction = ''

    for d in ('up', 'down', 'left', 'right'):
        d_image = imread(d +'.png')
    
        for pos in locateAll(d_image, img):
            if pos.top >= current_top:
                current_top = pos.top
                direction = d

    end = timer()
    print('get_next_clue_direction: ', end - start)
    
    return direction

location = imread('location.png')

def get_next_clue_name():
    start = timer()

    img = pyautogui.screenshot('hunter_panel.png', region=(33,400,280,300))
    img = imread('hunter_panel.png')
    os.remove('hunter_panel.png')

    try:
        [pos] = locateAll(location, img)
    except: return '???'

    img = pyautogui.screenshot(None, region=(33, 393 + pos.top.item(), 120,42))
    text = tesserocr.image_to_text(img, path='./tessdata')

    end = timer()
    print('get_next_clue_name: ', end - start)

    return text.replace('\n', ' ').strip()

def get_next_clue():
    excecutor = ThreadPoolExecutor()
    position = excecutor.submit(get_next_clue_position)
    direction = excecutor.submit(get_next_clue_direction)
    name = excecutor.submit(get_next_clue_name)

    for _ in futures.as_completed([position, direction, name]):
        continue

    x, y = position.result()
    direction = direction.result()
    clue_name = name.result()

    return (x, y, direction, clue_name)

def phorreur_travel(x,y,direction):
    if direction == 'up':
        y -= 10

    if direction == 'down':
        y += 10

    if direction == 'left':
        x -= 10

    if direction == 'right':
        x += 10

    return x, y

display = Display()

    
def handler(reply):
    data = reply.data
    while len(data):
        event, data = protocol.rq.EventField('').parse_binary_value(data, display.display, None, None)
        detail = copy.copy(event.detail)
        if event.type == X.KeyPress and detail == 112:
            img = pyautogui.screenshot('hunter_panel.png', region=(33,400,280,300))
            img = imread('hunter_panel.png')
            os.remove('hunter_panel.png')
            try:
                [pos] = locateAll(location, img)
                mx, my = pyautogui.position()
                pyautogui.click(33 + pos.left + 8, 400 + pos.top + 8)
                pyautogui.moveTo(mx, my)
                detail = 119
                time.sleep(0.3)
            except: continue
        if event.type == X.KeyPress and detail == 119:
            x, y, direction, clue_name = get_next_clue()

            if 'Drhelle' in clue_name:
                x, y = phorreur_travel(x, y, direction)
            else:
                ratio, x, y, clue_name_matched = find_next_clue_map(x,y,direction,clue_name)
                if ratio < 40:
                    pyautogui.alert('Clue not found <> ' + str(ratio) + ' <> ' + clue_name + ' <> ' + str(clue_name_matched))
                    continue

                print(x,y, direction, clue_name, clue_name_matched)

            mx, my = pyautogui.position()
            pyautogui.click(216, 1065)
            pyautogui.typewrite('/travel ' + str(x) + ' ' + str(y))
            pyautogui.press('enter')
            
            time.sleep(0.3)

            pyautogui.press('enter')
            pyautogui.moveTo(mx, my)

            if 'Drhelle' in clue_name:
                pyautogui.alert('Going to DrHeller \\!/')

root = display.screen().root

ctx = display.record_create_context(
    0,
    [record.AllClients],
    [{
        'core_requests': (0, 0),
        'core_replies': (0, 0),
        'ext_requests': (0, 0, 0, 0),
        'ext_replies': (0, 0, 0, 0),
        'delivered_events': (0, 0),
        'device_events': (X.KeyReleaseMask, X.ButtonReleaseMask),
        'errors': (0, 0),
        'client_started': False,
        'client_died': False,
    }]
)

display.record_enable_context(ctx, handler)

