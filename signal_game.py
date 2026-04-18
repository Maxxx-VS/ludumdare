import os
import cv2
import numpy as np
import random
import time
from ultralytics import YOLO
from collections import deque

# ---------- НАСТРОЙКИ ----------
MODEL_PT = "yolo11s-pose.pt"
MODEL_ENGINE = "yolo11s-pose.engine"
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
POSE_CONFIDENCE = 0.6
ANGLE_TOLERANCE = 20  # градусов допуска при проверке позы
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
# Индексы ключевых точек COCO
LEFT_SHOULDER, RIGHT_SHOULDER = 5, 6
LEFT_ELBOW, RIGHT_ELBOW = 7, 8
LEFT_WRIST, RIGHT_WRIST = 9, 10
LEFT_HIP, RIGHT_HIP = 11, 12
LEFT_KNEE, RIGHT_KNEE = 13, 14
LEFT_ANKLE, RIGHT_ANKLE = 15, 16

def angle_between_points(a, b, c):
    """Вычисляет угол ABC в градусах."""
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    ba = a - b
    bc = c - b
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    return np.degrees(angle)

class PoseClassifier:
    """Классификатор поз на основе углов и относительных положений."""

    @staticmethod
    def classify(keypoints):
        # Проверка видимости основных точек (от плеч и ниже)
        required = [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP,
                    LEFT_ELBOW, RIGHT_ELBOW, LEFT_WRIST, RIGHT_WRIST,
                    LEFT_KNEE, RIGHT_KNEE]
        for idx in required:
            if keypoints[idx][2] < POSE_CONFIDENCE:
                return "UNKNOWN"

        ls = keypoints[LEFT_SHOULDER][:2]
        rs = keypoints[RIGHT_SHOULDER][:2]
        le = keypoints[LEFT_ELBOW][:2]
        re = keypoints[RIGHT_ELBOW][:2]
        lw = keypoints[LEFT_WRIST][:2]
        rw = keypoints[RIGHT_WRIST][:2]
        lh = keypoints[LEFT_HIP][:2]
        rh = keypoints[RIGHT_HIP][:2]
        lk = keypoints[LEFT_KNEE][:2]
        rk = keypoints[RIGHT_KNEE][:2]

        left_elbow_angle = angle_between_points(ls, le, lw)
        right_elbow_angle = angle_between_points(rs, re, rw)
        left_knee_angle = angle_between_points(lh, lk, keypoints[LEFT_ANKLE][:2])
        right_knee_angle = angle_between_points(rh, rk, keypoints[RIGHT_ANKLE][:2])

        mid_shoulder = (ls + rs) / 2
        mid_hip = (lh + rh) / 2

        if (160 < left_elbow_angle < 200 and 160 < right_elbow_angle < 200 and
                abs(lw[1] - ls[1]) < 50 and abs(rw[1] - rs[1]) < 50):
            return "T_POSE"

        if (lw[1] < ls[1] - 30 and rw[1] < rs[1] - 30 and
                left_elbow_angle > 140 and right_elbow_angle > 140):
            return "HANDS_UP"

        if (left_knee_angle < 120 and right_knee_angle < 120 and
                mid_hip[1] > mid_shoulder[1] + 80):
            return "SQUAT"

        shoulder_slope = abs(ls[1] - rs[1])
        if shoulder_slope > 40:
            return "LEFT_LEAN" if ls[1] > rs[1] else "RIGHT_LEAN"

        dist_lw_to_rs = np.linalg.norm(lw - rs)
        dist_rw_to_ls = np.linalg.norm(rw - ls)
        if dist_lw_to_rs < 60 and dist_rw_to_ls < 60:
            return "CROSS_ARMS"

        return "UNKNOWN"

# ---------- ИГРОВЫЕ НАСТРОЙКИ ----------
POSE_LIST = ["T_POSE", "HANDS_UP", "SQUAT", "LEFT_LEAN", "RIGHT_LEAN", "CROSS_ARMS"]
POSE_NAMES_RU = {
    "T_POSE": "Руки в стороны",
    "HANDS_UP": "Руки вверх",
    "SQUAT": "Присед",
    "LEFT_LEAN": "Наклон влево",
    "RIGHT_LEAN": "Наклон вправо",
    "CROSS_ARMS": "Руки крестом"
}

