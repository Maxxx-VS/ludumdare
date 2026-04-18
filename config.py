import cv2

# Настройки камеры и модели
MODEL_PT = "yolo11s-pose.pt"
MODEL_ENGINE = "yolo11s-pose.engine"
WIDTH, HEIGHT = 640, 480
POSE_CONFIDENCE = 0.6

# Индексы COCO
SKELETON_LINKS = [(5,6), (5,7), (7,9), (6,8), (8,10), (5,11), (6,12),
                  (11,12), (11,13), (13,15), (12,14), (14,16)]

POSE_NAMES_RU = {
    "T_POSE": "Руки в стороны",
    "HANDS_UP": "Руки вверх",
    "SQUAT": "Присед",
    "LEFT_LEAN": "Наклон влево",
    "RIGHT_LEAN": "Наклон вправо",
    "CROSS_ARMS": "Руки крестом",
    "UNKNOWN": "---"
}