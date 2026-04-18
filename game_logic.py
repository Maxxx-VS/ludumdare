import random
from config import Config


class GameEngine:
    def __init__(self):
        self.score = 0
        self.completed = False
        self.state = "SPLASH"
        self.is_paused = False

        # Переменные уровней
        self.current_level_index = 0
        self.current_level_data = None
        self.lives = 5
        self.time_left = 0
        self.target_pose = None

        self.full_reset()

    def full_reset(self):
        """Полный сброс игры (к 1 уровню)."""
        self.score = 0
        self.current_level_index = 0
        # Если игра уже идет, сразу кидаем в экран перехода к 1 уровню
        if self.state not in ["SPLASH", "LOADING"]:
            self.state = "LEVEL_TRANSITION"
        self.load_level(0)

    def load_level(self, index):
        """Загрузка конфигурации конкретного уровня."""
        if index >= len(Config.LEVELS):
            self.state = "WIN"
            return

        self.current_level_index = index
        self.current_level_data = Config.LEVELS[index]
        self.time_left = self.current_level_data["duration"]

        # Обновляем жизни, если в конфиге не стоит -1 (сохранение текущих)
        level_lives = self.current_level_data.get("lives", -1)
        if level_lives != -1:
            self.lives = level_lives

        self.completed = False
        self.is_paused = False
        self.target_pose = random.choice(self.current_level_data["pose_pool"])

    def next_pose(self):
        """Смена позы (выбирается из пула текущего уровня)."""
        self.target_pose = random.choice(self.current_level_data["pose_pool"])
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