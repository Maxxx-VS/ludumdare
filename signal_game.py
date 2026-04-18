import os
import cv2
import numpy as np
import random
import pygame
from ultralytics import YOLO
from collections import deque


# ==========================================
# 1. КОНФИГУРАЦИЯ
# ==========================================
class Config:
    MODEL_PT = "yolo11s-pose.pt"
    MODEL_ENGINE = "yolo11s-pose.engine"
    # Размеры кадра OpenCV
    CAM_WIDTH, CAM_HEIGHT = 640, 480
    # Размеры окна Pygame
    WIN_WIDTH, WIN_HEIGHT = 1920, 1080
    CONFIDENCE = 0.6
    FPS = 30

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


# --- Логические классы (PoseEngine, SignalBlock, GameEngine, Renderer) остаются прежними ---
# Они работают в системе координат 640x480

class PoseEngine:
    def __init__(self):
        self._init_model()
        self.history = deque(maxlen=5)

    def _init_model(self):
        if not os.path.exists(Config.MODEL_ENGINE):
            YOLO(Config.MODEL_PT).export(format="engine", device=0, half=True)
        self.model = YOLO(Config.MODEL_ENGINE, task='pose')

    @staticmethod
    def get_angle(a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        ba, bc = a - b, c - b
        cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        return np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))

    def classify(self, kpts):
        if kpts is None: return "UNKNOWN"
        p = {name: kpts[idx][:2] for name, idx in Config.POINTS.items()}
        # Упрощенная проверка видимости ключевых точек
        req = [5, 6, 11, 12]
        if any(kpts[i][2] < Config.CONFIDENCE for i in req): return "UNKNOWN"

        l_elbow_ang = self.get_angle(p['L_SHOULDER'], p['L_ELBOW'], p['L_WRIST'])
        r_elbow_ang = self.get_angle(p['R_SHOULDER'], p['R_ELBOW'], p['R_WRIST'])
        l_knee_ang = self.get_angle(p['L_HIP'], p['L_KNEE'], p['L_ANKLE'])
        r_knee_ang = self.get_angle(p['R_HIP'], p['R_KNEE'], p['R_ANKLE'])
        mid_sh, mid_hp = (p['L_SHOULDER'] + p['R_SHOULDER']) / 2, (p['L_HIP'] + p['R_HIP']) / 2

        res = "UNKNOWN"
        if 160 < l_elbow_ang < 200 and 160 < r_elbow_ang < 200 and abs(p['L_WRIST'][1] - p['L_SHOULDER'][1]) < 50:
            res = "T_POSE"
        elif p['L_WRIST'][1] < p['L_SHOULDER'][1] - 30:
            res = "HANDS_UP"
        elif l_knee_ang < 120 and mid_hp[1] > mid_sh[1] + 80:
            res = "SQUAT"
        elif abs(p['L_SHOULDER'][1] - p['R_SHOULDER'][1]) > 40:
            res = "LEFT_LEAN" if p['L_SHOULDER'][1] > p['R_SHOULDER'][1] else "RIGHT_LEAN"
        elif np.linalg.norm(p['L_WRIST'] - p['R_SHOULDER']) < 60:
            res = "CROSS_ARMS"

        self.history.append(res)
        return max(set(self.history), key=self.history.count)


class SignalBlock:
    def __init__(self, speed_mult):
        self.pose = random.choice(Config.POSES)
        self.x = random.randint(20, Config.CAM_WIDTH - 200)
        self.y, self.speed = -50, 2.0 * speed_mult
        self.w, self.h, self.hit = 180, 50, False

    def update(self): self.y += self.speed


