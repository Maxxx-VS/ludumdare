import pygame
import cv2
import threading  # НОВОЕ: для фоновой загрузки
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

        self.start_ticks = pygame.time.get_ticks()
        self.last_pose_change = 0
        self.game_start_ticks = 0
        self.success_time = 0
        self.running = True

        # Переменные для контроля потока загрузки
        self.cv_loading_thread = None
        self.cv_initialized = False

    def init_cv_task(self):
        """Задача для фонового потока: загрузка нейросети и камеры."""
        try:
            from engine import PoseEngine
            from visuals import Renderer

            # Сначала создаем движок (это самое долгое)
            temp_pose_eng = PoseEngine()
            temp_view = Renderer()

            # Затем камеру
            temp_cap = cv2.VideoCapture(0)
            temp_cap.set(cv2.CAP_PROP_FRAME_WIDTH, Config.CAM_WIDTH)
            temp_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.CAM_HEIGHT)

            # Передаем готовые объекты в основной класс
            self.pose_eng = temp_pose_eng
            self.view = temp_view
            self.cap = temp_cap
            self.cv_initialized = True
        except Exception as e:
            print(f"Ошибка при фоновой загрузке: {e}")

    def update_timer(self):
        current_time = pygame.time.get_ticks()

        # 1. Логотип (2 секунды)
        if self.game.state == "SPLASH":
            if current_time - self.start_ticks >= 2000:
                self.game.state = "LOADING"
            return

        # 2. Загрузка (анимированный GIF)
        if self.game.state == "LOADING":
            # Если поток еще не запущен — запускаем
            if self.cv_loading_thread is None:
                self.cv_loading_thread = threading.Thread(target=self.init_cv_task)
                self.cv_loading_thread.start()

            # Если поток закончил работу
            if self.cv_initialized:
                self.game.state = "PLAYING"
                self.game_start_ticks = pygame.time.get_ticks()
                self.last_pose_change = pygame.time.get_ticks()
            return

        # 3. Игровой процесс (PLAYING)
        if self.game.state != "PLAYING": return

        elapsed_sec = (current_time - self.game_start_ticks) // 1000
        self.game.time_left = max(0, 30 - elapsed_sec)

        if self.game.time_left <= 0:
            if self.game.lives > 0: self.game.state = "WIN"
            return

        if self.game.is_paused:
            if current_time - self.success_time >= 1000:
                self.game.next_pose()
                self.last_pose_change = current_time
            return

        if current_time - self.last_pose_change >= 3000:
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

            # В состояниях SPLASH и LOADING просто рисуем и крутим цикл
            if self.game.state == "SPLASH":
                self.ui_renderer.draw_splash()
                pygame.display.flip()
                self.clock.tick(Config.FPS)
                continue

            if self.game.state == "LOADING":
                self.ui_renderer.draw_loading()  # Здесь GIF будет проигрываться плавно
                pygame.display.flip()
                self.clock.tick(Config.FPS)
                continue

            # Если всё еще не инициализировано (на всякий случай)
            if not self.cv_initialized:
                continue

            # Основной цикл игры с камерой
            ret, frame = self.cap.read()
            if not ret: break
            frame = cv2.flip(frame, 1)

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
                    self.game.reset()
                    self.last_pose_change = pygame.time.get_ticks()
                    self.game_start_ticks = pygame.time.get_ticks()

    def cleanup(self):
        if self.cap: self.cap.release()
        pygame.quit()