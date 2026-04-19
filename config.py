import os

class Config:
    MODEL_PT = "yolo11s-pose.pt"
    MODEL_ENGINE = "yolo11s-pose.engine"
    CAM_WIDTH, CAM_HEIGHT = 640, 480
    WIN_WIDTH, WIN_HEIGHT = 1920, 1080
    CONFIDENCE = 0.6
    FPS = 30

    # ГРОМКОСТЬ ПО УМОЛЧАНИЮ
    DEFAULT_VOLUME = 0.25

    # НАСТРОЙКИ ДИСТРАКТОРА (WALKER)
    WALKER_GIF_PATH = "./graphics/walker.gif"

    # ПУТИ К ГРАФИКЕ
    LOGO_PATH = "./graphics/logo.png"
    LOADING_GIF_PATH = "./graphics/loading.gif"
    OK_IMAGE_PATH = "./graphics/okey.png"
    ERROR_GIF_PATH = "./graphics/error.gif"

    # НОВЫЕ ПУТИ ДЛЯ ЗАГОЛОВКОВ МЕНЮ
    TITLE_IMAGE_PATH = "./graphics/title.png"
    SETTINGS_IMAGE_PATH = "./graphics/settings.png"
    SELECT_DIFFICULTY_IMAGE_PATH = "./graphics/select_difficullty.png"

    # НОВЫЕ ПУТИ ДЛЯ ЭКРАНОВ КОНЦА ИГРЫ
    WIN_IMAGE_PATH = "./graphics/youwin.png"
    LOSE_IMAGE_PATH = "./graphics/gameover.png"

    # ПУТИ К МУЗЫКЕ
    MUSIC_PATHS = {
        0: "./music/difficulty1.mp3",
        1: "./music/difficulty2.mp3",
        2: "./music/difficulty3.mp3"
    }

    # ПУТИ К ИЗОБРАЖЕНИЯМ ПОЗ ПО СЛОЖНОСТЯМ
    POSE_IMAGES = {
        "EASY": {
            "T_POSE": "./graphics/hum_t_pose.png",
            "HANDS_UP": "./graphics/hum_hands_up.png",
            "ONE_HAND_UP": "./graphics/hum_one_hand_up.png",
            "ONE_HAND_SIDE": "./graphics/hum_one_hand_side.png",
            "STAR": "./graphics/hum_star.png"
        },
        "NORMAL": {
            "T_POSE": "./graphics/stick_t_pose.png",
            "HANDS_UP": "./graphics/stick_t_hands_up.png",
            "ONE_HAND_UP": "./graphics/stick_one_hand_up.png",
            "ONE_HAND_SIDE": "./graphics/stick_one_hand_side.png",
            "STAR": "./graphics/stick_star.png",
            "SUMO": "./graphics/stick_sumo.png",
            "TREE": "./graphics/stick_tree.png"
        },
        "HARD": {
            "T_POSE": "./graphics/crab_t_pose.png",
            "HANDS_UP": "./graphics/crab_hands_up.png",
            "ONE_HAND_UP": "./graphics/crab_one_hand_up.png",
            "ONE_HAND_SIDE": "./graphics/crab_one_hand_side.png",
            "STAR": "./graphics/crab_star.png",
            "SUMO": "./graphics/crab_sumo.png",
            "TREE": "./graphics/crab_tree.png",
            "ONE_LEG_UP": "./graphics/crab_one_leg_up.png"
        }
    }

    POINTS = {
        'L_SHOULDER': 5, 'R_SHOULDER': 6, 'L_ELBOW': 7, 'R_ELBOW': 8,
        'L_WRIST': 9, 'R_WRIST': 10, 'L_HIP': 11, 'R_HIP': 12,
        'L_KNEE': 13, 'R_KNEE': 14, 'L_ANKLE': 15, 'R_ANKLE': 16
    }

    SKELETON_LINKS = [
        (5, 6), (5, 7), (7, 9), (6, 8), (8, 10), (5, 11),
        (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)
    ]

    POSES = ["T_POSE", "HANDS_UP", "ONE_HAND_UP", "ONE_HAND_SIDE", "STAR", "SUMO", "TREE", "ONE_LEG_UP"]

    POSE_NAMES_RU = {
        "T_POSE": "Руки в стороны",
        "HANDS_UP": "Руки вверх",
        "ONE_HAND_UP": "Одна рука вверх",
        "ONE_HAND_SIDE": "Одна рука в сторону",
        "STAR": "Звезда",
        "SUMO": "Сумо",
        "TREE": "Поза дерева",
        "ONE_LEG_UP": "Одна нога вверх",
        "UNKNOWN": "---"
    }

    AUTHORS = [
        "Testing - Artem Vysochanskiy",
        "Design - Yaroslav Kutsypin",
        "CV, Code - Maksim Vysochanskiy",
        "Code - Petr Bychkov",
    ]

    DIFFICULTIES = {
        "EASY": [
            {
                "duration": 25,
                "pose_pool": ["T_POSE", "HANDS_UP"],
                "pose_time_limit": 5000,
                "lives": 10,
                "max_lives": 10,
                "distractor_interval": 10000,
                "distractor_prob": 0.75
            },
            {
                "duration": 40,
                "pose_pool": ["T_POSE", "HANDS_UP", "ONE_HAND_SIDE"],
                "pose_time_limit": 4000,
                "lives": -1,
                "max_lives": 10,
                "distractor_interval": 10000,
                "distractor_prob": 0.75
            }
        ],
        "NORMAL": [
            {
                "duration": 30,
                "pose_pool": ["T_POSE", "HANDS_UP", "ONE_HAND_SIDE", "SUMO"],
                "pose_time_limit": 3500,
                "lives": 7,
                "max_lives": 7,
                "distractor_interval": 5000,
                "distractor_prob": 0.75
            },
            {
                "duration": 40,
                "pose_pool": ["T_POSE", "HANDS_UP", "ONE_HAND_SIDE", "ONE_HAND_UP", "SUMO", "TREE"],
                "pose_time_limit": 3000,
                "lives": -1,
                "max_lives": 7,
                "distractor_interval": 5000,
                "distractor_prob": 0.75
            },
            {
                "duration": 50,
                "pose_pool": ["T_POSE", "HANDS_UP", "ONE_HAND_SIDE", "ONE_HAND_UP", "STAR", "SUMO", "TREE"],
                "pose_time_limit": 2500,
                "lives": -1,
                "max_lives": 7,
                "distractor_interval": 5000,
                "distractor_prob": 0.75
            }
        ],
        "HARD": [
            {
                "duration": 30,
                "pose_pool": ["T_POSE", "HANDS_UP", "ONE_HAND_SIDE", "ONE_HAND_UP", "STAR", "SUMO", "TREE"],
                "pose_time_limit": 2000,
                "lives": 5,
                "max_lives": 5,
                "distractor_interval": 4000,
                "distractor_prob": 0.75
            },
            {
                "duration": 40,
                "pose_pool": ["T_POSE", "HANDS_UP", "ONE_HAND_SIDE", "ONE_HAND_UP", "STAR", "SUMO", "TREE", "ONE_LEG_UP"],
                "pose_time_limit": 1500,
                "lives": -1,
                "max_lives": 5,
                "distractor_interval": 4000,
                "distractor_prob": 0.75
            },
            {
                "duration": 50,
                "pose_pool": ["T_POSE", "HANDS_UP", "ONE_HAND_SIDE", "ONE_HAND_UP", "STAR", "SUMO", "TREE", "ONE_LEG_UP"],
                "pose_time_limit": 1000,
                "lives": -1,
                "max_lives": 5,
                "distractor_interval": 4000,
                "distractor_prob": 0.75
            }
        ]
    }