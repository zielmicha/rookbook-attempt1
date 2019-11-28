from rookcore import web_server, async_tools, rpc
from rookcore.common import *
from rookcore.reactive import *
from rookwidget.core import *
from . import core, base_cells, sheet_editor_widget, base_widgets
from rookwidget.core import mount_root_widget
import functools, rookcore.reactive_rpc

class ServerIface(metaclass=rpc.RpcMeta):
    @rpc.rpcmethod(id=1)
    def get_sheet(self) -> core.Sheet: pass

class MyHandler(web_server.Handler, ServerIface):
    async def run(self, websocket):
        await self.run_rpc(websocket, root_obj=self)

    @classmethod
    def get_user_code(self):
        return [
            'rookcore.*', 'rookwidget.*', 'rookbook.*']

    @classmethod
    def get_main_code(self):
        return 'import rookbook.server; rookbook.server.client_run()'

    def __init__(self, root_dir):
        self.book = core.Book(
            cell_types=base_cells.cell_types, root_dir=root_dir)

        scope_obs = Observer(self.book.scope.require_all_values)

        o = Observer(reactive(lambda: dict(self.book.scope.cells)))
        print(dict(self.book.scope.cells))
        stabilise()
        print(dict(self.book.scope.cells))

    async def get_sheet(self):
        return self.book.sheets['default'].value

def client_run():
    from rookcore import js_asyncio, js_rpc

    async def rpc_main():
        session = await js_rpc.start_websocket_rpc_session('/websocket', root_object=None)
        iface = session.remote_root_object.as_proxy(ServerIface)

        sheet = await iface.get_sheet()

        w = await sheet_editor_widget.make_editor_widget(base_widgets.cell_widget_types, sheet)
        mount_root_widget(w)
        stabilise()

    async_tools.run_in_background(rpc_main())

if __name__ == '__main__':
    import sys
    web_server.WebServer(MyHandler(sys.argv[1])).main('localhost', 4001)
