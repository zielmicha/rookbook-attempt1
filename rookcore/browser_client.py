import sys, json

websocket = None
on_message_callback = lambda data: None
on_close_callback = lambda: None

def on_close(ev):
    on_close_callback()

def on_message(ev):
    data = ev.data
    if data[0] == 'F':
        filename, data = data.split('\n', 1)
        with open(filename, 'w') as f:
            f.write(data)
    elif data[0] == 'E':
        code = data[1:]
        exec(code)

def ws_url(url):
    if '://' in url:
        return url
    else:
        return ('wss://' if browser.window.location.protocol == 'https:' else 'ws://') + browser.window.location.host + url

def start(url):
    global websocket
    websocket = browser.websocket.WebSocket(ws_url(url))

    websocket.bind('close', on_close)
    websocket.bind('message', on_message)
