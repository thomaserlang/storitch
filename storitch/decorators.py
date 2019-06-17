import functools

def run_on_executor(method):
    """Run a method in a new thread.
    Compatible with AsyncIO async await.

    Example:

        class Handler(base.Handler):

            async def get(self):
                data = await self.get_data()
                self.write_object(data)

            @run_on_executor
            def get_data():
                // Some database query
                return data
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        return self.application.loop.run_in_executor(
            self.application.settings['executor'],
            functools.partial(method, self, *args, **kwargs)
        )
    return wrapper