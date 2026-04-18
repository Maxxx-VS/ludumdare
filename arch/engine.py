import os
from ultralytics import YOLO
from config import Config


class PoseEngine:
    def __init__(self):
        # Выбираем .engine если есть, иначе .pt
        model_path = Config.MODEL_ENGINE if os.path.exists(Config.MODEL_ENGINE) else Config.MODEL_PT
        self.model = YOLO(model_path)

    def classify(self, kpts):
        if kpts is None:
            return "UNKNOWN"

        # Пример простейшей логики классификации (упрощенно)
        # Здесь должна быть твоя математика углов/координат
        try:
            lw, rw = kpts[9], kpts[10]  # Запястья
            ls, rs = kpts[5], kpts[6]  # Плечи

            if lw[1] < ls[1] and rw[1] < rs[1]: return "HANDS_UP"
            if abs(lw[1] - ls[1]) < 40 and abs(rw[1] - rs[1]) < 40: return "T_POSE"
            # ... и так далее для всех поз
        except:
            pass

        return "UNKNOWN"