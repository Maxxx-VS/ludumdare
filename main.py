import pygame
import cv2
import numpy as np
from config import Config
from engine import PoseEngine
from game_logic import GameEngine
from visuals import Renderer

def main():
    pygame.init()

    screen = pygame.display.set_mode(
        (Config.WIN_WIDTH, Config.WIN_HEIGHT),
        pygame.FULLSCREEN | pygame.DOUBLEBUF
    )
    pygame.display.set_caption("SIGNAL FLOW")
    clock = pygame.time.Clock()

    font = pygame.font.Font(None, 42)
    font_small = pygame.font.Font(None, 36)

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, Config.CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.CAM_HEIGHT)

    pose_eng = PoseEngine()
    game = GameEngine()
    view = Renderer()

    scale_factor = Config.WIN_HEIGHT / Config.CAM_HEIGHT
    scaled_width = int(Config.CAM_WIDTH * scale_factor)
    scaled_height = Config.WIN_HEIGHT
    pos_x = 0
    pos_y = 0

    # Определяем правую панель (свободная область)
    right_panel_start = scaled_width
    panel_margin = 30

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            if event.type == pygame.KEYDOWN and event.key in [pygame.K_SPACE, pygame.K_r]:
                game.reset()

        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)

        results = pose_eng.model(frame, imgsz=640, device=0, verbose=False, conf=Config.CONFIDENCE)

        kpts = None
        if results and len(results[0].keypoints.data) > 0:
            kpts = results[0].keypoints.data.cpu().numpy()[0]

        cur_pose = pose_eng.classify(kpts)
        is_correct = game.update(cur_pose)

        # Рисуем скелет на кадре
        view.draw_skeleton(frame, kpts)

        # Конвертация и масштабирование кадра
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        surf = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
        scaled_surf = pygame.transform.scale(surf, (scaled_width, scaled_height))

        screen.fill((10, 10, 10))
        screen.blit(scaled_surf, (pos_x, pos_y))

        # Разделительная линия
        if scaled_width < Config.WIN_WIDTH:
            pygame.draw.line(screen, (80, 80, 80),
                             (scaled_width, 0), (scaled_width, Config.WIN_HEIGHT), 2)

        # ---- Отрисовка UI в правой свободной панели ----
        # Полупрозрачный фон для панели (по желанию)
        panel_rect = pygame.Rect(right_panel_start, 0,
                                 Config.WIN_WIDTH - right_panel_start, Config.WIN_HEIGHT)
        s = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        screen.blit(s, (panel_rect.x, panel_rect.y))

        # 1. Заголовок "ЗАДАНИЕ"
        title_surf = font.render("ЗАДАНИЕ", True, (220, 220, 220))
        title_rect = title_surf.get_rect(center=(right_panel_start + panel_rect.width//2,
                                                 panel_margin + 20))
        screen.blit(title_surf, title_rect)

        # 2. Целевая поза (крупно)
        target_text = Config.POSE_NAMES_RU.get(game.target_pose, "???")
        target_surf = font.render(target_text, True, (255, 255, 0))
        target_rect = target_surf.get_rect(center=(right_panel_start + panel_rect.width//2,
                                                   panel_margin + 100))
        screen.blit(target_surf, target_rect)

        # 3. Статус выполнения (True/False)
        status_text = "ВЕРНО" if is_correct else "НЕВЕРНО"
        status_color = (0, 255, 0) if is_correct else (255, 80, 80)
        status_surf = font.render(status_text, True, status_color)
        status_rect = status_surf.get_rect(center=(right_panel_start + panel_rect.width//2,
                                                   panel_margin + 180))
        screen.blit(status_surf, status_rect)

        # 4. Счёт (внизу справа, как и было)
        score_text = f"Счёт: {game.score}"
        score_surf = font.render(score_text, True, (255, 255, 255))
        score_rect = score_surf.get_rect(bottomright=(Config.WIN_WIDTH - panel_margin,
                                                      Config.WIN_HEIGHT - panel_margin))
        screen.blit(score_surf, score_rect)

        # 5. Текущая распознанная поза (под счётом)
        pose_name = Config.POSE_NAMES_RU.get(cur_pose, "---")
        pose_color = (0, 255, 0) if cur_pose != "UNKNOWN" else (255, 100, 100)
        pose_surf = font_small.render(f"Текущая: {pose_name}", True, pose_color)
        pose_rect = pose_surf.get_rect(bottomright=(Config.WIN_WIDTH - panel_margin,
                                                    Config.WIN_HEIGHT - panel_margin - 50))
        screen.blit(pose_surf, pose_rect)

        # Короткая подсказка
        hint_surf = font_small.render("R / SPACE — новая поза", True, (180, 180, 180))
        hint_rect = hint_surf.get_rect(bottomright=(Config.WIN_WIDTH - panel_margin,
                                                    Config.WIN_HEIGHT - panel_margin - 100))
        screen.blit(hint_surf, hint_rect)

        pygame.display.flip()
        clock.tick(Config.FPS)

    cap.release()
    pygame.quit()

if __name__ == "__main__":
    main()