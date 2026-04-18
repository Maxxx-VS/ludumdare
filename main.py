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
        is_correct = game.update(cur_pose)   # обновляем игру и получаем флаг совпадения

        # Рисуем скелет
        view.draw_skeleton(frame, kpts)

        # Конвертация и масштабирование кадра
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        surf = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
        scaled_surf = pygame.transform.scale(surf, (scaled_width, scaled_height))

        screen.fill((10, 10, 10))
        screen.blit(scaled_surf, (pos_x, pos_y))

        # Разделительная линия (если нужно)
        if scaled_width < Config.WIN_WIDTH:
            line_y = Config.WIN_HEIGHT // 2
            start_x = scaled_width
            end_x = Config.WIN_WIDTH - 1
            pygame.draw.line(screen, (255, 255, 255), (start_x, line_y), (end_x, line_y), 2)

        margin = 20

        # --- ЗАДАНИЕ (сверху) ---
        target_text = f"Задание: {Config.POSE_NAMES_RU.get(game.target_pose, '???')}"
        target_surf = font.render(target_text, True, (255, 255, 0))
        target_rect = target_surf.get_rect(topleft=(margin, margin))
        screen.blit(target_surf, target_rect)

        correct_text = "True" if is_correct else "False"
        correct_color = (0, 255, 0) if is_correct else (255, 0, 0)
        correct_surf = font.render(correct_text, True, correct_color)
        correct_rect = correct_surf.get_rect(topleft=(margin, margin + 50))
        screen.blit(correct_surf, correct_rect)

        # --- СЧЁТ (справа внизу) ---
        score_text = f"Score: {game.score}"
        score_surf = font.render(score_text, True, (255, 255, 255))
        score_rect = score_surf.get_rect(bottomright=(Config.WIN_WIDTH - margin, Config.WIN_HEIGHT - margin))
        screen.blit(score_surf, score_rect)

        # --- ТЕКУЩАЯ ПОЗА (под счётом) ---
        pose_name = Config.POSE_NAMES_RU.get(cur_pose, "---")
        pose_color = (0, 255, 0) if cur_pose != "UNKNOWN" else (255, 0, 0)
        pose_surf = font.render(pose_name, True, pose_color)
        pose_rect = pose_surf.get_rect(bottomright=(Config.WIN_WIDTH - margin, Config.WIN_HEIGHT - margin - 40))
        screen.blit(pose_surf, pose_rect)

        pygame.display.flip()
        clock.tick(Config.FPS)

    cap.release()
    pygame.quit()

if __name__ == "__main__":
    main()