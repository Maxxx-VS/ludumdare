import random
from config import Config

class GameEngine:
    def __init__(self):
        self.score = 0
        self.target_pose = None
        self.completed = False
        self.lives = 5         # НОВОЕ: Запас жизней
        self.time_left = 30     # НОВОЕ: Основной таймер игры
        self.state = "PLAYING"  # НОВОЕ: Статус (PLAYING, WIN, LOSE)
        self.reset()

    def reset(self):
        """Полный сброс: обнуление очков, новая поза и сброс жизней/времени."""
        self.score = 0
        self.completed = False
        self.lives = 10         # НОВОЕ
        self.time_left = 30     # НОВОЕ
        self.state = "PLAYING"  # НОВОЕ
        self.target_pose = random.choice(Config.POSES)

    def next_pose(self):
        """Смена позы без обнуления счёта (для таймера)."""
        self.target_pose = random.choice(Config.POSES)
        self.completed = False

    def update(self, current_pose):
        # ИЗМЕНЕНО: Не засчитываем позы, если игра окончена
        if self.state != "PLAYING":
            return False

        if not self.completed and current_pose == self.target_pose:
            self.score += 10
            self.completed = True
        return current_pose == self.target_pose