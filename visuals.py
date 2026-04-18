import cv2
import numpy as np
from config import Config

class Renderer:
    def draw_skeleton(self, frame, kpts):
        if kpts is None:
            return

        line_thickness = 2
        circle_radius = line_thickness * 5  # 10 пикселей

        # Рисуем кости
        for start, end in Config.SKELETON_LINKS:
            if start < len(kpts) and end < len(kpts):
                if kpts[start][2] > 0.5 and kpts[end][2] > 0.5:
                    p1 = tuple(kpts[start][:2].astype(int))
                    p2 = tuple(kpts[end][:2].astype(int))
                    cv2.line(frame, p1, p2, (0, 255, 0), line_thickness)

        # Исключаем лицевые точки (индексы 0..4: нос, глаза, уши)
        face_indices = {0, 1, 2, 3, 4}

        for i, pt in enumerate(kpts):
            if i in face_indices:
                continue
            if pt[2] > 0.5:
                x, y = int(pt[0]), int(pt[1])
                if 0 <= x < frame.shape[1] and 0 <= y < frame.shape[0]:
                    cv2.circle(frame, (x, y), circle_radius, (0, 0, 255), -1)

    def draw_ui(self, frame, game, cur_pose):
        pass  # UI теперь в Pygame