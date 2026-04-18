import cv2
from config import Config

class Renderer:
    def draw_skeleton(self, frame, kpts):
        if kpts is None: return
        for start, end in Config.SKELETON_LINKS:
            if start < len(kpts) and end < len(kpts):
                if kpts[start][2] > 0.5 and kpts[end][2] > 0.5:
                    p1 = tuple(kpts[start][:2].astype(int))
                    p2 = tuple(kpts[end][:2].astype(int))
                    cv2.line(frame, p1, p2, (0, 255, 0), 2)
        for i, pt in enumerate(kpts):
            if i > 4 and pt[2] > 0.5: # Пропуск лица
                cv2.circle(frame, (int(pt[0]), int(pt[1])), 5, (0, 0, 255), -1)