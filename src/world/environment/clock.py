# Simple clock for time management
import time

class GameClock:
    def __init__(self):
        self.start_time = time.time()
        self.seconds = 0

    def update(self):
        self.seconds = int(time.time() - self.start_time)