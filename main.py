import pygame
import cv2
from engine import Config, PoseEngine, GameEngine, Renderer
from renderer_utils import PygameBridge


def main():
    # --- Инициализация Pygame ---
    pygame.init()
    screen = pygame.display.set_mode(
        (Config.WIN_WIDTH, Config.WIN_HEIGHT),
        pygame.FULLSCREEN | pygame.DOUBLEBUF
    )
    pygame.display.set_caption("Signal Flow Game")
    clock = pygame.time.Clock()

    # --- Инициализация систем ---
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, Config.CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.CAM_HEIGHT)

    pose_eng = PoseEngine()
    game = GameEngine()
    cv_view = Renderer()
    bridge = PygameBridge()

    # Координаты для левого нижнего угла
    POS_X = 0
    POS_Y = Config.WIN_HEIGHT - Config.CAM_HEIGHT

    running = True
    while running:
        # 1. События Pygame
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key in [pygame.K_SPACE, pygame.K_r]:
                    game.reset()

        # 2. Захват кадра и обработка (OpenCV/YOLO)
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)

        # Нейросеть и игровая логика
        results = pose_eng.model(frame, imgsz=640, device=0, verbose=False, conf=0.5)
        kpts = results[0].keypoints.data.cpu().numpy()[0] if (results and len(results[0].keypoints.data) > 0) else None

        cur_pose = pose_eng.classify(kpts)
        game.process_logic(cur_pose)

        # 3. Отрисовка OpenCV элементов на кадре
        cv_view.draw_skeleton(frame, kpts)
        cv_view.draw_ui(frame, game, cur_pose)

        # 4. Вывод в окно Pygame
        # Конвертируем готовый кадр в поверхность
        game_surface = bridge.cv_to_pygame(frame)

        screen.fill((20, 20, 20))  # Очистка фона
        screen.blit(game_surface, (POS_X, POS_Y))  # Вставляем в угол

        pygame.display.flip()
        clock.tick(Config.FPS)

    cap.release()
    pygame.quit()


if __name__ == "__main__":
    main()