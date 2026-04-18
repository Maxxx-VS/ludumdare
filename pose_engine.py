import os
import numpy as np
from ultralytics import YOLO
from config import *


class PoseDetector:
    def __init__(self):
        if not os.path.exists(MODEL_ENGINE):
            model = YOLO(MODEL_PT)
            model.export(format="engine", device=0, half=True)
        self.model = YOLO(MODEL_ENGINE, task='pose')

    def get_keypoints(self, frame):
        results = self.model(frame, imgsz=640, device=0, verbose=False, conf=0.5)
        if len(results) > 0 and results[0].keypoints is not None:
            kpts = results[0].keypoints.data.cpu().numpy()
            return kpts[0] if len(kpts) > 0 else None
        return None

    @staticmethod
    def calculate_angle(a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        ba, bc = a - b, c - b
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        return np.degrees(np.arccos(np.clip(cosine_angle, -1.0, 1.0)))

    def classify_pose(self, kpts):
        if kpts is None: return "UNKNOWN"

        # Простая проверка видимости (плечи, локти, бедра)
        for i in [5, 6, 7, 8, 11, 12]:
            if kpts[i][2] < POSE_CONFIDENCE: return "UNKNOWN"

        # Извлекаем координаты (x, y)
        points = {i: kpts[i][:2] for i in range(17)}

        # Углы
        l_elbow_angle = self.calculate_angle(points[5], points[7], points[9])
        r_elbow_angle = self.calculate_angle(points[6], points[8], points[10])

        # Логика определения (упрощенно для примера)
        if 160 < l_elbow_angle < 200 and 160 < r_elbow_angle < 200:
            if abs(points[9][1] - points[5][1]) < 50: return "T_POSE"

        if points[9][1] < points[5][1] - 30 and points[10][1] < points[6][1] - 30:
            return "HANDS_UP"

        return "UNKNOWN"