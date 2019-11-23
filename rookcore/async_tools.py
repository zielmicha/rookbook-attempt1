import asyncio, functools, traceback

class RunOnlyOne:
    def __init__(self):
        self._waiting_call = None

    def run(self, call):
        if self._waiting_call is None:
            run_in_background(self._run(call))
        else:
            self._waiting_call = call

    async def _run(self, call):
        await call()
        if self._waiting_call is not None:
            next_call = self._waiting_call
            self._waiting_call = None
            self.run(next_call)

def run_in_background(task):
    async def f():
        try:
            await task
        except Exception:
            traceback.print_exc()

    asyncio.ensure_future(f())
