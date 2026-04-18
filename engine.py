import math
import os
from ultralytics import YOLO
from config import Config


class PoseEngine:
    def __init__(self):
        model_path = Config.MODEL_ENGINE if os.path.exists(Config.MODEL_ENGINE) else Config.MODEL_PT
        self.model = YOLO(model_path)

    def classify(self, kpts):
        if kpts is None or len(kpts) < 17:
            return "UNKNOWN"

        try:
            # Индексы COCO
            NOSE = 0
            LEFT_SHOULDER, RIGHT_SHOULDER = 5, 6
            LEFT_ELBOW, RIGHT_ELBOW = 7, 8
            LEFT_WRIST, RIGHT_WRIST = 9, 10
            LEFT_HIP, RIGHT_HIP = 11, 12
            LEFT_KNEE, RIGHT_KNEE = 13, 14
            LEFT_ANKLE, RIGHT_ANKLE = 15, 16

            def get_xy(idx):
                return kpts[idx][0], kpts[idx][1]

            # Координаты
            lw_x, lw_y = get_xy(LEFT_WRIST)
            rw_x, rw_y = get_xy(RIGHT_WRIST)
            ls_x, ls_y = get_xy(LEFT_SHOULDER)
            rs_x, rs_y = get_xy(RIGHT_SHOULDER)
            le_x, le_y = get_xy(LEFT_ELBOW)
            re_x, re_y = get_xy(RIGHT_ELBOW)
            lh_x, lh_y = get_xy(LEFT_HIP)
            rh_x, rh_y = get_xy(RIGHT_HIP)
            lk_x, lk_y = get_xy(LEFT_KNEE)
            rk_x, rk_y = get_xy(RIGHT_KNEE)
            la_x, la_y = get_xy(LEFT_ANKLE)
            ra_x, ra_y = get_xy(RIGHT_ANKLE)

            # Ширина плеч и высота корпуса для нормировки
            shoulder_width = abs(rs_x - ls_x)
            if shoulder_width < 1:
                shoulder_width = 1  # защита от деления на ноль
            torso_height = ((lh_y + rh_y) / 2) - ((ls_y + rs_y) / 2)

            # ----- Классификация (порядок важен) -----

            # 1. Звезда (STAR) — обе руки и обе ноги разведены в стороны
            # Руки вытянуты в стороны от плеч (угол в локте ~180°)
            left_arm_straight = self._angle_between(ls_x, ls_y, le_x, le_y, lw_x, lw_y) > 150
            right_arm_straight = self._angle_between(rs_x, rs_y, re_x, re_y, rw_x, rw_y) > 150
            # Кисти далеко от плеч по горизонтали
            left_hand_out = abs(lw_x - ls_x) > shoulder_width * 0.8
            right_hand_out = abs(rw_x - rs_x) > shoulder_width * 0.8
            # Ноги разведены (лодыжки далеко друг от друга по горизонтали)
            legs_spread = abs(la_x - ra_x) > shoulder_width * 1.2
            if left_arm_straight and right_arm_straight and left_hand_out and right_hand_out and legs_spread:
                return "STAR"

            # 2. Т-поза (обе руки в стороны примерно на уровне плеч)
            if (abs(lw_y - ls_y) < 40 and abs(rw_y - rs_y) < 40 and
                left_hand_out and right_hand_out):
                return "T_POSE"

            # 3. Руки вверх (обе выше плеч)
            if lw_y < ls_y and rw_y < rs_y:
                return "HANDS_UP"

            # 4. Одна рука в сторону (локоть почти прямой, рука горизонтальна)
            left_side = (left_arm_straight and abs(lw_y - ls_y) < 40 and abs(lw_x - ls_x) > shoulder_width * 0.7)
            right_side = (right_arm_straight and abs(rw_y - rs_y) < 40 and abs(rw_x - rs_x) > shoulder_width * 0.7)
            # Исключающий XOR: только одна рука в сторону
            if left_side != right_side:
                return "ONE_HAND_SIDE"

            # 5. Одна рука вверх (только одна рука выше плеча)
            left_up = lw_y < ls_y
            right_up = rw_y < rs_y
            if left_up != right_up:
                return "ONE_HAND_UP"

        except (IndexError, TypeError, AttributeError):
            pass

        return "UNKNOWN"

    @staticmethod
    def _angle_between(ax, ay, bx, by, cx, cy):
        """Угол ABC в градусах"""
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