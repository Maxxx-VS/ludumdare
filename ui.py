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
        self.font_large = pygame.font.Font(None, 72)

        self.scale_factor = Config.WIN_HEIGHT / Config.CAM_HEIGHT
        self.scaled_width = int(Config.CAM_WIDTH * self.scale_factor)
        self.scaled_height = Config.WIN_HEIGHT
        self.right_panel_start = self.scaled_width
        self.panel_margin = 30

        self.logo_img = self._load_asset(Config.LOGO_PATH)
        self.loading_frames = self._load_gif(Config.LOADING_GIF_PATH)
        self.gif_fps = 15

        # Вычисляем ширину боковой панели для максимального расширения картинок
        panel_width = Config.WIN_WIDTH - self.right_panel_start
        max_img_width = panel_width - (self.panel_margin * 2)
        max_img_height = Config.WIN_HEIGHT // 2  # Ограничение по высоте, чтобы не перекрыть статистику внизу

        # Загрузка и динамическое масштабирование картинок поз
        self.pose_images = {}
        for pose_key, path in Config.POSE_IMAGES.items():
            img = self._load_asset(path)
            if img:
                rect = img.get_rect()
                # Масштабируем до максимально возможного размера в панели
                scale = min(max_img_width / rect.width, max_img_height / rect.height)
                new_size = (int(rect.width * scale), int(rect.height * scale))
                img = pygame.transform.smoothscale(img, new_size)
                self.pose_images[pose_key] = img

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

        # 1. Отрисовка кадра камеры
        if frame is not None:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            surf = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
            scaled_surf = pygame.transform.scale(surf, (self.scaled_width, self.scaled_height))
            self.screen.fill((10, 10, 10))
            self.screen.blit(scaled_surf, (0, 0))

        # 2. Отрисовка боковой панели (фон)
        panel_rect = pygame.Rect(self.right_panel_start, 0, Config.WIN_WIDTH - self.right_panel_start,
                                 Config.WIN_HEIGHT)
        s = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.screen.blit(s, (panel_rect.x, panel_rect.y))
        pygame.draw.rect(self.screen, (255, 255, 255), panel_rect, 2)

        # 3. ВЕРХНЯЯ ЧАСТЬ: Задание (Только крупная картинка)
        if not game.is_paused:
            target_img = self.pose_images.get(game.target_pose)
            if target_img:
                # Центрируем по ширине панели, прижимаем к верхнему краю с отступом panel_margin
                img_rect = target_img.get_rect(center=(self.right_panel_start + panel_rect.width // 2,
                                                       self.panel_margin + target_img.get_height() // 2))
                self.screen.blit(target_img, img_rect)
            else:
                # Резервный текст, если картинка не загрузилась
                target_text = Config.POSE_NAMES_RU.get(game.target_pose, "???")
                self._draw_text(target_text, (255, 255, 0),
                                center=(self.right_panel_start + panel_rect.width // 2, self.panel_margin + 50))

        # 4. НИЖНЯЯ ЧАСТЬ: Статистика (всегда видна, нетронута)
        bottom_y = Config.WIN_HEIGHT - self.panel_margin

        # Рестарт
        self._draw_text("R / SPACE — рестарт", (180, 180, 180), is_small=True,
                        bottomright=(Config.WIN_WIDTH - self.panel_margin, bottom_y))

        # Текущая поза
        pose_name = Config.POSE_NAMES_RU.get(cur_pose, "---")
        self._draw_text(f"Текущая: {pose_name}", (0, 255, 0), is_small=True,
                        bottomright=(Config.WIN_WIDTH - self.panel_margin, bottom_y - 40))

        # Жизни (шкала из 10 сегментов)
        rect_w, rect_h, gap = 20, 15, 5
        start_x = Config.WIN_WIDTH - self.panel_margin - (10 * rect_w + 9 * gap)
        for i in range(10):
            color = (0, 255, 0) if i < game.lives else (100, 100, 100)
            pygame.draw.rect(self.screen, color, (start_x + i * (rect_w + gap), bottom_y - 80, rect_w, rect_h))

        # Таймер
        self._draw_text(f"Осталось: {game.time_left} сек", (255, 255, 255),
                        bottomright=(Config.WIN_WIDTH - self.panel_margin, bottom_y - 110))

        # Счёт
        self._draw_text(f"Счёт: {game.score}", (255, 255, 255),
                        bottomright=(Config.WIN_WIDTH - self.panel_margin, bottom_y - 150))

        # 5. Оверлей финала
        if game.state in ["WIN", "LOSE"]:
            overlay = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            self.screen.blit(overlay, (panel_rect.x, panel_rect.y))
            msg = "ПОБЕДА!" if game.state == "WIN" else "ИГРА ОКОНЧЕНА"
            self._draw_text(msg, (255, 255, 255),
                            center=(self.right_panel_start + panel_rect.width // 2, Config.WIN_HEIGHT // 2))

    def _draw_text(self, text, color, center=None, bottomright=None, is_small=False):
        font = self.font_small if is_small else self.font
        surf = font.render(str(text), True, color)
        rect = surf.get_rect()
        if center: rect.center = center
        if bottomright: rect.bottomright = bottomright
        self.screen.blit(surf, rect)