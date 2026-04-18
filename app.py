import pygame
import cv2
import threading
from config import Config
from game_logic import GameEngine
from ui import UIRenderer

class Application:
    def __init__(self):
        pygame.init()
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

        # Таймеры
        self.start_ticks = pygame.time.get_ticks()
        self.last_pose_change = 0
        self.level_start_ticks = 0        # Время начала текущего уровня
        self.transition_start_ticks = 0   # Время начала заставки между уровнями
        self.success_time = 0
        self.running = True

        self.cv_loading_thread = None
        self.cv_initialized = False

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
            print(f"Ошибка при фоновой загрузке: {e}")

    def update_timer(self):
        current_time = pygame.time.get_ticks()

        # 1. Логотип
        if self.game.state == "SPLASH":
            if current_time - self.start_ticks >= 2000:
                self.game.state = "LOADING"
            return

        # 2. Загрузка
        if self.game.state == "LOADING":
            if self.cv_loading_thread is None:
                self.cv_loading_thread = threading.Thread(target=self.init_cv_task)
                self.cv_loading_thread.start()

            if self.cv_initialized:
                self.game.state = "LEVEL_TRANSITION"
                self.transition_start_ticks = pygame.time.get_ticks()
            return

        # 3. Переход между уровнями (пауза 3 сек)
        if self.game.state == "LEVEL_TRANSITION":
            if current_time - self.transition_start_ticks >= 3000:
                self.game.state = "PLAYING"
                self.level_start_ticks = current_time
                self.last_pose_change = current_time
            return

        # 4. Игровой процесс
        if self.game.state != "PLAYING": return

        # Таймер уровня
        elapsed_sec = (current_time - self.level_start_ticks) // 1000
        level_duration = self.game.current_level_data["duration"]
        self.game.time_left = max(0, level_duration - elapsed_sec)

        # Время вышло - победа на уровне!
        if self.game.time_left <= 0:
            if self.game.lives > 0:
                # Переключаем уровень
                next_lvl = self.game.current_level_index + 1
                if next_lvl >= len(Config.LEVELS):
                    self.game.state = "WIN" # Прошли все уровни
                else:
                    self.game.load_level(next_lvl)
                    self.game.state = "LEVEL_TRANSITION"
                    self.transition_start_ticks = pygame.time.get_ticks()
            return

        # Динамическое время на смену позы из конфига
        pose_limit = self.game.current_level_data.get("pose_time_limit", 3000)

        # Пауза после правильной позы
        if self.game.is_paused:
            if current_time - self.success_time >= 1000:
                self.game.next_pose()
                self.last_pose_change = current_time
            return

        # Штраф за пропуск позы
        if current_time - self.last_pose_change >= pose_limit:
            if not self.game.completed:
                self.game.lives -= 1
                if self.game.lives <= 0: self.game.state = "LOSE"
            if self.game.state == "PLAYING":
                self.game.next_pose()
                self.last_pose_change = current_time

    def run(self):
        while self.running:
            self.process_events()
            self.update_timer()

            if self.game.state == "SPLASH":
                self.ui_renderer.draw_splash()
                pygame.display.flip()
                self.clock.tick(Config.FPS)
                continue

            if self.game.state == "LOADING":
                self.ui_renderer.draw_loading()
                pygame.display.flip()
                self.clock.tick(Config.FPS)
                continue

            if not self.cv_initialized:
                continue

            ret, frame = self.cap.read()
            if not ret: break
            frame = cv2.flip(frame, 1)

            # Если мы в транзиции, победе или проигрыше - позы не проверяем, но рисуем интерфейс
            cur_pose = "UNKNOWN"
            is_correct = False
            kpts = None

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

    def process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self.running = False
            if event.type == pygame.KEYDOWN and event.key in [pygame.K_SPACE, pygame.K_r]:
                if self.game.state not in ["SPLASH", "LOADING"]:
                    self.game.full_reset()
                    self.transition_start_ticks = pygame.time.get_ticks()

    def cleanup(self):
        if self.cap: self.cap.release()
        pygame.quit()