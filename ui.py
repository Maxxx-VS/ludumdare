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

        # 4. Верхние UI элементы
        self._draw_text("ЗАДАНИЕ", (220, 220, 220),
                        center=(self.right_panel_start + panel_rect.width // 2, self.panel_margin + 20))

        target_text = Config.POSE_NAMES_RU.get(game.target_pose, "???")
        self._draw_text(target_text, (255, 255, 0),
                        center=(self.right_panel_start + panel_rect.width // 2, self.panel_margin + 100))

        status_text = "ВЕРНО" if is_correct else "НЕВЕРНО"
        status_color = (0, 255, 0) if is_correct else (255, 80, 80)
        self._draw_text(status_text, status_color,
                        center=(self.right_panel_start + panel_rect.width // 2, self.panel_margin + 180))

        # 5. ИЗМЕНЕНО: Нижние UI элементы (выровнены, добавлены жизни и таймер)
        bottom_y = Config.WIN_HEIGHT - self.panel_margin

        self._draw_text("R / SPACE — рестарт", (180, 180, 180), is_small=True,
                        bottomright=(Config.WIN_WIDTH - self.panel_margin, bottom_y))

        pose_name = Config.POSE_NAMES_RU.get(cur_pose, "---")
        pose_color = (0, 255, 0) if cur_pose != "UNKNOWN" else (255, 100, 100)
        self._draw_text(f"Текущая: {pose_name}", pose_color, is_small=True,
                        bottomright=(Config.WIN_WIDTH - self.panel_margin, bottom_y - 40))

        # НОВОЕ: Отрисовка жизней (10 прямоугольников)
        rect_w = 20
        rect_h = 15
        gap = 5
        total_w = 10 * rect_w + 9 * gap
        start_x = Config.WIN_WIDTH - self.panel_margin - total_w
        start_y = bottom_y - 80

        for i in range(10):
            # Зеленый, если жизнь есть, серый если потрачена
            color = (0, 255, 0) if i < game.lives else (100, 100, 100)
            pygame.draw.rect(self.screen, color, (start_x + i * (rect_w + gap), start_y, rect_w, rect_h))

        # НОВОЕ: Отрисовка 30-секундного таймера
        timer_text = f"Осталось: {game.time_left} сек"
        timer_color = (255, 255, 255) if game.time_left > 10 else (255, 100, 100) # Краснеет к концу
        self._draw_text(timer_text, timer_color,
                        bottomright=(Config.WIN_WIDTH - self.panel_margin, bottom_y - 110))

        # Счёт
        score_text = f"Счёт: {game.score}"
        self._draw_text(score_text, (255, 255, 255),
                        bottomright=(Config.WIN_WIDTH - self.panel_margin, bottom_y - 150))

        # 6. НОВОЕ: Оверлей статуса завершения игры (Победа / Поражение)
        if game.state in ["WIN", "LOSE"]:
            overlay = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
            overlay_color = (0, 50, 0, 200) if game.state == "WIN" else (50, 0, 0, 200)
            overlay.fill(overlay_color)
            self.screen.blit(overlay, (panel_rect.x, panel_rect.y))

            text = "ПОБЕДА!" if game.state == "WIN" else "ИГРА ОКОНЧЕНА"
            text_color = (0, 255, 0) if game.state == "WIN" else (255, 50, 50)
            self._draw_text(text, text_color, center=(self.right_panel_start + panel_rect.width // 2, Config.WIN_HEIGHT // 2))

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