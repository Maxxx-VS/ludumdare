import random
from collections import deque
from config import Config

class SignalBlock:
    def __init__(self, pose):
        self.target_pose = pose
        self.status = "PENDING" # PENDING, DONE, FAIL

class GameEngine:
    def __init__(self):
        self.score = 0
        self.active_signals = deque()
        self.reset()

    def reset(self):
        self.score = 0
        self.active_signals.clear()
        self.spawn_signal()

    def spawn_signal(self):
        new_pose = random.choice(Config.POSES)
        self.active_signals.append(SignalBlock(new_pose))

    def process_logic(self, current_pose):
        if not self.active_signals:
            self.spawn_signal()
            return

        target = self.active_signals[0]
        if current_pose == target.target_pose:
            self.score += 10
            self.active_signals.popleft()
            self.spawn_signal()