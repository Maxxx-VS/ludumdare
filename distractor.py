import pygame
import os
from PIL import Image, ImageSequence
from config import Config


class WalkerDistractor:
    def __init__(self):
        self.frames = self._load_gif(Config.WALKER_GIF_PATH)
        self.active = False
        self.x = 0
        self.y = 0
        self.speed = 10  # Скорость прохождения дистрактора
        self.last_trigger_time = pygame.time.get_ticks()
        self.last_update_time = pygame.time.get_ticks()
        self.gif_fps = 15

    def _load_gif(self, path):
        if not os.path.exists(path):
            return []
        frames = []
        try:
            pil_image = Image.open(path)
            for frame in ImageSequence.Iterator(pil_image):
                frame_rgba = frame.convert('RGBA')
                data = frame_rgba.tobytes()
                size = frame_rgba.size
                pygame_surface = pygame.image.fromstring(data, size, 'RGBA')
                frames.append(pygame_surface)
        except Exception as e:
            print(f"[DEBUG] Ошибка загрузки дистрактора: {e}")
        return frames

    def reset(self, current_time):
        """Сбрасывает таймер дистрактора и скрывает его."""
        self.active = False
        self.last_trigger_time = current_time
        self.last_update_time = current_time

    def update(self, current_time, target_rect, is_paused):
        """Обновляет состояние, таймер и позицию дистрактора."""
        if is_paused:
            # Сдвигаем таймер, чтобы во время показа галочки/крестика отсчет не шел
            if not self.active:
                self.last_trigger_time += (current_time - self.last_update_time)
        else:
            if not self.active:
                # Проверяем, пришло ли время выпускать дистрактор
                if current_time - self.last_trigger_time >= Config.DISTRACT_PHASE:
                    self.active = True
                    self.last_trigger_time = current_time
                    if target_rect:
                        # Начинаем движение слева, за пределами картинки позы
                        self.x = target_rect.left - 150
                        self.y = target_rect.centery
            else:
                self.x += self.speed
                # Если ушел достаточно далеко вправо, деактивируем
                if target_rect and self.x > target_rect.right + 150:
                    self.active = False
                    self.last_trigger_time = current_time

        self.last_update_time = current_time

    def draw(self, screen, current_time):
        """Отрисовывает дистрактора поверх переданного экрана."""
        if self.active and self.frames:
            frame_idx = (current_time // (1000 // self.gif_fps)) % len(self.frames)
            current_frame = self.frames[frame_idx]
            rect = current_frame.get_rect(center=(int(self.x), int(self.y)))
            screen.blit(current_frame, rect)