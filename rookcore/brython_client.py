import sys, browser, browser.websocket, json

websocket = None
on_message_callback = lambda data: None
on_close_callback = lambda: None

def add_module(modname, data, is_pkg):
    browser.window.__BRYTHON__.VFS[modname] = ['.py', data, None, is_pkg]

def on_close(ev):
    on_close_callback()

def on_message(ev):
    data = ev.data
    if data[0] == 'M':
        print(repr(data))
        is_pkg = data[1] == 'P'
        mod_name, data = data[2:].split('\n', 1)
        add_module(mod_name, data, is_pkg)
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
