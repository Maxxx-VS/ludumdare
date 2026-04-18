import random
from config import Config

class GameEngine:
    def __init__(self):
        self.score = 0
        self.target_pose = None
        self.completed = False
        self.lives = 5
        self.time_left = 30
        self.state = "SPLASH"  # Начинаем с логотипа
        self.is_paused = False
        self.reset()

    def reset(self):
        self.score = 0
        self.completed = False
        self.lives = 5
        self.time_left = 30
        # Если игра уже шла, ресет не возвращает к логотипу
        if self.state not in ["SPLASH", "LOADING"]:
            self.state = "PLAYING"
        self.is_paused = False
        self.target_pose = random.choice(Config.POSES)

    def next_pose(self):
        self.target_pose = random.choice(Config.POSES)
        self.completed = False
        self.is_paused = False

    def update(self, current_pose):
        if self.state != "PLAYING" or self.is_paused:
            return False

        if not self.completed and current_pose == self.target_pose:
            self.score += 10
            self.completed = True
            return True
        return current_pose == self.target_pose