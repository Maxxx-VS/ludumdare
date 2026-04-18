import pygame
import cv2
from config import Config
from engine import PoseEngine
from game_logic import GameEngine
from visuals import Renderer
from ui import UIRenderer


class Application:
    def __init__(self):
        self.success_time = 0  # НОВОЕ: время начала паузы
        self.running = True

    def update_timer(self):
        if self.game.state != "PLAYING":
            return

        current_time = pygame.time.get_ticks()

        # 1. Основной таймер (30 сек)
        elapsed_sec = (current_time - self.game_start_time) // 1000
        self.game.time_left = max(0, 30 - elapsed_sec)

        if self.game.time_left <= 0:
            if self.game.lives > 0:
                self.game.state = "WIN"
            return

        # 2. НОВОЕ: Обработка 1-секундной паузы ПОСЛЕ успеха
        if self.game.is_paused:
            if current_time - self.success_time >= 1000:
                self.game.next_pose()
                self.last_pose_change = current_time  # Сбрасываем таймер для следующей позы
            return  # Пока мы на паузе, нижний блок с 3-секундным таймером не срабатывает

        # 3. ИЗМЕНЕНО: 3-секундный таймер (проигрыш жизни)
        if current_time - self.last_pose_change >= 3000:
            if not self.game.completed:
                self.game.lives -= 1
                if self.game.lives <= 0:
                    self.game.state = "LOSE"

            if self.game.state == "PLAYING":
                self.game.next_pose()
                self.last_pose_change = current_time

    def run(self):
        while self.running:
            self.process_events()
            self.update_timer()

            ret, frame = self.cap.read()
            if not ret: break
            frame = cv2.flip(frame, 1)

            results = self.pose_eng.model(frame, imgsz=640, device=0, verbose=False, conf=Config.CONFIDENCE)
            kpts = results[0].keypoints.data.cpu().numpy()[0] if results and len(
                results[0].keypoints.data) > 0 else None

            cur_pose = self.pose_eng.classify(kpts)
            is_correct = self.game.update(cur_pose)

            # ИЗМЕНЕНО: Логика перехода в режим паузы при успехе
            if is_correct and self.game.completed and not self.game.is_paused:
                self.game.lives = min(self.game.lives + 1, 10)
                self.game.is_paused = True  # Включаем паузу
                self.success_time = pygame.time.get_ticks()  # Засекаем время начала паузы

            self.view.draw_skeleton(frame, kpts)
            self.ui_renderer.draw(frame, self.game, cur_pose, is_correct)

            pygame.display.flip()
            self.clock.tick(Config.FPS)
        self.cleanup()

    def cleanup(self):
        self.cap.release()
        pygame.quit()