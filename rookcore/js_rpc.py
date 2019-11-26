from . import rpc_session
import asyncio
import js # type: ignore

js.window.eval('''window.new_websocket = function(url) {
    return new WebSocket((location.protocol == 'https:' ? 'wss://' : 'ws://') + location.host + url);
}
''')

def open_websocket(websocket_url, on_message):
    ready: asyncio.Future = asyncio.Future()

    def on_open(event):
        ready.set_result(ws)

    def on_error(event):
        ready.set_exception(Exception('failed to open WebSocket'))

    ws = js.window.new_websocket(websocket_url)
    ws.binaryType = 'arraybuffer'
    ws.onmessage = on_message
    ws.onopen = on_open
    ws.onerror = on_error

    return ready

async def start_websocket_rpc_session(websocket_url, root_object):
    def on_message(event):
        session.message_received(memoryview(event.data))

    ws = await open_websocket(websocket_url, on_message)

    def send(data):
        print('send', bytes(data))
        ws.send(data)

    session = rpc_session.RpcSession(root_object=root_object, on_message=send)
    return session
