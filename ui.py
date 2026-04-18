import pygame
import cv2
import os
from config import Config


class UIRenderer:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.Font(None, 42)
        self.font_small = pygame.font.Font(None, 36)

        self.scale_factor = Config.WIN_HEIGHT / Config.CAM_HEIGHT
        self.scaled_width = int(Config.CAM_WIDTH * self.scale_factor)
        self.scaled_height = Config.WIN_HEIGHT
        self.right_panel_start = self.scaled_width
        self.panel_margin = 30

        # Загрузка ассетов из папки graphics
        self.logo_img = self._load_asset(Config.LOGO_PATH)
        self.loading_img = self._load_asset(Config.LOADING_GIF_PATH)

    def _load_asset(self, path):
        if os.path.exists(path):
            try:
                return pygame.image.load(path).convert_alpha()
            except pygame.error:
                return None
        return None

    def draw_centered_image(self, image):
        self.screen.fill((0, 0, 0))
        if image:
            rect = image.get_rect(center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT // 2))
            self.screen.blit(image, rect)
        else:
            # Если файла нет, выводим текст ошибки
            err_text = self.font.render("ОШИБКА: ФАЙЛ НЕ НАЙДЕН", True, (255, 0, 0))
            self.screen.blit(err_text, err_text.get_rect(center=(Config.WIN_WIDTH // 2, Config.WIN_HEIGHT // 2)))

    def draw(self, frame, game, cur_pose, is_correct):
        # 1. Экраны заставки
        if game.state == "SPLASH":
            self.draw_centered_image(self.logo_img)
            return

        if game.state == "LOADING":
            self.draw_centered_image(self.loading_img)
            return

        # 2. Основная игра (если frame не пустой)
        if frame is not None:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            surf = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
            scaled_surf = pygame.transform.scale(surf, (self.scaled_width, self.scaled_height))
            self.screen.fill((10, 10, 10))
            self.screen.blit(scaled_surf, (0, 0))

        # Разделитель
        if self.scaled_width < Config.WIN_WIDTH:
            pygame.draw.line(self.screen, (255, 255, 255), (self.scaled_width, 0),
                             (self.scaled_width, Config.WIN_HEIGHT), 3)

        # Правая панель
        panel_rect = pygame.Rect(self.right_panel_start, 0, Config.WIN_WIDTH - self.right_panel_start,
                                 Config.WIN_HEIGHT)
        s = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.screen.blit(s, (panel_rect.x, panel_rect.y))
        pygame.draw.rect(self.screen, (255, 255, 255), panel_rect, 2)

        # Текст задания
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

        # Нижние элементы
        bottom_y = Config.WIN_HEIGHT - self.panel_margin
        self._draw_text("R / SPACE — рестарт", (180, 180, 180), is_small=True,
                        bottomright=(Config.WIN_WIDTH - self.panel_margin, bottom_y))

        pose_name = Config.POSE_NAMES_RU.get(cur_pose, "---")
        self._draw_text(f"Текущая: {pose_name}", (0, 255, 0), is_small=True,
                        bottomright=(Config.WIN_WIDTH - self.panel_margin, bottom_y - 40))

        # Шкала жизней
        rect_w, rect_h, gap = 20, 15, 5
        start_x = Config.WIN_WIDTH - self.panel_margin - (10 * rect_w + 9 * gap)
        for i in range(10):
            color = (0, 255, 0) if i < game.lives else (100, 100, 100)
            pygame.draw.rect(self.screen, color, (start_x + i * (rect_w + gap), bottom_y - 80, rect_w, rect_h))

        # Таймер и Счёт
        self._draw_text(f"Осталось: {game.time_left} сек", (255, 255, 255),
                        bottomright=(Config.WIN_WIDTH - self.panel_margin, bottom_y - 110))
        self._draw_text(f"Счёт: {game.score}", (255, 255, 255),
                        bottomright=(Config.WIN_WIDTH - self.panel_margin, bottom_y - 150))

        # Оверлей победы/поражения
        if game.state in ["WIN", "LOSE"]:
            overlay = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA);
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