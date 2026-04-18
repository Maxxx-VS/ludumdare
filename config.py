import os

class Config:
    MODEL_PT = "yolo11s-pose.pt"
    MODEL_ENGINE = "yolo11s-pose.engine"
    CAM_WIDTH, CAM_HEIGHT = 640, 480
    WIN_WIDTH, WIN_HEIGHT = 1920, 1080
    CONFIDENCE = 0.6
    FPS = 30

    # ПУТИ К ГРАФИКЕ
    LOGO_PATH = "logo.png"
    LOADING_GIF_PATH = os.path.join("graphics", "loading.gif") # Убедитесь, что папка и файл есть

    POINTS = {
        'L_SHOULDER': 5, 'R_SHOULDER': 6, 'L_ELBOW': 7, 'R_ELBOW': 8,
        'L_WRIST': 9, 'R_WRIST': 10, 'L_HIP': 11, 'R_HIP': 12,
        'L_KNEE': 13, 'R_KNEE': 14, 'L_ANKLE': 15, 'R_ANKLE': 16
    }

    SKELETON_LINKS = [
        (5, 6), (5, 7), (7, 9), (6, 8), (8, 10), (5, 11),
        (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)
    ]

    POSES = ["T_POSE", "HANDS_UP", "ONE_HAND_UP", "ONE_HAND_SIDE", "STAR"]

    POSE_NAMES_RU = {
        "T_POSE": "Руки в стороны",
        "HANDS_UP": "Руки вверх",
        "ONE_HAND_UP": "Одна рука вверх",
        "ONE_HAND_SIDE": "Одна рука в сторону",
        "STAR": "Звезда",
        "UNKNOWN": "---"
    }