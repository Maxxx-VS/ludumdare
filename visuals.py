import cv2
import numpy as np
from config import Config

class Renderer:
    def draw_skeleton(self, frame, kpts):
        if kpts is None:
            return

        # Толщина линий скелета (как в исходном коде)
        line_thickness = 2
        # Радиус кругов = 5 * толщина линий
        circle_radius = line_thickness * 5  # 10 пикселей

        # Рисуем соединения (кости)
        for start, end in Config.SKELETON_LINKS:
            if start < len(kpts) and end < len(kpts):
                if kpts[start][2] > 0.5 and kpts[end][2] > 0.5:
                    p1 = tuple(kpts[start][:2].astype(int))
                    p2 = tuple(kpts[end][:2].astype(int))
                    cv2.line(frame, p1, p2, (0, 255, 0), line_thickness)

        # Исключаем лицевые точки (нос, глаза, уши) – индексы 0..4
        face_indices = {0, 1, 2, 3, 4}

        # Рисуем красные круги на всех узлах (суставах) с достаточной уверенностью,
        # кроме лицевых точек
        for i, pt in enumerate(kpts):
            if i in face_indices:
                continue  # пропускаем лицо
            if pt[2] > 0.5:  # confidence > 0.5
                x, y = int(pt[0]), int(pt[1])
                # Проверяем границы кадра
                if 0 <= x < frame.shape[1] and 0 <= y < frame.shape[0]:
                    cv2.circle(frame, (x, y), circle_radius, (0, 0, 255), -1)  # -1 = заливка

    def draw_ui(self, frame, game, cur_pose):
        # UI теперь рисуется через Pygame в main.py
        pass