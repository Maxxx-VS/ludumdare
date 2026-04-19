import pygame
import cv2
import os
from PIL import Image, ImageSequence
from config import Config
from distractor import WalkerDistractor


class UIRenderer:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.Font(None, 42)
        self.font_small = pygame.font.Font(None, 36)
        self.font_large = pygame.font.Font(None, 72)

        self.scale_factor = Config.WIN_HEIGHT / Config.CAM_HEIGHT
        self.scaled_width = int(Config.CAM_WIDTH * self.scale_factor)
        self.scaled_height = Config.WIN_HEIGHT
        self.right_panel_start = self.scaled_width
        self.panel_margin = 30

        self.logo_img = self._load_asset(Config.LOGO_PATH)
        self.loading_frames = self._load_gif(Config.LOADING_GIF_PATH)
        self.gif_fps = 15

        panel_width = Config.WIN_WIDTH - self.right_panel_start
        img_display_width = panel_width - (self.panel_margin * 2)

        self.ok_img = self._load_asset(Config.OK_IMAGE_PATH)
        self.error_frames = self._load_gif(Config.ERROR_GIF_PATH)

        if self.ok_img:
            scale = img_display_width / self.ok_img.get_width()
            new_size = (int(self.ok_img.get_width() * scale), int(self.ok_img.get_height() * scale))
            self.ok_img = pygame.transform.smoothscale(self.ok_img, new_size)

        for i, frame in enumerate(self.error_frames):
            scale = img_display_width / frame.get_width()
            new_size = (int(frame.get_width() * scale), int(frame.get_height() * scale))
            self.error_frames[i] = pygame.transform.smoothscale(frame, new_size)

        self.win_img = self._load_asset(Config.WIN_IMAGE_PATH)
        if self.win_img:
            self.win_img = pygame.transform.smoothscale(self.win_img, (Config.WIN_WIDTH, Config.WIN_HEIGHT))

        self.lose_img = self._load_asset(Config.LOSE_IMAGE_PATH)
        if self.lose_img:
            self.lose_img = pygame.transform.smoothscale(self.lose_img, (Config.WIN_WIDTH, Config.WIN_HEIGHT))

        self.pose_images = {"EASY": {}, "NORMAL": {}, "HARD": {}}
        for difficulty, poses in Config.POSE_IMAGES.items():
            for pose_key, path in poses.items():
                img = self._load_asset(path)
                if img:
                    rect = img.get_rect()
                    scale = img_display_width / rect.width
                    new_size = (int(rect.width * scale), int(rect.height * scale))
                    img = pygame.transform.smoothscale(img, new_size)
                    self.pose_images[difficulty][pose_key] = img

        # Дистрактор
        self.distractor = WalkerDistractor()
        self.last_game_state = "SPLASH"

    def _load_asset(self, path):
        if os.path.exists(path):
            try:
                return pygame.image.load(path).convert_alpha()
            except pygame.error:
                return None
        return None

    def _load_gif(self, path):
        if not os.path.exists(path): return []
        frames = []
        try:
            pil_image = Image.open(path)
            for frame in ImageSequence.Iterator(pil_image):
                frame_rgba = frame.convert('RGBA')
                data = frame_rgba.tobytes()
                size = frame_rgba.size
                pygame_surface = pygame.image.fromstring(data, size, 'RGBA')
                frames.append(pygame_surface)
        except Exception as e:
            print(f"Ошибка загрузки GIF: {e}")
        return frames

    def draw_splash(self):
        self.screen.fill((0, 0, 0))
        if self.logo_img:
            rect = self.logo_img.get_rect(center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT // 2))
            self.screen.blit(self.logo_img, rect)

    def draw_main_menu(self, selected_index, mouse_pos):
        self.screen.fill((15, 15, 20))
        self._draw_text("SIGNAL FLOW", (255, 215, 0), center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT // 4),
                        is_large=True)

        rects = []
        options = ["New Game", "Settings", "Authors"]
        for i, opt in enumerate(options):
            color = (0, 255, 0) if i == selected_index else (200, 200, 200)
            center_y = Config.WIN_HEIGHT // 2 + i * 80
            rect = self._draw_text(opt, color, center=(Config.WIN_WIDTH // 2, center_y))
            if rect.collidepoint(mouse_pos):
                rect = self._draw_text(opt, (255, 255, 0), center=(Config.WIN_WIDTH // 2, center_y))
            rects.append(rect)
        return rects

    def draw_difficulty_menu(self, selected_index, mouse_pos, hard_unlocked):
        self.screen.fill((15, 15, 20))
        self._draw_text("SELECT DIFFICULTY", (255, 215, 0), center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT // 4),
                        is_large=True)
        rects = []
        options = ["Easy", "Normal", "Hard", "Back"]
        for i, opt in enumerate(options):
            if opt == "Hard" and not hard_unlocked:
                text = "Hard (Locked)"
                base_color = (100, 100, 100)
                hover_color = (100, 100, 100)
            else:
                text = opt
                base_color = (0, 255, 0) if i == selected_index else (200, 200, 200)
                hover_color = (255, 255, 0)
            center_y = Config.WIN_HEIGHT // 2 + i * 80
            rect = self._draw_text(text, base_color, center=(Config.WIN_WIDTH // 2, center_y))
            if rect.collidepoint(mouse_pos) and hover_color != (100, 100, 100):
                rect = self._draw_text(text, hover_color, center=(Config.WIN_WIDTH // 2, center_y))
            rects.append(rect)
        return rects

    def draw_settings(self, mouse_pos, current_volume):
        self.screen.fill((15, 15, 20))
        self._draw_text("SETTINGS", (255, 215, 0), center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT // 4),
                        is_large=True)
        self._draw_text("Music Volume:", (200, 200, 200),
                                         center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT // 2 - 40))
        slider_width, slider_height = 400, 10
        slider_x = (Config.WIN_WIDTH - slider_width) // 2
        slider_y = Config.WIN_HEIGHT // 2 + 10
        slider_rect = pygame.Rect(slider_x, slider_y, slider_width, slider_height)
        pygame.draw.rect(self.screen, (100, 100, 100), slider_rect, border_radius=5)
        filled_rect = pygame.Rect(slider_x, slider_y, int(slider_width * current_volume), slider_height)
        pygame.draw.rect(self.screen, (0, 255, 0), filled_rect, border_radius=5)
        handle_x = slider_x + int(slider_width * current_volume)
        pygame.draw.circle(self.screen, (255, 255, 255), (handle_x, slider_y + slider_height // 2), 15)
        vol_percent = int(current_volume * 100)
        self._draw_text(f"{vol_percent}%", (255, 255, 255),
                        center=(slider_x + slider_width + 60, slider_y + slider_height // 2))
        back_rect = self._draw_text("Back", (0, 255, 0), center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT - 100))
        if back_rect.collidepoint(mouse_pos):
            back_rect = self._draw_text("Back", (255, 255, 0), center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT - 100))
        return back_rect, slider_rect

    def draw_authors(self, mouse_pos):
        self.screen.fill((15, 15, 20))
        self._draw_text("AUTHORS", (255, 215, 0), center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT // 4), is_large=True)
        for i, author in enumerate(Config.AUTHORS):
            self._draw_text(author, (200, 200, 200),
                            center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT // 2 - 50 + i * 50))
        back_rect = self._draw_text("Back", (0, 255, 0), center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT - 100))
        if back_rect.collidepoint(mouse_pos):
            back_rect = self._draw_text("Back", (255, 255, 0), center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT - 100))
        return back_rect

    def draw_loading(self):
        self.screen.fill((0, 0, 0))
        if self.loading_frames:
            current_time = pygame.time.get_ticks()
            frame_index = (current_time // (1000 // self.gif_fps)) % len(self.loading_frames)
            current_frame = self.loading_frames[frame_index]
            rect = current_frame.get_rect(center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT // 2))
            self.screen.blit(current_frame, rect)

    def _draw_level_transition(self, game):
        self.screen.fill((15, 15, 20))
        level_num = game.current_level_index + 1
        dur = game.current_level_data["duration"]
        text_lvl = self.font_large.render(f"УРОВЕНЬ {level_num}", True, (255, 215, 0))
        self.screen.blit(text_lvl, text_lvl.get_rect(center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT // 2 - 50)))
        self._draw_text(f"Длительность: {dur} сек", (200, 200, 200),
                        center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT // 2 + 20), is_small=True)
        self._draw_text("Приготовьтесь!", (0, 255, 0), center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT // 2 + 80))

    def draw_end_screen(self, state):
        self.screen.fill((0, 0, 0))
        if state == "WIN" and self.win_img:
            self.screen.blit(self.win_img, (0, 0))
        elif state == "LOSE" and self.lose_img:
            self.screen.blit(self.lose_img, (0, 0))
        else:
            msg = "ПОБЕДА!" if state == "WIN" else "ИГРА ОКОНЧЕНА"
            self._draw_text(msg, (255, 255, 255),
                            center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT // 2), is_large=True)

    def draw(self, frame, game, cur_pose, is_correct):
        current_time = pygame.time.get_ticks()

        if self.last_game_state != "PLAYING" and game.state == "PLAYING":
            self.distractor.reset(current_time)
        self.last_game_state = game.state

        if game.state == "SPLASH":
            self.draw_splash()
            return
        if game.state == "LOADING":
            self.draw_loading()
            return
        if game.state == "LEVEL_TRANSITION":
            self._draw_level_transition(game)
            return

        if frame is not None:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            surf = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
            scaled_surf = pygame.transform.scale(surf, (self.scaled_width, self.scaled_height))
            self.screen.fill((10, 10, 10))
            self.screen.blit(scaled_surf, (0, 0))

        panel_rect = pygame.Rect(self.right_panel_start, 0, Config.WIN_WIDTH - self.right_panel_start,
                                 Config.WIN_HEIGHT)
        s = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.screen.blit(s, (panel_rect.x, panel_rect.y))
        pygame.draw.rect(self.screen, (255, 255, 255), panel_rect, 2)

        res_img = None
        if game.is_paused:
            if game.last_result_type == "SUCCESS":
                res_img = self.ok_img
            elif game.last_result_type == "ERROR" and self.error_frames:
                frame_idx = (current_time // (1000 // self.gif_fps)) % len(self.error_frames)
                res_img = self.error_frames[frame_idx]
        else:
            res_img = self.pose_images.get(game.difficulty, {}).get(game.target_pose)

        if res_img:
            img_rect = res_img.get_rect(center=(self.right_panel_start + panel_rect.width // 2,
                                                self.panel_margin + res_img.get_height() // 2))

            # 1. СНАЧАЛА рисуем картинку позы (она ложится на самый нижний слой)
            self.screen.blit(res_img, img_rect)

            # 2. ЗАТЕМ обновляем и рисуем дистрактора (он ляжет ПОВЕРХ позы)
            if game.state == "PLAYING":
                self.distractor.update(current_time, img_rect, game.is_paused, game.current_level_data)

                if not game.is_paused:
                    # Ограничиваем зону отрисовки правой панелью (чтобы не лез на окно OpenCV)
                    self.screen.set_clip(panel_rect)

                    # Рисуем дистрактора
                    self.distractor.draw(self.screen, current_time)

                    # Обязательно снимаем маску
                    self.screen.set_clip(None)

        elif not game.is_paused:
            target_text = Config.POSE_NAMES_RU.get(game.target_pose, "???")
            self._draw_text(target_text, (255, 255, 0),
                            center=(self.right_panel_start + panel_rect.width // 2, self.panel_margin + 50))

        bottom_y = Config.WIN_HEIGHT - self.panel_margin
        self._draw_text("R / SPACE — рестарт", (180, 180, 180), is_small=True,
                        bottomright=(Config.WIN_WIDTH - self.panel_margin, bottom_y))
        pose_name = Config.POSE_NAMES_RU.get(cur_pose, "---")
        self._draw_text(f"Текущая: {pose_name}", (0, 255, 0), is_small=True,
                        bottomright=(Config.WIN_WIDTH - self.panel_margin, bottom_y - 40))
        rect_w, rect_h, gap = 20, 15, 5
        start_x = Config.WIN_WIDTH - self.panel_margin - (10 * rect_w + 9 * gap)
        for i in range(10):
            color = (0, 255, 0) if i < game.lives else (100, 100, 100)
            pygame.draw.rect(self.screen, color, (start_x + i * (rect_w + gap), bottom_y - 80, rect_w, rect_h))
        self._draw_text(f"Осталось: {game.time_left} сек", (255, 255, 255),
                        bottomright=(Config.WIN_WIDTH - self.panel_margin, bottom_y - 110))
        self._draw_text(f"Счёт: {game.score}", (255, 255, 255),
                        bottomright=(Config.WIN_WIDTH - self.panel_margin, bottom_y - 150))

    def _draw_text(self, text, color, center=None, bottomright=None, is_small=False, is_large=False):
        if is_large: font = self.font_large
        elif is_small: font = self.font_small
        else: font = self.font
        surf = font.render(str(text), True, color)
        rect = surf.get_rect()
        if center: rect.center = center
        if bottomright: rect.bottomright = bottomright
        self.screen.blit(surf, rect)
        return rect