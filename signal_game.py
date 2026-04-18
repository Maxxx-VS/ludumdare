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

# Звук (раскомментировать при необходимости)
# import pygame
# pygame.mixer.init()
# sound_correct = pygame.mixer.Sound("correct.wav")
# sound_wrong = pygame.mixer.Sound("wrong.wav")

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
NOSE = 0
LEFT_EYE, RIGHT_EYE = 1, 2
LEFT_EAR, RIGHT_EAR = 3, 4
LEFT_SHOULDER, RIGHT_SHOULDER = 5, 6
LEFT_ELBOW, RIGHT_ELBOW = 7, 8
LEFT_WRIST, RIGHT_WRIST = 9, 10
LEFT_HIP, RIGHT_HIP = 11, 12
LEFT_KNEE, RIGHT_KNEE = 13, 14
LEFT_ANKLE, RIGHT_ANKLE = 15, 16

def angle_between_points(a, b, c):
    """Вычисляет угол ABC в градусах."""
    a = np.array(a); b = np.array(b); c = np.array(c)
    ba = a - b
    bc = c - b
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    return np.degrees(angle)

def get_keypoint_xy(kp, idx):
    """Возвращает (x, y) если точка видима, иначе None."""
    if kp[idx][2] > POSE_CONFIDENCE:
        return (int(kp[idx][0]), int(kp[idx][1]))
    return None

