import pygame
import cv2
import threading
import os
from config import Config
from game_logic import GameEngine
from ui import UIRenderer


class Application:
    def __init__(self):
        print("\n[DEBUG] === ЗАПУСК ИГРЫ ===")
        print("[DEBUG] Инициализация Pygame...")
        pygame.init()

        # --- ЯВНАЯ ИНИЦИАЛИЗАЦИЯ ЗВУКА С ДЕБАГОМ ---
        try:
            print("[DEBUG] Инициализация микшера...")
            pygame.mixer.init()
            print("[DEBUG] Микшер успешно инициализирован.")

            # --- ТЕСТОВЫЙ ЗАПУСК МУЗЫКИ СО СТАРТА ---
            test_track = Config.MUSIC_PATHS.get(0)
            print(f"[DEBUG] Относительный путь из конфига: {test_track}")

            if test_track:
                # Получаем полный абсолютный путь к файлу
                abs_path = os.path.abspath(test_track)
                print(f"[DEBUG] Абсолютный путь к файлу: {abs_path}")

                # Проверяем, существует ли файл физически
                if os.path.exists(abs_path):
                    print("[DEBUG] Файл НАЙДЕН на диске. Загружаем...")
                    pygame.mixer.music.load(abs_path)  # Грузим по абсолютному пути
                    print("[DEBUG] Музыка загружена. Включаем воспроизведение...")
                    pygame.mixer.music.play(-1)
                    print("[DEBUG] Команда play(-1) успешно отправлена микшеру.")
                else:
                    print("[DEBUG] ОШИБКА: Файл НЕ СУЩЕСТВУЕТ по этому пути!")
            else:
                print("[DEBUG] ОШИБКА: Трек под индексом 0 не найден в Config!")
            # ----------------------------------------

        except Exception as e:
            print(f"[DEBUG] КРИТИЧЕСКАЯ ОШИБКА АУДИО: {e}")
        # ---------------------------------
        print("[DEBUG] === ИНИЦИАЛИЗАЦИЯ ОКНА ===\n")

        self.screen = pygame.display.set_mode(
            (Config.WIN_WIDTH, Config.WIN_HEIGHT),
            pygame.FULLSCREEN | pygame.DOUBLEBUF
        )
        pygame.display.set_caption("SIGNAL FLOW")
        self.clock = pygame.time.Clock()

        self.game = GameEngine()
        self.ui_renderer = UIRenderer(self.screen)

        self.pose_eng = None
        self.cap = None
        self.view = None

        self.start_ticks = pygame.time.get_ticks()
        self.last_pose_change = 0
        self.level_start_ticks = 0
        self.transition_start_ticks = 0
        self.success_time = 0
        self.running = True

        self.cv_loading_thread = None
        self.cv_initialized = False

        # Настройки меню
        self.menu_index = 0
        self.menu_rects = []
        self.back_rect = None

    def init_cv_task(self):
        try:
            from engine import PoseEngine
            from visuals import Renderer
            temp_pose_eng = PoseEngine()
            temp_view = Renderer()
            temp_cap = cv2.VideoCapture(0)
            temp_cap.set(cv2.CAP_PROP_FRAME_WIDTH, Config.CAM_WIDTH)
            temp_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.CAM_HEIGHT)

            self.pose_eng = temp_pose_eng
            self.view = temp_view
            self.cap = temp_cap
            self.cv_initialized = True
        except Exception as e:
            print(f"Ошибка загрузки: {e}")

    def update_timer(self):
        current_time = pygame.time.get_ticks()

        if self.game.state == "SPLASH":
            if current_time - self.start_ticks >= 2000:
                self.game.state = "MAIN_MENU"
            return

        if self.game.state == "LOADING":
            if self.cv_loading_thread is None:
                self.cv_loading_thread = threading.Thread(target=self.init_cv_task)
                self.cv_loading_thread.start()
            if self.cv_initialized:
                self.game.state = "LEVEL_TRANSITION"
                self.transition_start_ticks = current_time
                # --- ЗАПУСК МУЗЫКИ ПОСЛЕ ЗАГРУЗКИ ---
                self.game.play_music(self.game.current_level_index)
            return

        if self.game.state == "LEVEL_TRANSITION":
            if current_time - self.transition_start_ticks >= 3000:
                self.game.state = "PLAYING"
                self.level_start_ticks = current_time
                self.last_pose_change = current_time
            return

        if self.game.state != "PLAYING": return

        elapsed_sec = (current_time - self.level_start_ticks) // 1000
        self.game.time_left = max(0, self.game.current_level_data["duration"] - elapsed_sec)

        if self.game.time_left <= 0:
            next_lvl = self.game.current_level_index + 1
            if next_lvl >= len(Config.DIFFICULTIES[self.game.difficulty]):
                self.game.state = "WIN"
                self.game.stop_music()
                if self.game.difficulty == "NORMAL":
                    self.game.hard_unlocked = True
            else:
                self.game.load_level(next_lvl)
                self.game.state = "LEVEL_TRANSITION"
                self.transition_start_ticks = current_time
            return

        pose_limit = self.game.current_level_data.get("pose_time_limit", 3000)

        if self.game.is_paused:
            if current_time - self.success_time >= 1000:
                self.game.next_pose()
                self.last_pose_change = current_time
            return

        if current_time - self.last_pose_change >= pose_limit:
            self.game.lives -= 1
            if self.game.lives <= 0:
                self.game.state = "LOSE"
                self.game.stop_music()
            if self.game.state == "PLAYING":
                self.game.next_pose()
                self.last_pose_change = current_time

    def run(self):
        while self.running:
            self.process_events()
            self.update_timer()

            mouse_pos = pygame.mouse.get_pos()

            if self.game.state in ["SPLASH", "MAIN_MENU", "DIFFICULTY_MENU", "SETTINGS", "AUTHORS", "LOADING"]:
                if self.game.state == "SPLASH":
                    self.ui_renderer.draw_splash()
                elif self.game.state == "MAIN_MENU":
                    self.menu_rects = self.ui_renderer.draw_main_menu(self.menu_index, mouse_pos)
                elif self.game.state == "DIFFICULTY_MENU":
                    self.menu_rects = self.ui_renderer.draw_difficulty_menu(self.menu_index, mouse_pos,
                                                                            self.game.hard_unlocked)
                elif self.game.state == "SETTINGS":
                    self.back_rect = self.ui_renderer.draw_settings(mouse_pos)
                elif self.game.state == "AUTHORS":
                    self.back_rect = self.ui_renderer.draw_authors(mouse_pos)
                else:
                    self.ui_renderer.draw_loading()

                pygame.display.flip()
                self.clock.tick(Config.FPS)
                continue

            if not self.cv_initialized: continue

            ret, frame = self.cap.read()
            if not ret: break
            frame = cv2.flip(frame, 1)

            cur_pose, is_correct, kpts = "UNKNOWN", False, None

            if self.game.state == "PLAYING":
                results = self.pose_eng.model(frame, imgsz=640, device=0, verbose=False, conf=Config.CONFIDENCE)
                kpts = results[0].keypoints.data.cpu().numpy()[0] if results and len(
                    results[0].keypoints.data) > 0 else None
                cur_pose = self.pose_eng.classify(kpts)
                is_correct = self.game.update(cur_pose)

                if is_correct and self.game.completed and not self.game.is_paused:
                    self.game.lives = min(self.game.lives + 1, 10)
                    self.game.is_paused = True
                    self.success_time = pygame.time.get_ticks()

            self.view.draw_skeleton(frame, kpts)
            self.ui_renderer.draw(frame, self.game, cur_pose, is_correct)

            pygame.display.flip()
            self.clock.tick(Config.FPS)
        self.cleanup()

    def _handle_difficulty_selection(self):
        # Меняем состояние НА LOADING до сброса, чтобы музыка не запускалась рано
        if self.menu_index == 0:
            self.game.difficulty = "EASY"
            self.game.state = "LOADING"
            self.game.full_reset()
        elif self.menu_index == 1:
            self.game.difficulty = "NORMAL"
            self.game.state = "LOADING"
            self.game.full_reset()
        elif self.menu_index == 2:
            if self.game.hard_unlocked:
                self.game.difficulty = "HARD"
                self.game.state = "LOADING"
                self.game.full_reset()
        elif self.menu_index == 3:
            self.game.state = "MAIN_MENU"
            self.menu_index = 0

    def process_events(self):
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                if self.game.state == "MAIN_MENU":
                    self.running = False
                else:
                    self.game.state = "MAIN_MENU"
                    self.game.stop_music()
                    self.menu_index = 0

            if self.game.state == "MAIN_MENU":
                if event.type == pygame.MOUSEMOTION:
                    for i, rect in enumerate(self.menu_rects):
                        if rect.collidepoint(mouse_pos):
                            self.menu_index = i
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, rect in enumerate(self.menu_rects):
                        if rect.collidepoint(mouse_pos):
                            self.menu_index = i
                            if self.menu_index == 0:
                                self.game.state = "DIFFICULTY_MENU"
                                self.menu_index = 0
                            elif self.menu_index == 1:
                                self.game.state = "SETTINGS"
                            elif self.menu_index == 2:
                                self.game.state = "AUTHORS"
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        self.menu_index = (self.menu_index - 1) % 3
                    elif event.key == pygame.K_DOWN:
                        self.menu_index = (self.menu_index + 1) % 3
                    elif event.key == pygame.K_RETURN:
                        if self.menu_index == 0:
                            self.game.state = "DIFFICULTY_MENU"
                            self.menu_index = 0
                        elif self.menu_index == 1:
                            self.game.state = "SETTINGS"
                        elif self.menu_index == 2:
                            self.game.state = "AUTHORS"

            elif self.game.state == "DIFFICULTY_MENU":
                if event.type == pygame.MOUSEMOTION:
                    for i, rect in enumerate(self.menu_rects):
                        if rect.collidepoint(mouse_pos):
                            self.menu_index = i
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, rect in enumerate(self.menu_rects):
                        if rect.collidepoint(mouse_pos):
                            self.menu_index = i
                            self._handle_difficulty_selection()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        self.menu_index = (self.menu_index - 1) % 4
                    elif event.key == pygame.K_DOWN:
                        self.menu_index = (self.menu_index + 1) % 4
                    elif event.key == pygame.K_RETURN:
                        self._handle_difficulty_selection()
                    elif event.key in [pygame.K_BACKSPACE, pygame.K_ESCAPE]:
                        self.game.state = "MAIN_MENU"
                        self.game.stop_music()
                        self.menu_index = 0

            elif self.game.state in ["SETTINGS", "AUTHORS"]:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.back_rect and self.back_rect.collidepoint(mouse_pos):
                        self.game.state = "MAIN_MENU"
                        self.game.stop_music()
                elif event.type == pygame.KEYDOWN and event.key in [pygame.K_RETURN, pygame.K_BACKSPACE,
                                                                    pygame.K_ESCAPE]:
                    self.game.state = "MAIN_MENU"
                    self.game.stop_music()

            if event.type == pygame.KEYDOWN and event.key in [pygame.K_SPACE, pygame.K_r]:
                if self.game.state not in ["SPLASH", "LOADING", "MAIN_MENU", "DIFFICULTY_MENU", "SETTINGS", "AUTHORS"]:
                    self.game.full_reset()
                    self.transition_start_ticks = pygame.time.get_ticks()

    def cleanup(self):
        if self.cap: self.cap.release()
        pygame.quit()