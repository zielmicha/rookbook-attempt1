import asyncio, http, websockets, os, importlib.util

def get_static(content_type, path):
    with open(path, 'rb') as f:
        return http.HTTPStatus.OK, [('content-type', content_type)], f.read()

class WebServer:
    def __init__(self, handler_cls):
        self.handler_cls = handler_cls

    async def process_request(self, path, request_headers):
        path = path.split('?')[0]
        base_dir = os.path.dirname(__file__)

        if path == "/":
            return get_static('text/html', os.path.join(base_dir, 'index.html'))

        if path in ("/brython.js", '/brython_stdlib.js'):
            return get_static('text/html', os.path.join(base_dir, '../brython' + path))

        if path in ("/brython_client.py", ):
            return get_static('text/python', os.path.join(base_dir + path))

        if path != "/websocket":
            return http.HTTPStatus.NOT_FOUND, [], b'not found'

    async def handle_websocket(self, websocket, path):
        await self.handler_cls(websocket).run()

    def main(self, host, port):
        start_server = websockets.serve(
            self.handle_websocket, host, port, process_request=self.process_request
        )

        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

class Handler:
    def __init__(self, websocket):
        self.websocket = websocket

    def send_module_data(self, name, data, is_pkg):
        msg = 'M' + ('P' if is_pkg else 'M') + name + '\n' + data
        return self.websocket.send(msg)

    def send_module(self, name):
        spec = importlib.util.find_spec(name)
        if not spec: raise ImportError('no such module %r' % name)
        filename = spec.origin
        if not filename: raise ImportError('module %r has no associated file' % name)
        with open(filename, 'r') as f: data = f.read()
        is_pkg = filename.endswith('/__init__.py')

        return self.send_module_data(name, data, is_pkg)

    def exec_in_browser(self, code):
        return self.websocket.send('E' + code)
