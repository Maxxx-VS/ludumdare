import random
from config import Config

class GameEngine:
    def __init__(self):
        self.score = 0
        self.state = "SPLASH"
        self.full_reset()

    def full_reset(self):
        self.score = 0
        self.current_level_index = 0
        # Не переключать стейт, если мы находимся в системных экранах
        if self.state not in ["SPLASH", "LOADING", "MAIN_MENU", "SETTINGS", "AUTHORS"]:
            self.state = "LEVEL_TRANSITION"
        self.load_level(0)

    def load_level(self, index):
        if index >= len(Config.LEVELS):
            self.state = "WIN"
            return
        self.current_level_index = index
        self.current_level_data = Config.LEVELS[index]
        self.time_left = self.current_level_data["duration"]
        l_lives = self.current_level_data.get("lives", -1)
        if l_lives != -1: self.lives = l_lives
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