import os
import cv2
import numpy as np
import random
from ultralytics import YOLO
from collections import deque


# ==========================================
# 1. КОНФИГУРАЦИЯ И КОНСТАНТЫ
# ==========================================
class Config:
    MODEL_PT = "yolo11s-pose.pt"
    MODEL_ENGINE = "yolo11s-pose.engine"
    WIDTH, HEIGHT = 640, 480
    CONFIDENCE = 0.6
    FPS = 30

    # Индексы ключевых точек COCO
    POINTS = {
        'L_SHOULDER': 5, 'R_SHOULDER': 6,
        'L_ELBOW': 7, 'R_ELBOW': 8,
        'L_WRIST': 9, 'R_WRIST': 10,
        'L_HIP': 11, 'R_HIP': 12,
        'L_KNEE': 13, 'R_KNEE': 14,
        'L_ANKLE': 15, 'R_ANKLE': 16
    }

    SKELETON_LINKS = [
        (5, 6), (5, 7), (7, 9), (6, 8), (8, 10), (5, 11),
        (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)
    ]

    POSES = ["T_POSE", "HANDS_UP", "SQUAT", "LEFT_LEAN", "RIGHT_LEAN", "CROSS_ARMS"]
    POSE_NAMES_RU = {
        "T_POSE": "Руки в стороны", "HANDS_UP": "Руки вверх",
        "SQUAT": "Присед", "LEFT_LEAN": "Наклон влево",
        "RIGHT_LEAN": "Наклон вправо", "CROSS_ARMS": "Руки крестом",
        "UNKNOWN": "---"
    }


# ==========================================
# 2. МОДУЛЬ ОБРАБОТКИ ПОЗ
# ==========================================
class PoseEngine:
    def __init__(self):
        self._init_model()
        self.history = deque(maxlen=5)

    def _init_model(self):
        print("🔄 Подготовка нейросети...")
        if not os.path.exists(Config.MODEL_ENGINE):
            print("⚙️ Экспорт в TensorRT...")
            YOLO(Config.MODEL_PT).export(format="engine", device=0, half=True)
        self.model = YOLO(Config.MODEL_ENGINE, task='pose')
        print("✅ Модель загружена")

    @staticmethod
    def get_angle(a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        ba, bc = a - b, c - b
        cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        return np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))

    def classify(self, kpts):
        if kpts is None: return "UNKNOWN"

        # Проверка видимости
        req = [Config.POINTS[k] for k in ['L_SHOULDER', 'R_SHOULDER', 'L_HIP', 'R_HIP', 'L_ELBOW', 'R_ELBOW']]
        if any(kpts[i][2] < Config.CONFIDENCE for i in req): return "UNKNOWN"

        # Извлечение координат для удобства
        p = {name: kpts[idx][:2] for name, idx in Config.POINTS.items()}

        l_elbow_ang = self.get_angle(p['L_SHOULDER'], p['L_ELBOW'], p['L_WRIST'])
        r_elbow_ang = self.get_angle(p['R_SHOULDER'], p['R_ELBOW'], p['R_WRIST'])
        l_knee_ang = self.get_angle(p['L_HIP'], p['L_KNEE'], p['L_ANKLE'])
        r_knee_ang = self.get_angle(p['R_HIP'], p['R_KNEE'], p['R_ANKLE'])

        mid_sh = (p['L_SHOULDER'] + p['R_SHOULDER']) / 2
        mid_hp = (p['L_HIP'] + p['R_HIP']) / 2

        # Логика определения
        res = "UNKNOWN"
        if 160 < l_elbow_ang < 200 and 160 < r_elbow_ang < 200 and abs(p['L_WRIST'][1] - p['L_SHOULDER'][1]) < 50:
            res = "T_POSE"
        elif p['L_WRIST'][1] < p['L_SHOULDER'][1] - 30 and l_elbow_ang > 140:
            res = "HANDS_UP"
        elif l_knee_ang < 120 and r_knee_ang < 120 and mid_hp[1] > mid_sh[1] + 80:
            res = "SQUAT"
        elif abs(p['L_SHOULDER'][1] - p['R_SHOULDER'][1]) > 40:
            res = "LEFT_LEAN" if p['L_SHOULDER'][1] > p['R_SHOULDER'][1] else "RIGHT_LEAN"
        elif np.linalg.norm(p['L_WRIST'] - p['R_SHOULDER']) < 60:
            res = "CROSS_ARMS"

        self.history.append(res)
        return max(set(self.history), key=self.history.count)


# ==========================================
# 3. ИГРОВАЯ МЕХАНИКА
# ==========================================
class SignalBlock:
    def __init__(self, speed_mult):
        self.pose = random.choice(Config.POSES)
        self.x = random.randint(20, Config.WIDTH - 200)
        self.y = -50
        self.speed = 2.0 * speed_mult
        self.w, self.h = 180, 50
        self.hit = False

    def update(self):
        self.y += self.speed


