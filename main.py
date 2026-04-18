import pygame
import cv2
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

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, Config.CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.CAM_HEIGHT)

    pose_eng = PoseEngine()
    game = GameEngine()
    view = Renderer()

    pos_x = 0
    pos_y = Config.WIN_HEIGHT - Config.CAM_HEIGHT

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            if event.type == pygame.KEYDOWN and event.key in [pygame.K_SPACE, pygame.K_r]:
                game.reset()

        ret, frame = cap.read()
        if not ret: break
        frame = cv2.flip(frame, 1)

        # Нейросеть
        results = pose_eng.model(frame, imgsz=640, device=0, verbose=False, conf=Config.CONFIDENCE)

        kpts = None
        if results and len(results[0].keypoints.data) > 0:
            kpts = results[0].keypoints.data.cpu().numpy()[0]

        cur_pose = pose_eng.classify(kpts)
        game.process_logic(cur_pose)

        # Отрисовка
        view.draw_skeleton(frame, kpts)
        view.draw_ui(frame, game, cur_pose)

        # CV2 -> Pygame
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        surf = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))

        screen.fill((10, 10, 10))
        screen.blit(surf, (pos_x, pos_y))

        pygame.display.flip()
        clock.tick(Config.FPS)

    cap.release()
    pygame.quit()


if __name__ == "__main__":
    main()