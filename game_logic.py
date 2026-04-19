import random
import json
import os
from config import Config


class GameEngine:
    def __init__(self):
        self.score = 0
        self.state = "SPLASH"
        self.current_difficulty = "EASY"
        self.hard_unlocked = False

        self.load_save_data()
        self.full_reset()

    def load_save_data(self):
        """Загрузка прогресса из файла"""
        if os.path.exists(Config.SAVE_FILE):
            try:
                with open(Config.SAVE_FILE, "r") as f:
                    data = json.load(f)
                    self.hard_unlocked = data.get("hard_unlocked", False)
            except Exception as e:
                print(f"Ошибка чтения сохранения: {e}")
                self.hard_unlocked = False
        else:
            self.hard_unlocked = False

    def save_data(self):
        """Сохранение прогресса в файл"""
        try:
            with open(Config.SAVE_FILE, "w") as f:
                json.dump({"hard_unlocked": self.hard_unlocked}, f)
        except Exception as e:
            print(f"Ошибка записи сохранения: {e}")

    def set_difficulty(self, diff_name):
        self.current_difficulty = diff_name

    def full_reset(self):
        self.score = 0
        self.current_level_index = 0
        # Не переключать стейт, если мы находимся в системных экранах
        if self.state not in ["SPLASH", "LOADING", "MAIN_MENU", "DIFFICULTY_MENU", "SETTINGS", "AUTHORS"]:
            self.state = "LEVEL_TRANSITION"
        self.load_level(0)

    def load_level(self, index):
        levels = Config.DIFFICULTIES[self.current_difficulty]

        if index >= len(levels):
            self.state = "WIN"
            # Если прошли Normal, разблокируем Hard
            if self.current_difficulty == "NORMAL" and not self.hard_unlocked:
                self.hard_unlocked = True
                self.save_data()
            return

        self.current_level_index = index
        self.current_level_data = levels[index]
        self.time_left = self.current_level_data["duration"]

        l_lives = self.current_level_data.get("lives", -1)
        if l_lives != -1:
            self.lives = l_lives

        self.next_pose()

    def next_pose(self):
        self.target_pose = random.choice(self.current_level_data["pose_pool"])
        self.completed = False
        self.is_paused = False

    def update(self, current_pose):
        if self.state != "PLAYING" or self.is_paused: return False
        if not self.completed and current_pose == self.target_pose:
            self.score += 10
            self.completed = True
            return True
        return current_pose == self.target_pose