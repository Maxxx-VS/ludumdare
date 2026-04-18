import os
import cv2
import numpy as np
import random
import time
from ultralytics import YOLO
from collections import deque

# ---------- НАСТРОЙКИ ----------
# Общее разрешение окна
SCREEN_W = 1600
SCREEN_H = 900

# Размеры игровой зоны (3/4 экрана)
GAME_W = 1200
GAME_H = 900

# Размеры боковой панели (1/4 экрана)
SIDE_W = SCREEN_W - GAME_W

MODEL_PT = "yolo11s-pose.pt"
MODEL_ENGINE = "yolo11s-pose.engine"
POSE_CONFIDENCE = 0.6
ANGLE_TOLERANCE = 20
FPS_TARGET = 30

# ---------- ЗАГРУЗКА МОДЕЛИ ----------
print("🔄 Загрузка модели...")
if not os.path.exists(MODEL_ENGINE):
    print("⚙️ Конвертация в TensorRT engine...")
    model = YOLO(MODEL_PT)
    model.export(format="engine", device=0, half=True)
model = YOLO(MODEL_ENGINE, task='pose')
print("✅ Модель готова")

# ---------- ОПРЕДЕЛЕНИЕ ПОЗ ----------
LEFT_SHOULDER, RIGHT_SHOULDER = 5, 6
LEFT_ELBOW, RIGHT_ELBOW = 7, 8
LEFT_WRIST, RIGHT_WRIST = 9, 10
LEFT_HIP, RIGHT_HIP = 11, 12
LEFT_KNEE, RIGHT_KNEE = 13, 14
LEFT_ANKLE, RIGHT_ANKLE = 15, 16

