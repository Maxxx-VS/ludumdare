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
        self.is_paused = False  # НОВОЕ: состояние паузы после успеха
        self.reset()

    def reset(self):
        self.score = 0
        self.completed = False
        self.lives = 5
        self.time_left = 30
        self.state = "PLAYING"
        self.is_paused = False  # Сброс паузы
        self.target_pose = random.choice(Config.POSES)

    def next_pose(self):
        self.target_pose = random.choice(Config.POSES)
        self.completed = False
        self.is_paused = False  # Выходим из паузы при смене позы

    def update(self, current_pose):
        if self.state != "PLAYING" or self.is_paused: # ИЗМЕНЕНО: Не считаем позы во время паузы
            return False

        if not self.completed and current_pose == self.target_pose:
            self.score += 10
            self.completed = True
            return True
        return current_pose == self.target_pose