class GameEngine:
    def __init__(self):
        self.state = "MENU"
        self.reset()
        self.z_start = Config.HEIGHT - 120
        self.z_end = Config.HEIGHT - 20

    def reset(self):
        self.score = 0
        self.combo = 0
        self.signal = 100.0
        self.blocks = []
        self.spawn_timer = 0
        self.speed_mult = 1.0
        self.state = "PLAYING"

    def process_logic(self, current_pose):
        if self.state != "PLAYING": return

        # Спавн
        self.spawn_timer += 1
        if self.spawn_timer >= max(20, 60 - int(self.score / 50)):
            self.blocks.append(SignalBlock(self.speed_mult))
            self.spawn_timer = 0

        # Обновление блоков
        for b in self.blocks[:]:
            b.update()
            if b.y > Config.HEIGHT:
                self.blocks.remove(b)
                self.combo = 0
                self.signal = max(0, self.signal - 15)
            elif self.z_start < b.y < self.z_end:
                if not b.hit and current_pose == b.pose:
                    b.hit = True
                    self.combo += 1
                    self.score += 100 + (self.combo * 20)
                    self.signal = min(100, self.signal + 15)
                    self.speed_mult = 1.0 + (self.score / 1500)
                    self.blocks.remove(b)

        self.signal = max(0, self.signal - 0.2)
        if self.signal <= 0: self.state = "GAME_OVER"


# ==========================================
# 4. ВИЗУАЛИЗАЦИЯ (RENDERER)
# ==========================================
class Renderer:
    @staticmethod
    def draw_skeleton(frame, kpts):
        if kpts is None: return
        for s, e in Config.SKELETON_LINKS:
            p1, p2 = kpts[s], kpts[e]
            if p1[2] > 0.5 and p2[2] > 0.5:
                cv2.line(frame, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), (0, 255, 0), 2)
        for i in range(5, 17):
            if kpts[i][2] > 0.5:
                cv2.circle(frame, (int(kpts[i][0]), int(kpts[i][1])), 4, (0, 0, 255), -1)

    @staticmethod
    def draw_ui(frame, game, current_pose):
        # Header Overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (Config.WIDTH, 60), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        # Текст
        cv2.putText(frame, f"SCORE: {game.score}", (10, 30), 2, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"COMBO: x{game.combo}", (200, 30), 2, 0.7, (0, 255, 255), 2)

        # Шкала сигнала
        bx, by, bw, bh = Config.WIDTH - 240, 20, 200, 20
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 255, 0), 1)
        cv2.rectangle(frame, (bx, by), (bx + int(bw * game.signal / 100), by + bh), (0, 255, 0), -1)

        # Зона захвата и текущая поза
        cv2.rectangle(frame, (0, game.z_start), (Config.WIDTH, game.z_end), (0, 255, 255), 2)
        name = Config.POSE_NAMES_RU.get(current_pose, "---")
        cv2.putText(frame, f"POSE: {name}", (10, Config.HEIGHT - 20), 2, 0.7, (255, 255, 255), 2)

        # Блоки
        for b in game.blocks:
            color = (0, 255, 0) if not b.hit else (255, 255, 0)
            cv2.rectangle(frame, (b.x, int(b.y)), (b.x + b.w, int(b.y) + b.h), color, 2)
            cv2.putText(frame, Config.POSE_NAMES_RU[b.pose], (b.x + 10, int(b.y) + 35), 2, 0.6, color, 2)

        if game.state == "MENU":
            cv2.putText(frame, "PRESS SPACE TO START", (180, 240), 2, 0.8, (255, 255, 255), 2)
        elif game.state == "GAME_OVER":
            cv2.putText(frame, "GAME OVER", (220, 240), 2, 1.2, (0, 0, 255), 3)


# ==========================================
# ОСНОВНОЙ ЦИКЛ
# ==========================================
def main():
    cap = cv2.VideoCapture(0)
    cap.set(3, Config.WIDTH)
    cap.set(4, Config.HEIGHT)

    pose_eng = PoseEngine()
    game = GameEngine()
    view = Renderer()

    while True:
        ret, frame = cap.read()
        if not ret: break
        frame = cv2.flip(frame, 1)

        # 1. Инференс
        results = pose_eng.model(frame, imgsz=640, device=0, verbose=False, conf=0.5)
        kpts = results[0].keypoints.data.cpu().numpy()[0] if results and results[0].keypoints is not None and len(
            results[0].keypoints.data) > 0 else None

        # 2. Логика
        cur_pose = pose_eng.classify(kpts)
        game.process_logic(cur_pose)

        # 3. Отрисовка
        view.draw_skeleton(frame, kpts)
        view.draw_ui(frame, game, cur_pose)

        cv2.imshow("SIGNAL FLOW", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            break
        elif key in [ord(' '), ord('r')]:
            game.reset()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()