def angle_between_points(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc = a - b, c - b
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    return np.degrees(np.arccos(np.clip(cosine_angle, -1.0, 1.0)))

class PoseClassifier:
    @staticmethod
    def classify(keypoints):
        required = [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP,
                    LEFT_ELBOW, RIGHT_ELBOW, LEFT_WRIST, RIGHT_WRIST, LEFT_KNEE, RIGHT_KNEE]
        for idx in required:
            if keypoints[idx][2] < POSE_CONFIDENCE:
                return "UNKNOWN"

        ls, rs = keypoints[LEFT_SHOULDER][:2], keypoints[RIGHT_SHOULDER][:2]
        le, re = keypoints[LEFT_ELBOW][:2], keypoints[RIGHT_ELBOW][:2]
        lw, rw = keypoints[LEFT_WRIST][:2], keypoints[RIGHT_WRIST][:2]
        lh, rh = keypoints[LEFT_HIP][:2], keypoints[RIGHT_HIP][:2]
        lk, rk = keypoints[LEFT_KNEE][:2], keypoints[RIGHT_KNEE][:2]

        l_elbow_a = angle_between_points(ls, le, lw)
        r_elbow_a = angle_between_points(rs, re, rw)
        l_knee_a = angle_between_points(lh, lk, keypoints[LEFT_ANKLE][:2])
        r_knee_a = angle_between_points(rh, rk, keypoints[RIGHT_ANKLE][:2])

        mid_sh, mid_hip = (ls + rs) / 2, (lh + rh) / 2

        if 160 < l_elbow_a < 200 and 160 < r_elbow_a < 200 and abs(lw[1]-ls[1]) < 80 and abs(rw[1]-rs[1]) < 80:
            return "T_POSE"
        if lw[1] < ls[1] - 50 and rw[1] < rs[1] - 50 and l_elbow_a > 130 and r_elbow_a > 130:
            return "HANDS_UP"
        if l_knee_a < 130 and r_knee_a < 130 and mid_hip[1] > mid_sh[1] + 100:
            return "SQUAT"
        if abs(ls[1] - rs[1]) > 60:
            return "LEFT_LEAN" if ls[1] > rs[1] else "RIGHT_LEAN"
        if np.linalg.norm(lw - rs) < 80 and np.linalg.norm(rw - ls) < 80:
            return "CROSS_ARMS"
        return "UNKNOWN"

# ---------- ИГРОВЫЕ НАСТРОЙКИ ----------
POSE_LIST = ["T_POSE", "HANDS_UP", "SQUAT", "LEFT_LEAN", "RIGHT_LEAN", "CROSS_ARMS"]
POSE_NAMES_RU = {
    "T_POSE": "Руки в стороны", "HANDS_UP": "Руки вверх", "SQUAT": "Присед",
    "LEFT_LEAN": "Наклон влево", "RIGHT_LEAN": "Наклон вправо", "CROSS_ARMS": "Руки крестом"
}

class SignalBlock:
    def __init__(self, pose_type, x, y, speed):
        self.pose, self.x, self.y, self.speed = pose_type, x, y, speed
        self.width, self.height, self.hit = 220, 60, False

    def update(self): self.y += self.speed
    def draw(self, frame):
        color = (0, 255, 0) if not self.hit else (255, 255, 0)
        cv2.rectangle(frame, (self.x, int(self.y)), (self.x + self.width, int(self.y) + self.height), color, 3)
        cv2.putText(frame, POSE_NAMES_RU[self.pose], (self.x + 10, int(self.y) + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    def is_in_capture_zone(self, z_start, z_end):
        return (self.y < z_end and (self.y + self.height) > z_start)

class Game:
    def __init__(self):
        self.state = "MENU"
        self.score, self.combo, self.max_combo, self.signal_strength = 0, 0, 0, 100
        self.blocks, self.spawn_timer, self.speed_multiplier = [], 0, 1.0
        self.pose_classifier = PoseClassifier()
        self.current_pose = "UNKNOWN"
        self.capture_zone_y_start = GAME_H - 180
        self.capture_zone_y_end = GAME_H - 40
        self.pose_history = deque(maxlen=5)

    def reset(self):
        self.score, self.combo, self.max_combo, self.signal_strength = 0, 0, 0, 100
        self.blocks, self.spawn_timer, self.speed_multiplier = [], 0, 1.0
        self.pose_history.clear()
        self.state = "PLAYING"

    def update(self, keypoints):
        if keypoints is not None:
            pose = self.pose_classifier.classify(keypoints)
            self.pose_history.append(pose)
            self.current_pose = max(set(self.pose_history), key=self.pose_history.count)
        else: self.current_pose = "UNKNOWN"

        if self.state != "PLAYING": return

        self.spawn_timer += 1
        if self.spawn_timer >= max(25, 70 - int(self.score / 600)):
            p = random.choice(POSE_LIST)
            x = random.randint(50, GAME_W - 250)
            self.blocks.append(SignalBlock(p, x, -60, 3.5 * self.speed_multiplier))
            self.spawn_timer = 0

        for b in self.blocks[:]:
            b.update()
            if b.y > GAME_H:
                self.blocks.remove(b)
                self.combo, self.signal_strength = 0, max(0, self.signal_strength - 15)
            elif b.is_in_capture_zone(self.capture_zone_y_start, self.capture_zone_y_end):
                if not b.hit and self.current_pose == b.pose:
                    b.hit = True
                    self.combo += 1
                    self.max_combo = max(self.max_combo, self.combo)
                    self.score += 100 + (self.combo * 20)
                    self.signal_strength = min(100, self.signal_strength + 12)
                    self.speed_multiplier = 1.0 + (self.score / 5000)
                    self.blocks.remove(b)

        self.signal_strength = max(0, self.signal_strength - 0.15)
        if self.signal_strength <= 0: self.state = "GAME_OVER"

    def draw_ui(self, frame):
        # UI поверх игрового окна
        cv2.putText(frame, f"SCORE: {self.score}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
        cv2.putText(frame, f"COMBO: x{self.combo}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        
        # Индикатор сигнала
        cv2.rectangle(frame, (GAME_W - 320, 30), (GAME_W - 20, 60), (0, 255, 0), 2)
        cv2.rectangle(frame, (GAME_W - 320, 30), (GAME_W - 320 + int(300 * self.signal_strength / 100), 60), (0, 255, 0), -1)

        cv2.rectangle(frame, (0, self.capture_zone_y_start), (GAME_W, self.capture_zone_y_end), (0, 255, 255), 2)
        p_name = POSE_NAMES_RU.get(self.current_pose, "---")
        cv2.putText(frame, f"POSE: {p_name}", (20, GAME_H - 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        for b in self.blocks: b.draw(frame)
        if self.state == "MENU":
            cv2.putText(frame, "PRESS SPACE TO START", (GAME_W // 2 - 250, GAME_H // 2), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
        elif self.state == "GAME_OVER":
            cv2.putText(frame, "GAME OVER", (GAME_W // 2 - 150, GAME_H // 2), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 255), 4)
            cv2.putText(frame, "PRESS R TO RESTART", (GAME_W // 2 - 180, GAME_H // 2 + 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

def main():
    cap = cv2.VideoCapture(0)
    game = Game()
    skeleton_links = [(5, 6), (5, 7), (7, 9), (6, 8), (8, 10), (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)]

    while True:
        ret, raw_frame = cap.read()
        if not ret: break
        
        # 1. Подготовка игрового кадра (3/4 слева)
        game_frame = cv2.flip(raw_frame, 1)
        game_frame = cv2.resize(game_frame, (GAME_W, GAME_H))

        # 2. Детекция (только на игровом кадре)
        results = model(game_frame, imgsz=640, device=0, verbose=False, conf=0.5)
        keypoints_data = None

        if len(results) > 0 and results[0].keypoints is not None:
            kpts = results[0].keypoints.data.cpu().numpy()
            if len(kpts) > 0:
                keypoints_data = kpts[0]
                for s, e in skeleton_links:
                    pt1, pt2 = keypoints_data[s], keypoints_data[e]
                    if pt1[2] > 0.5 and pt2[2] > 0.5:
                        cv2.line(game_frame, (int(pt1[0]), int(pt1[1])), (int(pt2[0]), int(pt2[1])), (0, 255, 0), 3)
                for i in range(5, 17):
                    if keypoints_data[i][2] > 0.5:
                        cv2.circle(game_frame, (int(keypoints_data[i][0]), int(keypoints_data[i][1])), 5, (0, 0, 255), -1)

        game.update(keypoints_data)
        game.draw_ui(game_frame)

        # 3. Сборка финального полотна (1600x900)
        canvas = np.zeros((SCREEN_H, SCREEN_W, 3), dtype=np.uint8)
        
        # Левая часть: Игра
        canvas[0:GAME_H, 0:GAME_W] = game_frame
        
        # Правая часть: Сектора (Синий и Зеленый)
        # Верхний правый (Синий)
        canvas[0:SCREEN_H//2, GAME_W:SCREEN_W] = [150, 50, 0] # BGR
        # Нижний правый (Зеленый)
        canvas[SCREEN_H//2:SCREEN_H, GAME_W:SCREEN_W] = [0, 120, 0]
        
        # Разделительные линии
        cv2.line(canvas, (GAME_W, 0), (GAME_W, SCREEN_H), (255, 255, 255), 2) # Вертикальная
        cv2.line(canvas, (GAME_W, SCREEN_H//2), (SCREEN_W, SCREEN_H//2), (255, 255, 255), 2) # Горизонтальная

        cv2.imshow("SIGNAL FLOW - MULTI PANEL", canvas)
        
        key = cv2.waitKey(1) & 0xFF
        if key == 27: break
        elif key == ord(' '): game.reset()
        elif key == ord('r'): game.reset()

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
