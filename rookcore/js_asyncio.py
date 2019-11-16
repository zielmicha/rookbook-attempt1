import contextvars, functools, heapq, asyncio.events, traceback, typing
import js # type: ignore

def unix_time():
    return js.window.performance.now() / 1000.0

class JsLoop(asyncio.events.AbstractEventLoop):
    def __init__(self):
        self.timers_queue = []
        self.current_time = unix_time()
        self._task_factory = None
        self._debug = False

    def call_soon_threadsafe(self, callback, *args, context=None):
        self.call_later(0, callback, *args, context=context)

    def call_at(self, when, callback, *args, context=None):
        if context:
            callback = functools.partial(context.run, callback)
        else:
            callback = functools.partial(callback)

        js.window._asyncio_set_timeout(max(0, when - self.current_time), when)
        handle = asyncio.TimerHandle(when, callback=callback, args=args, loop=self) # type: ignore
        heapq.heappush(self.timers_queue, handle)
        return handle

    def call_later(self, by, callback, *args, context=None):
        return self.call_at(self.current_time + by, callback, *args, context=context)

    def _timer_handle_cancelled(self, handle):
        pass

    def _timeout_callback(self, new_time):
        self.enter_from_js()

        while self.timers_queue:
            handle = self.timers_queue[0]

            if handle.when() <= new_time: # this is `new_time`, not `self.current_time`
                heapq.heappop(self.timers_queue)
                if not handle._cancelled:
                    handle._run()
            else:
                break

    def enter_from_js(self):
        self.current_time = unix_time()

    def time(self):
        return self.current_time

    def create_future(self):
        return asyncio.Future(loop=self)

    def create_task(self, coro):
        if self._task_factory is None:
            task = asyncio.Task(coro, loop=self)
        else:
            task = self._task_factory(self, coro)
        return task

    def set_task_factory(self, factory):
        self._task_factory = factory

    def get_task_factory(self):
        """Return a task factory, or None if the default one is in use."""
        return self._task_factory

    def get_debug(self):
        return self._debug

    def set_debug(self, enabled):
        self._debug = enabled

    def call_exception_handler(self, context):
        traceback.print_exc()

    call_soon = call_soon_threadsafe

js_loop = JsLoop() # type: ignore

js.window._asyncio_timeout_callback = js_loop._timeout_callback

js.window.eval('''
window._asyncio_set_timeout = function(delta, new_time) {
    setTimeout(function() { window._asyncio_timeout_callback(new_time); }, delta * 1000);
}
''')

asyncio.set_event_loop(js_loop)
