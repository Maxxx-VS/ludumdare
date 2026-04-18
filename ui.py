import pygame
import cv2
import os
from PIL import Image, ImageSequence
from config import Config


class UIRenderer:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.Font(None, 42)
        self.font_small = pygame.font.Font(None, 36)
        self.font_large = pygame.font.Font(None, 72)  # Добавлен крупный шрифт для уровней

        self.scale_factor = Config.WIN_HEIGHT / Config.CAM_HEIGHT
        self.scaled_width = int(Config.CAM_WIDTH * self.scale_factor)
        self.scaled_height = Config.WIN_HEIGHT
        self.right_panel_start = self.scaled_width
        self.panel_margin = 30

        self.logo_img = self._load_asset(Config.LOGO_PATH)
        self.loading_frames = self._load_gif(Config.LOADING_GIF_PATH)
        self.gif_fps = 15

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
        else:
            self._draw_error("ЛОГОТИП НЕ НАЙДЕН")

    def draw_loading(self):
        self.screen.fill((0, 0, 0))
        if self.loading_frames:
            current_time = pygame.time.get_ticks()
            frame_index = (current_time // (1000 // self.gif_fps)) % len(self.loading_frames)
            current_frame = self.loading_frames[frame_index]
            rect = current_frame.get_rect(center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT // 2))
            self.screen.blit(current_frame, rect)
        else:
            self._draw_error("GIF ЗАГРУЗКИ НЕ НАЙДЕН")

    def _draw_level_transition(self, game):
        """Заставка между уровнями"""
        self.screen.fill((15, 15, 20))
        level_num = game.current_level_index + 1
        dur = game.current_level_data["duration"]

        text_lvl = self.font_large.render(f"УРОВЕНЬ {level_num}", True, (255, 215, 0))
        self.screen.blit(text_lvl, text_lvl.get_rect(center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT // 2 - 50)))

        self._draw_text(f"Длительность: {dur} сек", (200, 200, 200),
                        center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT // 2 + 20), is_small=True)
        self._draw_text("Приготовьтесь!", (0, 255, 0), center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT // 2 + 80))

    def _draw_error(self, message):
        err_text = self.font.render(message, True, (255, 0, 0))
        self.screen.blit(err_text, err_text.get_rect(center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT // 2)))

    def draw(self, frame, game, cur_pose, is_correct):
        if game.state == "SPLASH":
            self.draw_splash()
            return
        if game.state == "LOADING":
            self.draw_loading()
            return
        if game.state == "LEVEL_TRANSITION":
            self._draw_level_transition(game)
            return

        # --- Основной интерфейс игры ---
        if frame is not None:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            surf = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
            scaled_surf = pygame.transform.scale(surf, (self.scaled_width, self.scaled_height))
            self.screen.fill((10, 10, 10))
            self.screen.blit(scaled_surf, (0, 0))

        if self.scaled_width < Config.WIN_WIDTH:
            pygame.draw.line(self.screen, (255, 255, 255), (self.scaled_width, 0),
                             (self.scaled_width, Config.WIN_HEIGHT), 3)

        panel_rect = pygame.Rect(self.right_panel_start, 0, Config.WIN_WIDTH - self.right_panel_start,
                                 Config.WIN_HEIGHT)
        s = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.screen.blit(s, (panel_rect.x, panel_rect.y))
        pygame.draw.rect(self.screen, (255, 255, 255), panel_rect, 2)

        self._draw_text("ЗАДАНИЕ", (220, 220, 220),
                        center=(self.right_panel_start + panel_rect.width // 2, self.panel_margin + 20))
        target_text = "---" if game.is_paused else Config.POSE_NAMES_RU.get(game.target_pose, "???")
        self._draw_text(target_text, (255, 255, 0),
                        center=(self.right_panel_start + panel_rect.width // 2, self.panel_margin + 100))

        show_success = game.completed or is_correct
        status_text = "ВЕРНО" if show_success else "НЕВЕРНО"
        status_color = (0, 255, 0) if show_success else (255, 80, 80)
        self._draw_text(status_text, status_color,
                        center=(self.right_panel_start + panel_rect.width // 2, self.panel_margin + 180))

        # Отображение текущего уровня в панели
        self._draw_text(f"Уровень: {game.current_level_index + 1} / {len(Config.LEVELS)}", (100, 200, 255),
                        center=(self.right_panel_start + panel_rect.width // 2, self.panel_margin + 260))

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

        if game.state in ["WIN", "LOSE"]:
            overlay = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            self.screen.blit(overlay, (panel_rect.x, panel_rect.y))
            msg = "ПОБЕДА (Все уровни пройдены)!" if game.state == "WIN" else "ИГРА ОКОНЧЕНА"
            self._draw_text(msg, (255, 255, 255),
                            center=(self.right_panel_start + panel_rect.width // 2, Config.WIN_HEIGHT // 2))

    def _draw_text(self, text, color, center=None, bottomright=None, is_small=False):
        font = self.font_small if is_small else self.font
        surf = font.render(str(text), True, color)
        rect = surf.get_rect()
        if center: rect.center = center
        if bottomright: rect.bottomright = bottomright
        self.screen.blit(surf, rect)