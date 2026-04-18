import pygame
import cv2
import numpy as np
from pose_engine import PoseDetector
from game_logic import GameEngine
from config import *


class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Signal Flow: Pygame Edition")

        self.cap = cv2.VideoCapture(0)
        self.detector = PoseDetector()
        self.game = GameEngine()
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 24)

    def cvframe_to_pygame(self, frame):
        """Конвертирует BGR кадр OpenCV в Pygame Surface"""
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.rot90(frame)  # Зависит от ориентации камеры
        frame = pygame.surfarray.make_surface(cv2.flip(frame, 0))
        return frame

    def draw_ui(self):
        # Очки
        score_txt = self.font.render(f"Score: {self.game.score} | Combo: {self.game.combo}", True, (255, 255, 255))
        self.screen.blit(score_txt, (20, 20))

        # Полоска сигнала
        pygame.draw.rect(self.screen, (255, 0, 0), (WIDTH - 120, 20, 100, 20), 2)
        pygame.draw.rect(self.screen, (0, 255, 0), (WIDTH - 120, 20, self.game.signal, 20))

        # Игровые блоки
        for b in self.game.blocks:
            rect = pygame.Rect(b.x, b.y, 180, 40)
            pygame.draw.rect(self.screen, (0, 255, 255), rect, 2, border_radius=5)
            name_txt = self.font.render(POSE_NAMES_RU.get(b.pose, "???"), True, (255, 255, 0))
            self.screen.blit(name_txt, (b.x + 10, b.y + 5))

    def run(self):
        running = True
        spawn_event = pygame.USEREVENT + 1
        pygame.time.set_timer(spawn_event, 2000)

        while running:
            ret, frame = self.cap.read()
            if not ret: break
            frame = cv2.flip(frame, 1)

            # 1. Обработка событий
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE: self.game.state = "PLAYING"
                if event.type == spawn_event and self.game.state == "PLAYING":
                    self.game.spawn_block()

            # 2. Детекция и логика
            kpts = self.detector.get_keypoints(frame)
            current_pose = self.detector.classify_pose(kpts)
            self.game.update(current_pose)

            # 3. Визуализация
            # Сначала рисуем видеопоток
            bg_surface = self.cvframe_to_pygame(frame)
            self.screen.blit(bg_surface, (0, 0))

            # Затем интерфейс поверх видео
            self.draw_ui()

            pygame.display.flip()
            self.clock.tick(30)

        self.cap.release()
        pygame.quit()


if __name__ == "__main__":
    App().run()