import cv2
import pygame

class PygameBridge:
    @staticmethod
    def cv_to_pygame(frame):
        """Конвертирует кадр OpenCV BGR в Surface Pygame RGB"""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Транспонируем оси, так как в CV (H, W), а в Pygame (W, H)
        return pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))