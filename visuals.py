import cv2
import numpy as np
from config import Config

class Renderer:
    def draw_skeleton(self, frame, kpts):
        if kpts is None: return

        for start, end in Config.SKELETON_LINKS:
            p1 = tuple(kpts[start][:2].astype(int))
            p2 = tuple(kpts[end][:2].astype(int))
            if kpts[start][2] > 0.5 and kpts[end][2] > 0.5:
                cv2.line(frame, p1, p2, (0, 255, 0), 2)

    def draw_ui(self, frame, game, cur_pose):
        # Текст теперь отрисовывается через Pygame в main.py
        pass
