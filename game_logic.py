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
        self.is_paused = False  # Флаг паузы между позами
        self.reset()

    def reset(self):
        """Полный сброс игры."""
        self.score = 0
        self.completed = False
        self.lives = 5
        self.time_left = 30
        self.state = "PLAYING"
        self.is_paused = False
        self.target_pose = random.choice(Config.POSES)

    def next_pose(self):
        """Переход к следующему заданию."""
        self.target_pose = random.choice(Config.POSES)
        self.completed = False
        self.is_paused = False  # Снимаем паузу при смене позы

    def update(self, current_pose):
        """Проверка выполнения позы."""
        if self.state != "PLAYING" or self.is_paused:
            return False

        # Если игрок принял верную позу
        if not self.completed and current_pose == self.target_pose:
            self.score += 10
            self.completed = True
            return True  # Возвращаем True только в момент первого срабатывания успеха

        return current_pose == self.target_pose