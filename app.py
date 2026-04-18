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

        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, Config.CAM_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.CAM_HEIGHT)

        self.pose_eng = PoseEngine()
        self.game = GameEngine()
        self.view = Renderer()
        self.ui_renderer = UIRenderer(self.screen)

        self.last_pose_change = pygame.time.get_ticks()
        self.game_start_time = pygame.time.get_ticks()
        self.running = True

    def process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self.running = False
            if event.type == pygame.KEYDOWN and event.key in [pygame.K_SPACE, pygame.K_r]:
                self.game.reset()
                self.last_pose_change = pygame.time.get_ticks()
                self.game_start_time = pygame.time.get_ticks()

    def update_timer(self):
        if self.game.state != "PLAYING":
            return

        current_time = pygame.time.get_ticks()

        # Главный таймер игры (30 сек)
        elapsed_sec = (current_time - self.game_start_time) // 1000
        self.game.time_left = max(0, 30 - elapsed_sec)

        if self.game.time_left <= 0:
            if self.game.lives > 0:
                self.game.state = "WIN"
            return

        # ИЗМЕНЕНО: Таймер смены позы сокращен до 3000мс (3 секунды)
        if current_time - self.last_pose_change >= 3000:
            # Если время вышло и поза не была принята
            if not self.game.completed:
                self.game.lives -= 1
                if self.game.lives <= 0:
                    self.game.state = "LOSE"

            # Смена позы по истечении времени
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

            results = self.pose_eng.model(frame, imgsz=640, device=0, verbose=False, conf=Config.CONFIDENCE)

            kpts = None
            if results and len(results[0].keypoints.data) > 0:
                kpts = results[0].keypoints.data.cpu().numpy()[0]

            cur_pose = self.pose_eng.classify(kpts)

            # ИЗМЕНЕНО: Логика мгновенного успеха
            is_correct = self.game.update(cur_pose)

            # Если игрок только что верно выполнил позу
            if is_correct and self.game.completed:
                # Добавляем жизнь (максимум 10, так как в UI отрисовывается 10 делений)
                self.game.lives = min(self.game.lives + 1, 10)
                # Сразу переключаем на следующую позу
                self.game.next_pose()
                # Сбрасываем 3-секундный таймер
                self.last_pose_change = pygame.time.get_ticks()

            self.view.draw_skeleton(frame, kpts)
            self.ui_renderer.draw(frame, self.game, cur_pose, is_correct)

            pygame.display.flip()
            self.clock.tick(Config.FPS)

        self.cleanup()

    def cleanup(self):
        self.cap.release()
        pygame.quit()