class PoseClassifier:
    """Классификатор поз на основе углов и относительных положений."""
    
    @staticmethod
    def classify(keypoints):
        """
        keypoints: numpy array [17, 3] (x, y, conf)
        Возвращает строку с названием позы.
        """
        # Проверка видимости основных точек
        required = [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP,
                    LEFT_ELBOW, RIGHT_ELBOW, LEFT_WRIST, RIGHT_WRIST,
                    LEFT_KNEE, RIGHT_KNEE]
        for idx in required:
            if keypoints[idx][2] < POSE_CONFIDENCE:
                return "UNKNOWN"
        
        # Получаем координаты
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
        
        # Вычисляем углы
        left_elbow_angle = angle_between_points(ls, le, lw)
        right_elbow_angle = angle_between_points(rs, re, rw)
        left_shoulder_angle = angle_between_points(le, ls, lh)
        right_shoulder_angle = angle_between_points(re, rs, rh)
        left_knee_angle = angle_between_points(lh, lk, keypoints[LEFT_ANKLE][:2])
        right_knee_angle = angle_between_points(rh, rk, keypoints[RIGHT_ANKLE][:2])
        
        # Относительные положения
        mid_shoulder = (ls + rs) / 2
        mid_hip = (lh + rh) / 2
        
        # Руки в стороны (T-pose)
        if (160 < left_elbow_angle < 200 and 160 < right_elbow_angle < 200 and
            abs(lw[1] - ls[1]) < 50 and abs(rw[1] - rs[1]) < 50 and
            abs(ls[0] - lw[0]) > 50 and abs(rs[0] - rw[0]) > 50):
            return "T_POSE"
        
        # Руки вверх (Victory)
        if (lw[1] < ls[1] - 30 and rw[1] < rs[1] - 30 and
            left_elbow_angle > 140 and right_elbow_angle > 140):
            return "HANDS_UP"
        
        # Присед (Squat) - колени согнуты, бедра ниже обычного
        if (left_knee_angle < 120 and right_knee_angle < 120 and
            mid_hip[1] > mid_shoulder[1] + 80):
            return "SQUAT"
        
        # Наклон влево (плечи наклонены)
        shoulder_slope = abs(ls[1] - rs[1])
        if shoulder_slope > 40:
            if ls[1] > rs[1]:
                return "LEFT_LEAN"
            else:
                return "RIGHT_LEAN"
        
        # Руки скрещены на груди (запястья близко к противоположным плечам)
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
    """Падающий блок с требованием позы."""
    def __init__(self, pose_type, x, y, speed):
        self.pose = pose_type
        self.x = x
        self.y = y
        self.speed = speed
        self.width = 180
        self.height = 50
        self.active = True
        self.hit = False  # был ли успешно активирован
    
    def update(self):
        self.y += self.speed
    
    def draw(self, frame):
        color = (0, 255, 0) if not self.hit else (255, 255, 0)
        cv2.rectangle(frame, (self.x, int(self.y)), (self.x + self.width, int(self.y) + self.height), color, 2)
        cv2.putText(frame, POSE_NAMES_RU[self.pose], (self.x + 10, int(self.y) + 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    def is_in_capture_zone(self, zone_y_start, zone_y_end):
        """Проверяет, находится ли блок в зоне захвата."""
        block_bottom = self.y + self.height
        return (self.y < zone_y_end and block_bottom > zone_y_start)

class Game:
    def __init__(self):
        self.state = "MENU"  # MENU, PLAYING, GAME_OVER
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.signal_strength = 0  # 0..100
        self.blocks = []
        self.frame_count = 0
        self.spawn_timer = 0
        self.base_speed = 2.0
        self.speed_multiplier = 1.0
        self.pose_classifier = PoseClassifier()
        self.current_pose = "UNKNOWN"
        
        # Зоны экрана
        self.capture_zone_y_start = CAMERA_HEIGHT - 120
        self.capture_zone_y_end = CAMERA_HEIGHT - 20
        
        # Для сглаживания распознавания
        self.pose_history = deque(maxlen=5)
        
    def reset(self):
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.signal_strength = 0
        self.blocks = []
        self.spawn_timer = 0
        self.speed_multiplier = 1.0
        self.pose_history.clear()
        self.state = "PLAYING"
    
    def spawn_block(self):
        """Создаёт новый блок в случайной позиции по X вверху экрана."""
        pose = random.choice(POSE_LIST)
        x = random.randint(CAMERA_WIDTH - 200, CAMERA_WIDTH - 20)
        speed = self.base_speed * self.speed_multiplier
        self.blocks.append(SignalBlock(pose, x, -50, speed))
    
    def update(self, keypoints):
        # Обновление текущей позы с фильтрацией
        if keypoints is not None:
            pose = self.pose_classifier.classify(keypoints)
            self.pose_history.append(pose)
            # Выбираем наиболее частую позу из истории
            if len(self.pose_history) > 0:
                self.current_pose = max(set(self.pose_history), key=self.pose_history.count)
        else:
            self.current_pose = "UNKNOWN"
        
        if self.state != "PLAYING":
            return
        
        # Спавн блоков
        self.spawn_timer += 1
        spawn_rate = max(20, 60 - int(self.score / 50))  # чаще с ростом очков
        if self.spawn_timer >= spawn_rate:
            self.spawn_block()
            self.spawn_timer = 0
        
        # Обновление блоков и проверка попаданий
        blocks_to_remove = []
        for block in self.blocks:
            block.update()
            
            # Проверка выхода за экран
            if block.y > CAMERA_HEIGHT:
                blocks_to_remove.append(block)
                self.combo = 0
                self.signal_strength = max(0, self.signal_strength - 10)
                continue
            
            # Проверка попадания в зону захвата
            if block.is_in_capture_zone(self.capture_zone_y_start, self.capture_zone_y_end):
                if not block.hit and self.current_pose == block.pose:
                    # Успех!
                    block.hit = True
                    self.combo += 1
                    self.max_combo = max(self.max_combo, self.combo)
                    
                    # Начисление очков: база + комбо-бонус
                    base_points = 100
                    combo_bonus = self.combo * 20
                    self.score += base_points + combo_bonus
                    
                    # Усиление сигнала
                    self.signal_strength = min(100, self.signal_strength + 15)
                    
                    # Увеличение сложности
                    self.speed_multiplier = 1.0 + (self.score / 500)
                    
                    # Звук успеха (опционально)
                    # try: sound_correct.play()
                    # except: pass
                    
                    blocks_to_remove.append(block)
                elif not block.hit and block.y + block.height > self.capture_zone_y_end - 10:
                    # Промах - блок прошёл зону без совпадения
                    self.combo = 0
                    self.signal_strength = max(0, self.signal_strength - 15)
                    blocks_to_remove.append(block)
            elif block.y + block.height > self.capture_zone_y_end:
                # Блок полностью прошёл зону без активации
                self.combo = 0
                self.signal_strength = max(0, self.signal_strength - 15)
                blocks_to_remove.append(block)
        
        # Удаление обработанных блоков
        for block in blocks_to_remove:
            if block in self.blocks:
                self.blocks.remove(block)
        
        # Постепенное затухание сигнала
        self.signal_strength = max(0, self.signal_strength - 0.5)
        
        # Условие окончания игры (сигнал упал до нуля)
        if self.signal_strength <= 0:
            self.state = "GAME_OVER"
    
    def draw_ui(self, frame):
        """Отрисовка всего интерфейса."""
        h, w = frame.shape[:2]
        
        # Затемнение фона для интерфейса (полупрозрачный слой)
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 60), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # Верхняя панель: очки, комбо, сила сигнала
        cv2.putText(frame, f"SCORE: {self.score}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"COMBO: x{self.combo}", (200, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Индикатор сигнала
        signal_text = f"SIGNAL: {int(self.signal_strength)}%"
        cv2.putText(frame, signal_text, (w - 250, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        # Полоса прогресса
        bar_x = w - 240
        bar_y = 40
        bar_w = 200
        bar_h = 15
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (0, 255, 0), 1)
        fill_w = int(bar_w * self.signal_strength / 100)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), (0, 255, 0), -1)
        
        # Зона захвата
        cv2.rectangle(frame, (0, self.capture_zone_y_start), (w, self.capture_zone_y_end), (0, 255, 255), 2)
        cv2.putText(frame, "CAPTURE ZONE", (10, self.capture_zone_y_start - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        # Текущая поза игрока
        pose_display = POSE_NAMES_RU.get(self.current_pose, self.current_pose)
        cv2.putText(frame, f"CURRENT: {pose_display}", (10, h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Отрисовка падающих блоков
        for block in self.blocks:
            block.draw(frame)
        
        # Сообщения при состояниях
        if self.state == "MENU":
            cv2.putText(frame, "SIGNAL FLOW", (w//2 - 150, h//2 - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
            cv2.putText(frame, "Press SPACE to start", (w//2 - 140, h//2 + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(frame, "Repeat the poses in the capture zone!", (w//2 - 220, h//2 + 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        elif self.state == "GAME_OVER":
            cv2.putText(frame, "GAME OVER", (w//2 - 120, h//2 - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            cv2.putText(frame, f"Final Score: {self.score}", (w//2 - 130, h//2 + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
            cv2.putText(frame, f"Max Combo: x{self.max_combo}", (w//2 - 120, h//2 + 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
            cv2.putText(frame, "Press R to restart, ESC to quit", (w//2 - 160, h//2 + 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

# ---------- ОСНОВНОЙ ЦИКЛ ----------
def main():
    # Камера через GStreamer (Jetson) или обычный cv2.VideoCapture(0)
    # Попробуем сначала GStreamer, если не получится - обычная камера
    cap = cv2.VideoCapture(
        "v4l2src device=/dev/video0 ! video/x-raw, width=640, height=480 ! videoconvert ! video/x-raw,format=BGR ! appsink drop=1",
        cv2.CAP_GSTREAMER
    )
    if not cap.isOpened():
        print("⚠️ GStreamer камера не открыта, пробуем обычную...")
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    
    if not cap.isOpened():
        print("❌ Камера не найдена")
        return
    
    game = Game()
    clock = cv2.getTickFrequency()
    prev_tick = cv2.getTickCount()
    
    print("🚀 Игра запущена. Нажмите ПРОБЕЛ для старта.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Зеркалим для естественности
        frame = cv2.flip(frame, 1)
        
        # Инференс YOLO
        results = model(frame, imgsz=640, device=0, verbose=False, conf=0.5)
        
        keypoints = None
        if len(results) > 0 and results[0].keypoints is not None:
            kpts = results[0].keypoints.data.cpu().numpy()
            if len(kpts) > 0:
                # Берём первого человека (можно расширить на несколько)
                keypoints = kpts[0]
                # Отрисовка скелета
                annotated_frame = results[0].plot()
                # Совмещаем с оригиналом для плавности
                frame = annotated_frame
        
        # Обновление игры
        game.update(keypoints)
        
        # Отрисовка игрового UI
        game.draw_ui(frame)
        
        # FPS
        curr_tick = cv2.getTickCount()
        fps = clock / (curr_tick - prev_tick + 1e-6)
        prev_tick = curr_tick
        cv2.putText(frame, f"FPS: {int(fps)}", (frame.shape[1] - 100, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        cv2.imshow("SIGNAL FLOW", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break
        elif key == ord(' ') and game.state == "MENU":
            game.reset()
        elif key == ord('r') and game.state == "GAME_OVER":
            game.reset()
        elif key == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