class SignalBlock:
    def __init__(self, pose_type, x, y, speed):
        self.pose = pose_type
        self.x = x
        self.y = y
        self.speed = speed
        self.width = 180
        self.height = 50
        self.hit = False

    def update(self):
        self.y += self.speed

    def draw(self, frame):
        color = (0, 255, 0) if not self.hit else (255, 255, 0)
        cv2.rectangle(frame, (self.x, int(self.y)), (self.x + self.width, int(self.y) + self.height), color, 2)
        cv2.putText(frame, POSE_NAMES_RU[self.pose], (self.x + 10, int(self.y) + 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    def is_in_capture_zone(self, z_start, z_end):
        return (self.y < z_end and (self.y + self.height) > z_start)

class Game:
    def __init__(self):
        self.state = "MENU"
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.signal_strength = 0
        self.blocks = []
        self.spawn_timer = 0
        self.speed_multiplier = 1.0
        self.pose_classifier = PoseClassifier()
        self.current_pose = "UNKNOWN"
        self.capture_zone_y_start = CAMERA_HEIGHT - 120
        self.capture_zone_y_end = CAMERA_HEIGHT - 20
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
        else:
            self.current_pose = "UNKNOWN"

        if self.state != "PLAYING": return

        self.spawn_timer += 1
        if self.spawn_timer >= max(20, 60 - int(self.score / 50)):
            p = random.choice(POSE_LIST)
            x = random.randint(20, CAMERA_WIDTH - 200)
            self.blocks.append(SignalBlock(p, x, -50, 2.0 * self.speed_multiplier))
            self.spawn_timer = 0

        for b in self.blocks[:]:
            b.update()
            if b.y > CAMERA_HEIGHT:
                self.blocks.remove(b)
                self.combo, self.signal_strength = 0, max(0, self.signal_strength - 15)
            elif b.is_in_capture_zone(self.capture_zone_y_start, self.capture_zone_y_end):
                if not b.hit and self.current_pose == b.pose:
                    b.hit = True
                    self.combo += 1
                    self.max_combo = max(self.max_combo, self.combo)
                    self.score += 100 + (self.combo * 20)
                    self.signal_strength = min(100, self.signal_strength + 15)
                    self.speed_multiplier = 1.0 + (self.score / 1500)
                    self.blocks.remove(b)

        self.signal_strength = max(0, self.signal_strength - 0.2)
        if self.signal_strength <= 0: self.state = "GAME_OVER"

    def draw_ui(self, frame):
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 60), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        cv2.putText(frame, f"SCORE: {self.score}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"COMBO: x{self.combo}", (200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Сигнал
        bar_x, bar_y, bar_w, bar_h = w - 240, 20, 200, 20
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (0, 255, 0), 1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_w * self.signal_strength / 100), bar_y + bar_h), (0, 255, 0), -1)

        cv2.rectangle(frame, (0, self.capture_zone_y_start), (w, self.capture_zone_y_end), (0, 255, 255), 2)
        p_name = POSE_NAMES_RU.get(self.current_pose, "---")
        cv2.putText(frame, f"POSE: {p_name}", (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        for b in self.blocks: b.draw(frame)
        if self.state == "MENU":
            cv2.putText(frame, "PRESS SPACE TO START", (w//2-140, h//2), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
        elif self.state == "GAME_OVER":
            cv2.putText(frame, "GAME OVER", (w//2-100, h//2), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,0,255), 3)
            cv2.putText(frame, "PRESS R TO RESTART", (w//2-120, h//2+40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)

def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    game = Game()
    skeleton_links = [(5,6), (5,7), (7,9), (6,8), (8,10), (5,11), (6,12), (11,12), (11,13), (13,15), (12,14), (14,16)]

    while True:
        ret, frame = cap.read()
        if not ret: break
        frame = cv2.flip(frame, 1)

        results = model(frame, imgsz=640, device=0, verbose=False, conf=0.5)
        keypoints_data = None

        if len(results) > 0 and results[0].keypoints is not None:
            kpts = results[0].keypoints.data.cpu().numpy()
            if len(kpts) > 0:
                keypoints_data = kpts[0]
                # РИСУЕМ СКЕЛЕТ (БЕЗ ГОЛОВЫ)
                for start_idx, end_idx in skeleton_links:
                    pt1, pt2 = keypoints_data[start_idx], keypoints_data[end_idx]
                    if pt1[2] > 0.5 and pt2[2] > 0.5:
                        cv2.line(frame, (int(pt1[0]), int(pt1[1])), (int(pt2[0]), int(pt2[1])), (0, 255, 0), 2)
                for i in range(5, 17): # Только тело
                    if keypoints_data[i][2] > 0.5:
                        cv2.circle(frame, (int(keypoints_data[i][0]), int(keypoints_data[i][1])), 4, (0, 0, 255), -1)

        game.update(keypoints_data)
        game.draw_ui(frame)

        cv2.imshow("SIGNAL FLOW", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 27: break
        elif key == ord(' '): game.reset()
        elif key == ord('r'): game.reset()

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
