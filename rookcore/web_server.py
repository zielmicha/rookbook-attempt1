import asyncio, http, os, importlib.util, zipfile, io, glob
from . import async_tools, rpc_session

try:
    # TODO: we should have js stub for that
    import websockets
except ImportError:
    pass

def get_static(content_type, path):
    with open(path, 'rb') as f:
        return http.HTTPStatus.OK, [('content-type', content_type)], f.read()

pyodide_file_map = {
    '/pyodide_dev.js': 'text/javascript',
    '/pyodide.asm.data.js': 'text/javascript',
    '/pyodide.asm.js': 'text/javascript',
    '/packages.json': 'text/javascript',
    '/pyodide.asm.wasm': 'application/wasm',
    '/pyodide.asm.data': 'application/octet-stream',
}

class WebServer:
    def __init__(self, handler):
        self.handler = handler

    async def process_request(self, path, request_headers):
        path = path.split('?')[0]
        base_dir = os.path.dirname(__file__)

        if path == "/":
            return get_static('text/html', os.path.join(base_dir, 'index.html'))

        if path in pyodide_file_map:
            return get_static(pyodide_file_map[path], os.path.join(base_dir, '../pyodide/build' + path))

        if path in ("/user-code.zip", ):
            return http.HTTPStatus.OK, [('content-type', 'application/zip')], self.handler.make_user_code_zip()

        if path != "/websocket":
            return http.HTTPStatus.NOT_FOUND, [], b'not found'

    async def handle_websocket(self, websocket, path):
        if path == '/websocket':
            await self.handler.run(websocket)

    def main(self, host, port):
        start_server = websockets.serve(
            self.handle_websocket, host, port, process_request=self.process_request,
            origins=['http://%s:%d' % (host, port), 'https://%s:%d' % (host, port)] # type: ignore
        )

        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

def get_module_data(name):
    spec = importlib.util.find_spec(name)
    if not spec: raise ImportError('no such module %r' % name)
    filename = spec.origin
    if not filename: raise ImportError('module %r has no associated file' % name)

    is_pkg = filename.endswith('/__init__.py')
    rel_filename = name.replace('.', '/')
    if is_pkg:
        rel_filename += '/__init__.py'
    else:
        rel_filename += '.py'

    return rel_filename, filename

class Handler:
    def __init__(self, websocket):
        self.websocket = websocket

    @classmethod
    def make_user_code_zip(self):
        out = io.BytesIO()
        z = zipfile.ZipFile(out, 'w')

        for mod_name in self.get_user_code():
            if mod_name.endswith('.*'):
                arcname, filename = get_module_data(mod_name[:-2])
                if not filename.endswith('/__init__.py'):
                    raise Exception('module wildcard %s doesn\'t match anything' % mod_name)


                base_filename = arcname.rsplit('/', 1)[0]
                base_arcname = arcname.rsplit('/', 1)[0]

                modules = []
                for name in os.listdir(base_filename):
                    if name.endswith('.py'):
                        modules.append((base_arcname + '/' + name, base_filename + '/' + name))
            else:
                modules = [get_module_data(mod_name)]

            for arcname, filename in modules:
                with open(filename, 'r') as f: data = f.read()
                z.writestr(arcname, data)

        z.writestr('main.py', self.get_main_code()) # type: ignore

        z.close()
        return out.getvalue()

    async def run_rpc(self, websocket, root_obj):
        def write(msg):
            async_tools.run_in_background(websocket.send(msg))

        session = rpc_session.RpcSession(root_object=root_obj,
                                         on_message=write)

        async for msg in websocket:
            session.message_received(memoryview(msg))
