import random
from config import Config

class GameEngine:
    def __init__(self):
        self.score = 0
        self.target_pose = None
        self.completed = False
        self.reset()

    def reset(self):
        self.score = 0
        self.completed = False
        self.target_pose = random.choice(Config.POSES)

    def update(self, current_pose):
        """
        Обновляет состояние игры.
        Возвращает True, если текущая поза совпадает с целевой.
        Начисляет очки только один раз при первом совпадении.
        """
        if not self.completed and current_pose == self.target_pose:
            self.score += 10
            self.completed = True
        return current_pose == self.target_pose