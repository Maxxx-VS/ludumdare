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
        # Отрисовка текста, очков и текущей позы
        cv2.putText(frame, f"Score: {game.score}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        status_color = (0, 255, 0) if cur_pose != "UNKNOWN" else (0, 0, 255)
        cv2.putText(frame, f"Pose: {Config.POSE_NAMES_RU.get(cur_pose)}", (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)