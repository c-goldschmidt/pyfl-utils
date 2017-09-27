import time


class Timer(object):

    def __init__(self, print_fnc=print):
        self._last_ts = time.time()
        self._print = print_fnc

    def step(self, message, reset=True):
        time_spent = time.time() - self._last_ts
        self._print('[{:5}] {}'.format(time_spent, message))

        if reset:
            self._last_ts = time.time()

    def start(self):
        self._last_ts = time.time()
