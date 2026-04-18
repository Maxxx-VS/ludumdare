import math
import os
from ultralytics import YOLO
from config import Config


class PoseEngine:
    def __init__(self):
        model_path = Config.MODEL_ENGINE if os.path.exists(Config.MODEL_ENGINE) else Config.MODEL_PT
        self.model = YOLO(model_path)

    def classify(self, kpts):
        if kpts is None or len(kpts) < 17: return "UNKNOWN"
        try:
            def get_xy(idx):
                return kpts[idx][0], kpts[idx][1]

            lw_x, lw_y = get_xy(9);
            rw_x, rw_y = get_xy(10)
            ls_x, ls_y = get_xy(5);
            rs_x, rs_y = get_xy(6)
            le_x, le_y = get_xy(7);
            re_x, re_y = get_xy(8)
            la_x, la_y = get_xy(15);
            ra_x, ra_y = get_xy(16)

            shoulder_width = max(1, abs(rs_x - ls_x))

            # Углы и вытяжение рук
            left_arm_straight = self._angle_between(ls_x, ls_y, le_x, le_y, lw_x, lw_y) > 150
            right_arm_straight = self._angle_between(rs_x, rs_y, re_x, re_y, rw_x, rw_y) > 150
            left_hand_out = abs(lw_x - ls_x) > shoulder_width * 0.8
            right_hand_out = abs(rw_x - rs_x) > shoulder_width * 0.8

            # STAR
            if left_arm_straight and right_arm_straight and left_hand_out and right_hand_out and abs(
                    la_x - ra_x) > shoulder_width * 1.1:
                return "STAR"
            # T_POSE
            if abs(lw_y - ls_y) < 50 and abs(rw_y - rs_y) < 50 and left_hand_out and right_hand_out:
                return "T_POSE"
            # HANDS_UP
            if lw_y < ls_y and rw_y < rs_y: return "HANDS_UP"
            # ONE_HAND_SIDE
            l_side = left_arm_straight and abs(lw_y - ls_y) < 50 and left_hand_out
            r_side = right_arm_straight and abs(rw_y - rs_y) < 50 and right_hand_out
            if l_side != r_side: return "ONE_HAND_SIDE"
            # ONE_HAND_UP
            if (lw_y < ls_y) != (rw_y < rs_y): return "ONE_HAND_UP"

        except:
            pass
        return "UNKNOWN"

    @staticmethod
    def _angle_between(ax, ay, bx, by, cx, cy):
        ab = (ax - bx, ay - by);
        cb = (cx - bx, cy - by)
        dot = ab[0] * cb[0] + ab[1] * cb[1]
        mag_ab = math.hypot(*ab);
        mag_cb = math.hypot(*cb)
        if mag_ab == 0 or mag_cb == 0: return 180.0
        return math.degrees(math.acos(max(-1.0, min(1.0, dot / (mag_ab * mag_cb)))))