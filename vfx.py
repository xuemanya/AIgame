# vfx.py
import pygame
import random
import math
from config import Config


def draw_glow_circle(surface, color, center, radius, alpha=100):
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    pygame.draw.circle(s, (*color, alpha), (radius, radius), radius)
    surface.blit(s, (center[0] - radius, center[1] - radius), special_flags=pygame.BLEND_ADD)


class Camera:
    def __init__(self):
        self.offset_x = 0
        self.offset_y = 0
        self.shake_magnitude = 0

    def update(self, target):
        # 平滑跟随
        target_x = -target.rect.centerx + Config.SCREEN_WIDTH // 2
        target_y = -target.rect.centery + Config.SCREEN_HEIGHT // 2 + 50

        # 缓动效果
        self.offset_x += (target_x - self.offset_x) * 0.1
        self.offset_y += (target_y - self.offset_y) * 0.1

        # 屏幕震动
        if self.shake_magnitude > 0:
            shake_x = random.randint(-self.shake_magnitude, self.shake_magnitude)
            shake_y = random.randint(-self.shake_magnitude, self.shake_magnitude)
            self.offset_x += shake_x
            self.offset_y += shake_y
            self.shake_magnitude = int(self.shake_magnitude * 0.9)

    def shake(self, magnitude=10):
        self.shake_magnitude = magnitude

    def apply(self, entity):
        return entity.rect.move(self.offset_x, self.offset_y)

    def apply_rect(self, rect):
        return rect.move(self.offset_x, self.offset_y)

    def apply_coords(self, x, y):
        return (x + self.offset_x, y + self.offset_y)


class Trail:
    def __init__(self, rect, color, alpha=150, decay=10):
        self.rect = rect.copy()
        self.color = color
        self.alpha = alpha
        self.decay = decay

    def update(self):
        self.alpha -= self.decay

    def draw(self, surface, camera):
        if self.alpha > 0:
            s = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            s.fill((*self.color, int(self.alpha)))
            surface.blit(s, camera.apply_rect(self.rect), special_flags=pygame.BLEND_ADD)


class Particle:
    def __init__(self, x, y, color, vel, size=4, decay=0.2, gravity=0):
        self.x, self.y = x, y
        self.color = color
        self.vel = list(vel)
        self.size = size
        self.decay = decay
        self.gravity = gravity
        self.life = 255

    def update(self):
        self.x += self.vel[0]
        self.y += self.vel[1]
        self.vel[1] += self.gravity
        self.life -= self.decay * 20
        self.size = max(0, self.size - self.decay)

    def draw(self, surface, camera):
        if self.life > 0 and self.size > 0:
            pos = camera.apply_coords(self.x, self.y)
            s = pygame.Surface((int(self.size * 4), int(self.size * 4)), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, int(self.life)), (int(self.size * 2), int(self.size * 2)),
                               int(self.size))
            surface.blit(s, (pos[0] - self.size * 2, pos[1] - self.size * 2), special_flags=pygame.BLEND_ADD)


class FloatingText:
    def __init__(self, x, y, text, color):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.life = 60
        self.y_offset = 0

    def update(self):
        self.life -= 1
        self.y_offset -= 1

    def draw(self, surface, camera, font):
        if self.life > 0:
            alpha = min(255, self.life * 5)
            text_surf = font.render(str(self.text), True, self.color)
            text_surf.set_alpha(alpha)
            pos = camera.apply_coords(self.x, self.y + self.y_offset)
            surface.blit(text_surf, pos)


class SwordVFX:
    def __init__(self, rect, facing_right):
        self.rect = rect
        self.life = 10
        self.facing_right = facing_right

    def draw(self, surface, camera):
        self.life -= 1
        if self.life > 0:
            start_angle = -30 if self.facing_right else 150
            draw_pos = camera.apply_rect(self.rect)
            center = (draw_pos.left if self.facing_right else draw_pos.right, draw_pos.centery)
            radius = 80
            points = [center]
            steps = 5
            base_ang = -60 if self.facing_right else 120
            for i in range(steps + 1):
                ang = math.radians(base_ang + i * (120 / steps))
                x = center[0] + math.cos(ang) * radius
                y = center[1] + math.sin(ang) * radius
                points.append((x, y))

            if len(points) > 2:
                pygame.draw.polygon(surface, Config.COLORS['sword_arc'], points)
                pygame.draw.lines(surface, (255, 255, 255), False, points[1:], 3)