import os
import cv2
from ultralytics import YOLO

MODEL_PT = "yolo11s-pose.pt"
MODEL_ENGINE = "yolo11s-pose.engine"

# 1. Загружаем модель (скачает автоматически)
model = YOLO(MODEL_PT)

# 2. Конвертация в TensorRT (если ещё нет)
if not os.path.exists(MODEL_ENGINE):
    print("🔄 Конвертация в TensorRT engine...")
    model.export(format="engine", device=0, half=True)
    print("✅ Готово")
else:
    print("✅ Engine уже существует")

# 3. Загружаем engine модель
model = YOLO(MODEL_ENGINE)

# 4. Открываем камеру (лучше через GStreamer на Jetson)
cap = cv2.VideoCapture(
    "v4l2src device=/dev/video0 ! video/x-raw, width=640, height=480 ! videoconvert ! video/x-raw,format=BGR ! appsink drop=1",
    cv2.CAP_GSTREAMER
)

if not cap.isOpened():
    print("❌ Камера не открыта")
    exit()

print("🚀 Запуск инференса...")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 5. Инференс
    results = model(frame, imgsz=640, device=0, verbose=False)

    # 6. Отрисовка keypoints
    annotated = results[0].plot()

    # 7. Показ
    cv2.imshow("YOLO Pose (TensorRT)", annotated)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
