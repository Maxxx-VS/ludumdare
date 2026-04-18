import pygame
import cv2
from config import Config

class UIRenderer:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.Font(None, 42)
        self.font_small = pygame.font.Font(None, 36)

        # Рассчет масштабов
        self.scale_factor = Config.WIN_HEIGHT / Config.CAM_HEIGHT
        self.scaled_width = int(Config.CAM_WIDTH * self.scale_factor)
        self.scaled_height = Config.WIN_HEIGHT

        self.right_panel_start = self.scaled_width
        self.panel_margin = 30

    def draw(self, frame, game, cur_pose, is_correct):
        # 1. Конвертация OpenCV кадра в Pygame Surface
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        surf = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
        scaled_surf = pygame.transform.scale(surf, (self.scaled_width, self.scaled_height))

        self.screen.fill((10, 10, 10))
        self.screen.blit(scaled_surf, (0, 0))

        # 2. Белая разделительная линия (если кадр не на весь экран)
        if self.scaled_width < Config.WIN_WIDTH:
            pygame.draw.line(self.screen, (255, 255, 255),
                             (self.scaled_width, 0), (self.scaled_width, Config.WIN_HEIGHT), 3)

        # 3. Полупрозрачный фон правой панели
        panel_rect = pygame.Rect(self.right_panel_start, 0,
                                 Config.WIN_WIDTH - self.right_panel_start, Config.WIN_HEIGHT)
        s = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.screen.blit(s, (panel_rect.x, panel_rect.y))
        pygame.draw.rect(self.screen, (255, 255, 255), panel_rect, 2)

        # 4. UI элементы
        self._draw_text("ЗАДАНИЕ", (220, 220, 220),
                        center=(self.right_panel_start + panel_rect.width // 2, self.panel_margin + 20))

        target_text = Config.POSE_NAMES_RU.get(game.target_pose, "???")
        self._draw_text(target_text, (255, 255, 0),
                        center=(self.right_panel_start + panel_rect.width // 2, self.panel_margin + 100))

        status_text = "ВЕРНО" if is_correct else "НЕВЕРНО"
        status_color = (0, 255, 0) if is_correct else (255, 80, 80)
        self._draw_text(status_text, status_color,
                        center=(self.right_panel_start + panel_rect.width // 2, self.panel_margin + 180))

        score_text = f"Счёт: {game.score}"
        self._draw_text(score_text, (255, 255, 255),
                        bottomright=(Config.WIN_WIDTH - self.panel_margin, Config.WIN_HEIGHT - self.panel_margin))

        pose_name = Config.POSE_NAMES_RU.get(cur_pose, "---")
        pose_color = (0, 255, 0) if cur_pose != "UNKNOWN" else (255, 100, 100)
        self._draw_text(f"Текущая: {pose_name}", pose_color, is_small=True,
                        bottomright=(Config.WIN_WIDTH - self.panel_margin, Config.WIN_HEIGHT - self.panel_margin - 50))

        self._draw_text("R / SPACE — новая поза", (180, 180, 180), is_small=True,
                        bottomright=(Config.WIN_WIDTH - self.panel_margin, Config.WIN_HEIGHT - self.panel_margin - 100))

    def _draw_text(self, text, color, center=None, bottomright=None, is_small=False):
        """Вспомогательный метод для удобной отрисовки текста."""
        font = self.font_small if is_small else self.font
        surf = font.render(text, True, color)
        rect = surf.get_rect()
        if center:
            rect.center = center
        if bottomright:
            rect.bottomright = bottomright
        self.screen.blit(surf, rect)