class GameEngine:
    def __init__(self):
        self.state = "MENU"
        self.reset()
        self.z_start, self.z_end = Config.CAM_HEIGHT - 120, Config.CAM_HEIGHT - 20

    def reset(self):
        self.score, self.combo, self.signal = 0, 0, 100.0
        self.blocks, self.spawn_timer, self.speed_mult = [], 0, 1.0
        self.state = "PLAYING"

    def process_logic(self, current_pose):
        if self.state != "PLAYING": return
        self.spawn_timer += 1
        if self.spawn_timer >= max(20, 60 - int(self.score / 50)):
            self.blocks.append(SignalBlock(self.speed_mult))
            self.spawn_timer = 0
        for b in self.blocks[:]:
            b.update()
            if b.y > Config.CAM_HEIGHT:
                self.blocks.remove(b);
                self.combo = 0;
                self.signal = max(0, self.signal - 15)
            elif self.z_start < b.y < self.z_end and not b.hit and current_pose == b.pose:
                b.hit = True;
                self.combo += 1;
                self.score += 100 + (self.combo * 20)
                self.signal = min(100, self.signal + 15);
                self.speed_mult = 1.0 + (self.score / 1500)
                self.blocks.remove(b)
        self.signal = max(0, self.signal - 0.2)
        if self.signal <= 0: self.state = "GAME_OVER"


class Renderer:
    @staticmethod
    def draw_skeleton(frame, kpts):
        if kpts is None: return
        for s, e in Config.SKELETON_LINKS:
            if kpts[s][2] > 0.5 and kpts[e][2] > 0.5:
                cv2.line(frame, (int(kpts[s][0]), int(kpts[s][1])), (int(kpts[e][0]), int(kpts[e][1])), (0, 255, 0), 2)

    @staticmethod
    def draw_ui(frame, game, current_pose):
        cv2.rectangle(frame, (0, 0), (Config.CAM_WIDTH, 50), (0, 0, 0), -1)
        cv2.putText(frame, f"SCORE: {game.score} | COMBO: {game.combo}", (10, 30), 2, 0.6, (0, 255, 0), 1)
        cv2.rectangle(frame, (0, game.z_start), (Config.CAM_WIDTH, game.z_end), (0, 255, 255), 1)
        for b in game.blocks:
            cv2.rectangle(frame, (b.x, int(b.y)), (b.x + b.w, int(b.y) + b.h), (0, 255, 0), 2)
            cv2.putText(frame, Config.POSE_NAMES_RU[b.pose], (b.x + 5, int(b.y) + 30), 2, 0.5, (0, 255, 0), 1)
        if game.state == "GAME_OVER": cv2.putText(frame, "GAME OVER", (200, 240), 2, 1, (0, 0, 255), 2)


# ==========================================
# ОСНОВНОЙ ЦИКЛ
# ==========================================
def main():
    pygame.init()
    screen = pygame.display.set_mode((Config.WIN_WIDTH, Config.WIN_HEIGHT))
    clock = pygame.time.Clock()

    cap = cv2.VideoCapture(0)
    cap.set(3, Config.CAM_WIDTH)
    cap.set(4, Config.CAM_HEIGHT)

    pose_eng = PoseEngine()
    game = GameEngine()
    view = Renderer()

    # Координаты для левого нижнего угла
    pos_x = 0
    pos_y = Config.WIN_HEIGHT - Config.CAM_HEIGHT

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE: game.reset()
                if event.key == pygame.K_ESCAPE: running = False

        ret, frame = cap.read()
        if not ret: break
        frame = cv2.flip(frame, 1)

        results = pose_eng.model(frame, imgsz=640, device=0, verbose=False, conf=0.5)
        kpts = results[0].keypoints.data.cpu().numpy()[0] if (results and len(results[0].keypoints.data) > 0) else None

        cur_pose = pose_eng.classify(kpts)
        game.process_logic(cur_pose)

        view.draw_skeleton(frame, kpts)
        view.draw_ui(frame, game, cur_pose)

        # Конвертация кадра в формат Pygame
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # swapaxes(0,1) нужен, так как OpenCV [H,W] а Pygame [W,H]
        surf = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))

        # Отрисовка
        screen.fill((30, 30, 30))  # Темный фон основного окна
        screen.blit(surf, (pos_x, pos_y))  # Вставка в левый нижний угол

        pygame.display.flip()
        clock.tick(Config.FPS)

    cap.release()
    pygame.quit()


if __name__ == "__main__":
    main()