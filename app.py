import pygame
import cv2
from config import Config
from engine import PoseEngine
from game_logic import GameEngine
from visuals import Renderer
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

        # Настройка камеры
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, Config.CAM_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.CAM_HEIGHT)

        # Инициализация модулей
        self.pose_eng = PoseEngine()
        self.game = GameEngine()
        self.view = Renderer()
        self.ui_renderer = UIRenderer(self.screen)

        self.last_pose_change = pygame.time.get_ticks()
        self.game_start_time = pygame.time.get_ticks() # НОВОЕ: Точка отсчета 30-секундного таймера
        self.running = True

    def process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self.running = False
            if event.type == pygame.KEYDOWN and event.key in [pygame.K_SPACE, pygame.K_r]:
                self.game.reset()
                self.last_pose_change = pygame.time.get_ticks()
                self.game_start_time = pygame.time.get_ticks() # НОВОЕ: Сброс 30-секундного таймера

    def update_timer(self):
        # НОВОЕ: Если игра выиграна или проиграна, останавливаем таймеры
        if self.game.state != "PLAYING":
            return

        current_time = pygame.time.get_ticks()

        # НОВОЕ: Обработка главного 30-секундного таймера
        elapsed_sec = (current_time - self.game_start_time) // 1000
        self.game.time_left = max(0, 30 - elapsed_sec)

        # НОВОЕ: Проверка на победу (время вышло, а жизни еще есть)
        if self.game.time_left <= 0:
            if self.game.lives > 0:
                self.game.state = "WIN"
            return # Выходим, чтобы 5-секундный таймер уже не сработал

        # ИЗМЕНЕНО: Обработка 5-секундного таймера смены позы
        if current_time - self.last_pose_change >= 5000:
            # Если игрок не успел принять позу
            if not self.game.completed:
                self.game.lives -= 1
                if self.game.lives <= 0:
                    self.game.state = "LOSE"

            # Смена позы происходит, только если мы всё ещё играем
            if self.game.state == "PLAYING":
                self.game.next_pose()
                self.last_pose_change = current_time

    def run(self):
        while self.running:
            self.process_events()
            self.update_timer()

            ret, frame = self.cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)

            # Распознавание позы
            results = self.pose_eng.model(frame, imgsz=640, device=0, verbose=False, conf=Config.CONFIDENCE)

            kpts = None
            if results and len(results[0].keypoints.data) > 0:
                kpts = results[0].keypoints.data.cpu().numpy()[0]

            cur_pose = self.pose_eng.classify(kpts)
            is_correct = self.game.update(cur_pose)

            # Отрисовка скелета (через OpenCV)
            self.view.draw_skeleton(frame, kpts)

            # Отрисовка интерфейса и финального кадра (через Pygame)
            self.ui_renderer.draw(frame, self.game, cur_pose, is_correct)

            pygame.display.flip()
            self.clock.tick(Config.FPS)

        self.cleanup()

    def cleanup(self):
        self.cap.release()
        pygame.quit()