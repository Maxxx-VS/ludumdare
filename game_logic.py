import random
import pygame
from config import Config


class GameEngine:
    def __init__(self):
        self.score = 0
        self.state = "SPLASH"
        self.difficulty = "EASY"
        self.hard_unlocked = False
        self.volume = Config.DEFAULT_VOLUME
        self.full_reset()
        self.last_result_type = None  # Может быть "SUCCESS" или "ERROR"
        self.full_reset()

    def play_music(self, index):
        """Запускает музыку, соответствующую индексу внутреннего уровня."""
        if not pygame.mixer.get_init():
            return

        track_path = Config.MUSIC_PATHS.get(index)
        if track_path:
            try:
                pygame.mixer.music.load(track_path)
                pygame.mixer.music.set_volume(self.volume)
                pygame.mixer.music.play(-1)  # Цикличное воспроизведение
            except Exception as e:
                print(f"Ошибка воспроизведения музыки: {e}")

    def set_volume(self, value):
        """Устанавливает громкость музыки (от 0.0 до 1.0)."""
        self.volume = max(0.0, min(1.0, value))
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(self.volume)

    def stop_music(self):
        """Останавливает текущую музыку."""
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()

    def full_reset(self):
        self.score = 0
        self.current_level_index = 0
        # Не переключать стейт, если мы находимся в системных экранах
        if self.state not in ["SPLASH", "LOADING", "MAIN_MENU", "DIFFICULTY_MENU", "SETTINGS", "AUTHORS"]:
            self.state = "LEVEL_TRANSITION"
        self.load_level(0)

    def load_level(self, index):
        levels_for_diff = Config.DIFFICULTIES[self.difficulty]

        if index >= len(levels_for_diff):
            self.state = "WIN"
            self.stop_music()
            if self.difficulty == "NORMAL":
                self.hard_unlocked = True
            return

        self.current_level_index = index
        self.current_level_data = levels_for_diff[index]
        self.time_left = self.current_level_data["duration"]
        l_lives = self.current_level_data.get("lives", -1)
        if l_lives != -1: self.lives = l_lives

        # --- ЗАЩИТА АВТОЗАПУСКА ---
        if self.state not in ["SPLASH", "LOADING", "MAIN_MENU", "DIFFICULTY_MENU", "SETTINGS", "AUTHORS"]:
            self.play_music(index)

        self.next_pose()

        # В методе next_pose сбрасываем тип результата
        def next_pose(self):
            self.target_pose = random.choice(self.current_level_data["pose_pool"])
            self.completed = False
            self.is_paused = False
            self.last_result_type = None

    def update(self, current_pose):
        if self.state != "PLAYING" or self.is_paused: return False
        if not self.completed and current_pose == self.target_pose:
            self.score += 10
            self.completed = True
            return True
        return current_pose == self.target_pose