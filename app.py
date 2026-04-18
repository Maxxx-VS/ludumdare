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
        self.running = True

    def process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self.running = False
            if event.type == pygame.KEYDOWN and event.key in [pygame.K_SPACE, pygame.K_r]:
                self.game.reset()
                self.last_pose_change = pygame.time.get_ticks()

    def update_timer(self):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_pose_change >= 5000:
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