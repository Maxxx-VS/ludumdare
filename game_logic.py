import random
from config import Config

class GameEngine:
    def __init__(self):
        self.score = 0
        self.target_pose = None
        self.completed = False
        self.reset()

    def reset(self):
        """Полный сброс: обнуление очков, новая поза."""
        self.score = 0
        self.completed = False
        self.target_pose = random.choice(Config.POSES)

    def next_pose(self):
        """Смена позы без обнуления счёта (для таймера)."""
        self.target_pose = random.choice(Config.POSES)
        self.completed = False

    def update(self, current_pose):
        if not self.completed and current_pose == self.target_pose:
            self.score += 10
            self.completed = True
        return current_pose == self.target_pose