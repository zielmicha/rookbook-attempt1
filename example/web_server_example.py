from rookcore import web_server
from . import web_server_common

class MyHandler(web_server.Handler, web_server_common.ServerIface):
    async def run(self):
        await self.run_rpc(root_obj=self)

    @classmethod
    def get_user_code(self):
        return [
            'rookcore.*', 'rookwidget.*',
            'example', 'example.web_server_client', 'example.web_server_common']

    @classmethod
    def get_main_code(self):
        return 'import example.web_server_client; example.web_server_client.client_run()'

    async def welcome(self, who):
        print('hello %s' % who)
        return 'Hello, %s' % who

if __name__ == '__main__':
    web_server.WebServer(MyHandler).main('localhost', 4000)
