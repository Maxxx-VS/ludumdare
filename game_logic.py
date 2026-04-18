import random
from config import Config


class GameEngine:
    def __init__(self):
        self.score = 0
        self.target_pose = None
        self.completed = False
        self.lives = 5
        self.time_left = 30
        self.state = "PLAYING"
        self.reset()

    def reset(self):
        self.score = 0
        self.completed = False
        self.lives = 5
        self.time_left = 30
        self.state = "PLAYING"
        self.target_pose = random.choice(Config.POSES)

    def next_pose(self):
        self.target_pose = random.choice(Config.POSES)
        self.completed = False

    def update(self, current_pose):
        if self.state != "PLAYING":
            return False

        # Если текущая поза совпала с целью и мы еще не пометили её как выполненную
        if not self.completed and current_pose == self.target_pose:
            self.score += 10
            self.completed = True
            return True  # Возвращаем True только в момент успеха

        return current_pose == self.target_pose