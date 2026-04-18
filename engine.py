import os
from ultralytics import YOLO
from config import Config


class PoseEngine:
    def __init__(self):
        # Выбираем .engine если есть, иначе .pt
        model_path = Config.MODEL_ENGINE if os.path.exists(Config.MODEL_ENGINE) else Config.MODEL_PT
        self.model = YOLO(model_path)

    def classify(self, kpts):
        if kpts is None or len(kpts) < 17:
            return "UNKNOWN"

        try:
            # Ключевые точки (индексы COCO)
            NOSE = 0
            LEFT_EYE, RIGHT_EYE = 1, 2
            LEFT_EAR, RIGHT_EAR = 3, 4
            LEFT_SHOULDER, RIGHT_SHOULDER = 5, 6
            LEFT_ELBOW, RIGHT_ELBOW = 7, 8
            LEFT_WRIST, RIGHT_WRIST = 9, 10
            LEFT_HIP, RIGHT_HIP = 11, 12
            LEFT_KNEE, RIGHT_KNEE = 13, 14
            LEFT_ANKLE, RIGHT_ANKLE = 15, 16

            # Извлечение координат (x, y) — предполагаем, что kpts[i] = (x, y) или (x, y, conf)
            def get_xy(idx):
                return kpts[idx][0], kpts[idx][1]

            lw_x, lw_y = get_xy(LEFT_WRIST)
            rw_x, rw_y = get_xy(RIGHT_WRIST)
            ls_x, ls_y = get_xy(LEFT_SHOULDER)
            rs_x, rs_y = get_xy(RIGHT_SHOULDER)
            le_x, le_y = get_xy(LEFT_ELBOW)
            re_x, re_y = get_xy(RIGHT_ELBOW)
            lh_x, lh_y = get_xy(LEFT_HIP)
            rh_x, rh_y = get_xy(RIGHT_HIP)
            nose_x, nose_y = get_xy(NOSE)

            # Вспомогательные вычисления
            shoulder_width = abs(rs_x - ls_x)
            torso_height = ((lh_y + rh_y) / 2) - ((ls_y + rs_y) / 2)
            mid_hip_y = (lh_y + rh_y) / 2

            # ----- Классификация поз -----

            # 1. Руки вверх (обе руки выше плеч)
            if lw_y < ls_y and rw_y < rs_y:
                return "HANDS_UP"

            # 2. Т-поза (руки вытянуты в стороны примерно на уровне плеч)
            if (abs(lw_y - ls_y) < 40 and abs(rw_y - rs_y) < 40 and
                abs(lw_x - ls_x) > shoulder_width * 0.8 and
                abs(rw_x - rs_x) > shoulder_width * 0.8):
                return "T_POSE"

            # 3. Руки в бока (руки согнуты, кисти у пояса)
            # Проверяем, что локти отведены в стороны, а запястья около бёдер
            elbow_angle_left = self._angle_between(ls_x, ls_y, le_x, le_y, lw_x, lw_y)
            elbow_angle_right = self._angle_between(rs_x, rs_y, re_x, re_y, rw_x, rw_y)
            wrist_near_hip_left = abs(lw_y - lh_y) < torso_height * 0.3 and abs(lw_x - lh_x) < shoulder_width * 0.4
            wrist_near_hip_right = abs(rw_y - rh_y) < torso_height * 0.3 and abs(rw_x - rh_x) < shoulder_width * 0.4
            if (elbow_angle_left < 110 and elbow_angle_right < 110 and
                wrist_near_hip_left and wrist_near_hip_right):
                return "HANDS_ON_HIPS"

            # 4. Скрещенные руки (запястья близко друг к другу перед грудью)
            wrists_distance = ((lw_x - rw_x) ** 2 + (lw_y - rw_y) ** 2) ** 0.5
            if wrists_distance < shoulder_width * 0.5 and lw_y < mid_hip_y and rw_y < mid_hip_y:
                return "CROSSED_ARMS"

            # 5. Руки за голову (запястья около головы/ушей)
            left_wrist_near_head = ((lw_x - ls_x) ** 2 + (lw_y - ls_y) ** 2) ** 0.5 < shoulder_width * 0.6
            right_wrist_near_head = ((rw_x - rs_x) ** 2 + (rw_y - rs_y) ** 2) ** 0.5 < shoulder_width * 0.6
            if left_wrist_near_head and right_wrist_near_head and lw_y < ls_y and rw_y < rs_y:
                return "HANDS_BEHIND_HEAD"

            # 6. Одна рука вверх
            left_up = lw_y < ls_y
            right_up = rw_y < rs_y
            if left_up != right_up:
                return "ONE_HAND_UP"

            # 7. Поза мыслителя (одна рука у лица)
            # Проверяем близость одного из запястий к носу / подбородку
            left_to_nose = ((lw_x - nose_x) ** 2 + (lw_y - nose_y) ** 2) ** 0.5
            right_to_nose = ((rw_x - nose_x) ** 2 + (rw_y - nose_y) ** 2) ** 0.5
            face_size = ((nose_x - (LEFT_EYE + RIGHT_EYE)/2)**2 + (nose_y - (LEFT_EYE + RIGHT_EYE)/2)**2)**0.5 * 3
            if left_to_nose < face_size or right_to_nose < face_size:
                return "THINKER_POSE"

            # Можно добавить дополнительные проверки (поклон, приседание и т.д.)

        except (IndexError, TypeError, AttributeError):
            # Если структура ключевых точек не соответствует ожидаемой
            pass

        return "UNKNOWN"

    @staticmethod
    def _angle_between(ax, ay, bx, by, cx, cy):
        """Вычисляет угол ABC в градусах (точки A-B-C)"""
        import math
        ab = (ax - bx, ay - by)
        cb = (cx - bx, cy - by)
        dot = ab[0] * cb[0] + ab[1] * cb[1]
        mag_ab = math.hypot(*ab)
        mag_cb = math.hypot(*cb)
        if mag_ab == 0 or mag_cb == 0:
            return 180.0
        cos_angle = dot / (mag_ab * mag_cb)
        cos_angle = max(-1.0, min(1.0, cos_angle))
        return math.degrees(math.acos(cos_angle))