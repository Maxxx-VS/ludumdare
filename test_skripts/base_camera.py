#!/usr/bin/env python3
"""
Захват видео с USB-камеры (1920x1080 -> 1600x900), трекинг рук MediaPipe
с подавлением шумных предупреждений на ARM (Jetson).
"""

import os
import sys
import warnings

# ------------------------------------------------------------
# Подавление предупреждений NumPy на ARM (subnormal)
# ------------------------------------------------------------
# Отключаем предупреждения при вычислении параметров float
warnings.filterwarnings("ignore", category=UserWarning, module="numpy.core.getlimits")

# Альтернативный способ: установить переменную окружения до импорта numpy
os.environ["NPY_DISABLE_CPU_FEATURES"] = "FP16C"

import cv2
import mediapipe as mp
import numpy as np
import math
from typing import List, Optional, Tuple

# ------------------------------------------------------------
# Подавление лишних логов OpenCV и MediaPipe
# ------------------------------------------------------------
# OpenCV GStreamer warning (Cannot query video position)
cv2.setLogLevel(0)  # Отключает все предупреждения OpenCV (если мешают)

# MediaPipe использует absl logging, перенаправляем в /dev/null
# (но можно оставить для отладки)
if not sys.stderr.isatty():
    # Если вывод не в терминал, можно подавить
    pass

# ------------------------------------------------------------
# Конфигурация
# ------------------------------------------------------------
CAPTURE_WIDTH = 1920
CAPTURE_HEIGHT = 1080
CAPTURE_FPS = 30

# Рабочее разрешение (уменьшенное для ускорения MediaPipe)
WORK_WIDTH = 1600
WORK_HEIGHT = 900

# Параметры MediaPipe Hands
MP_HANDS = mp.solutions.hands
HANDS = MP_HANDS.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
MP_DRAWING = mp.solutions.drawing_utils
MP_DRAWING_STYLES = mp.solutions.drawing_styles

# ------------------------------------------------------------
# GStreamer пайплайн (захват 1920x1080 MJPEG)
# ------------------------------------------------------------
def gstreamer_pipeline(
    capture_width: int = CAPTURE_WIDTH,
    capture_height: int = CAPTURE_HEIGHT,
    framerate: int = CAPTURE_FPS,
) -> str:
    return (
        f"v4l2src device=/dev/video0 ! "
        f"image/jpeg, width={capture_width}, height={capture_height}, framerate={framerate}/1 ! "
        f"jpegdec ! videoconvert ! video/x-raw, format=BGR ! appsink"
    )

# ------------------------------------------------------------
# Вспомогательные функции для распознавания жестов
# ------------------------------------------------------------
def get_landmark_coords(hand_landmarks, width: int, height: int) -> List[Tuple[int, int]]:
    coords = []
    for lm in hand_landmarks.landmark:
        x = int(lm.x * width)
        y = int(lm.y * height)
        coords.append((x, y))
    return coords

def is_finger_extended(
    landmarks_px: List[Tuple[int, int]],
    finger_tip_idx: int,
    finger_dip_idx: int,
    finger_pip_idx: int,
    finger_mcp_idx: int,
) -> bool:
    tip = np.array(landmarks_px[finger_tip_idx])
    dip = np.array(landmarks_px[finger_dip_idx])
    mcp = np.array(landmarks_px[finger_mcp_idx])
    return np.linalg.norm(tip - mcp) > np.linalg.norm(dip - mcp)

def recognise_gesture(hand_landmarks, width: int, height: int) -> Optional[str]:
    coords = get_landmark_coords(hand_landmarks, width, height)
    
    fingers = {
        "thumb": is_finger_extended(coords, 4, 3, 2, 2),
        "index": is_finger_extended(coords, 8, 7, 6, 5),
        "middle": is_finger_extended(coords, 12, 11, 10, 9),
        "ring": is_finger_extended(coords, 16, 15, 14, 13),
        "pinky": is_finger_extended(coords, 20, 19, 18, 17),
    }
    
    thumb_tip = np.array(coords[4])
    index_tip = np.array(coords[8])
    distance = np.linalg.norm(thumb_tip - index_tip)
    if distance < 30:
        return "OK"
    
    extended_count = sum(1 for v in fingers.values() if v)
    if extended_count == 1 and fingers["index"]:
        return "Pointing"
    elif extended_count == 2 and fingers["index"] and fingers["middle"]:
        return "Peace"
    elif extended_count == 5:
        return "Open Hand"
    elif extended_count == 0:
        return "Fist"
    
    return None

def react_to_action(action: str, frame: np.ndarray):
    h, w = frame.shape[:2]
    if action:
        cv2.putText(frame, f"Action: {action}", (30, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
        if action == "OK":
            cv2.circle(frame, (w//2, h//2), 40, (0, 255, 255), -1)
    return frame

# ------------------------------------------------------------
# Основной цикл
# ------------------------------------------------------------
def main():
    print("Запуск GStreamer пайплайна...")
    pipeline = gstreamer_pipeline()
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        print("Ошибка открытия камеры.")
        return

    print(f"Камера открыта: {CAPTURE_WIDTH}x{CAPTURE_HEIGHT} @ {CAPTURE_FPS} fps")
    print(f"Рабочее разрешение (после resize): {WORK_WIDTH}x{WORK_HEIGHT}")
    print("MediaPipe Hands активен. Для выхода нажмите 'q' или ESC.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Потерян кадр.")
            break

        # Уменьшаем кадр до рабочего разрешения
        frame = cv2.resize(frame, (WORK_WIDTH, WORK_HEIGHT), interpolation=cv2.INTER_LINEAR)

        # MediaPipe обрабатывает RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = HANDS.process(rgb_frame)

        action_text = None
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Отрисовка скелета
                MP_DRAWING.draw_landmarks(
                    frame,
                    hand_landmarks,
                    MP_HANDS.HAND_CONNECTIONS,
                    MP_DRAWING_STYLES.get_default_hand_landmarks_style(),
                    MP_DRAWING_STYLES.get_default_hand_connections_style()
                )
                if action_text is None:
                    action_text = recognise_gesture(hand_landmarks, WORK_WIDTH, WORK_HEIGHT)

        frame = react_to_action(action_text, frame)

        cv2.imshow("Hand Tracking (1600x900)", frame)
        if cv2.waitKey(1) & 0xFF in (ord('q'), 27):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
