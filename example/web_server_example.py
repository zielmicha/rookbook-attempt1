from rookcore import web_server

class MyHandler(web_server.Handler):
    async def run(self):
        await self.exec_in_browser('print("hello 1")')
        await self.exec_in_browser('import example.web_server_client; example.web_server_client.client_run()')

    @classmethod
    def get_user_code(self):
        return [
                'rookcore', 'rookcore.record', 'rookcore.reactive', 'rookcore.common',
                'example', 'example.web_server_client']

    @classmethod
    def get_main_code(self):
        return 'import example.web_server_client; example.web_server_client.client_run()'

if __name__ == '__main__':
    web_server.WebServer(MyHandler).main('localhost', 4000)
