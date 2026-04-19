import random
import pygame
from config import Config


class GameEngine:
    def __init__(self):
        self.score = 0
        self.state = "SPLASH"
        self.difficulty = "EASY"
        self.hard_unlocked = False
        self.sound_enabled = True
        self.full_reset()

        # --- Новые методы для управления музыкой ---
        def play_music(self, index):
            if not self.sound_enabled or not pygame.mixer.get_init():
                return

            # Если этапов больше чем треков, играем последний доступный
            track_index = min(index, len(Config.MUSIC_PATHS) - 1)
            track_path = Config.MUSIC_PATHS.get(track_index)

            if track_path:
                try:
                    pygame.mixer.music.load(track_path)
                    pygame.mixer.music.play(-1)  # -1 для бесконечного зацикливания трека
                except Exception as e:
                    print(f"Ошибка загрузки музыки: {e}")

        def stop_music(self):
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        # -------------------------------------------

    def load_level(self, index):
        levels_for_diff = Config.DIFFICULTIES[self.difficulty]

        if index >= len(levels_for_diff):
            self.state = "WIN"
            self.stop_music()  # Останавливаем музыку при победе
            if self.difficulty == "NORMAL":
                self.hard_unlocked = True
            return

        self.current_level_index = index
        self.current_level_data = levels_for_diff[index]
        self.time_left = self.current_level_data["duration"]
        l_lives = self.current_level_data.get("lives", -1)
        if l_lives != -1: self.lives = l_lives

        self.play_music(index)  # Запускаем музыку, соответствующую индексу этапа
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