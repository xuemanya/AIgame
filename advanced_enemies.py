import pygame
import math
import random
from config import Config
from entities import Enemy
from vfx import Particle


class Projectile(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, speed, game, size=12, color=(255, 50, 50)):
        super().__init__()
        self.game = game
        self.image = pygame.Surface((size, size))
        self.image.fill(color)
        self.rect = self.image.get_rect(center=(x, y))
        self.vel_x = math.cos(angle) * speed
        self.vel_y = math.sin(angle) * speed
        self.timer = 180
        self.color = color

    def update(self):
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y
        self.timer -= 1

        if random.random() < 0.3:
            self.game.particles.append(Particle(self.rect.centerx, self.rect.centery, self.color, (0, 0), size=3))

        if self.timer <= 0:
            self.kill()

    def draw(self, surface, camera):
        surface.blit(self.image, camera.apply_rect(self.rect))


class Bat(Enemy):
    """飞行敌人：沿正弦波飞行"""

    def __init__(self, x, y, game):
        super().__init__(x, y, game)
        self.rect = pygame.Rect(x, y, 30, 30)
        self.start_y = y
        self.offset = random.random() * 100
        self.hp = 40
        self.speed = 3

    def update(self):
        self.rect.x -= self.speed
        self.rect.y = self.start_y + math.sin((pygame.time.get_ticks() / 200) + self.offset) * 60

        if self.rect.right < self.game.camera.offset_x - 200:
            self.die(silent=True)

    def draw(self, surface, camera):
        draw_rect = camera.apply_rect(self.rect)
        pygame.draw.circle(surface, (100, 0, 150), draw_rect.center, 15)
        wing_y = draw_rect.centery + math.sin(pygame.time.get_ticks() * 0.2) * 15
        pygame.draw.line(surface, (120, 20, 180), draw_rect.center, (draw_rect.left - 10, wing_y), 4)
        pygame.draw.line(surface, (120, 20, 180), draw_rect.center, (draw_rect.right + 10, wing_y), 4)

        # 简单血条
        if self.hp < 40:
            pygame.draw.rect(surface, (255, 0, 0), (draw_rect.x, draw_rect.y - 8, 30 * (self.hp / 40), 3))


class Drone(Enemy):
    """射击敌人：悬停并追踪玩家，发射子弹"""

    def __init__(self, x, y, game):
        super().__init__(x, y, game)
        self.rect = pygame.Rect(x, y, 40, 40)
        self.hp = 80
        self.hover_y = y
        self.shoot_timer = 0

    def update(self):
        target_x = self.game.player.rect.x + 300
        self.rect.x += (target_x - self.rect.x) * 0.02
        self.rect.y = self.hover_y + math.sin(pygame.time.get_ticks() * 0.005) * 15

        self.shoot_timer += 1
        dist = math.hypot(self.game.player.rect.centerx - self.rect.centerx,
                          self.game.player.rect.centery - self.rect.centery)
        if self.shoot_timer > 120 and dist < 700:
            self.shoot()
            self.shoot_timer = 0

        if self.rect.y > Config.SCREEN_HEIGHT + 200:
            self.die(silent=True)

    def shoot(self):
        dx = self.game.player.rect.centerx - self.rect.centerx
        dy = self.game.player.rect.centery - self.rect.centery
        angle = math.atan2(dy, dx)
        bullet = Projectile(self.rect.centerx, self.rect.centery, angle, 6, self.game)
        self.game.projectiles.add(bullet)
        self.rect.x += 5

    def draw(self, surface, camera):
        draw_rect = camera.apply_rect(self.rect)
        pygame.draw.rect(surface, (60, 60, 70), draw_rect, border_radius=5)
        pygame.draw.rect(surface, (0, 255, 255), draw_rect, 2, border_radius=5)

        if self.hp < 80:
            pygame.draw.rect(surface, (255, 0, 0), (draw_rect.x, draw_rect.y - 8, 40 * (self.hp / 80), 3))


class KamikazeBeetle(Enemy):
    """自爆甲虫：地面单位，发现玩家后加速冲锋"""

    def __init__(self, x, y, game):
        super().__init__(x, y, game)
        self.rect = pygame.Rect(x, y, 30, 20)
        self.hp = 30
        self.speed = 2
        self.aggro = False  # 是否激怒

    def update(self):
        self.apply_physics(self.game.platforms)

        dist = self.game.player.rect.centerx - self.rect.centerx

        # 简单的AI
        if abs(dist) < 300:  # 视野范围
            self.aggro = True

        if self.aggro:
            if dist > 0:
                self.vel.x = 6  # 快速冲锋
            else:
                self.vel.x = -6
        else:
            self.vel.x = -2  # 缓慢巡逻

        if self.rect.y > Config.SCREEN_HEIGHT + 200: self.die(silent=True)

    def draw(self, surface, camera):
        draw_rect = camera.apply_rect(self.rect)
        color = Config.COLORS['beetle']
        if self.aggro: color = (255, 100, 0)  # 激怒变色

        pygame.draw.ellipse(surface, color, draw_rect)
        # 触角
        start = (draw_rect.right if self.vel.x > 0 else draw_rect.left, draw_rect.centery)
        end = (start[0] + (10 if self.vel.x > 0 else -10), start[1] - 10)
        pygame.draw.line(surface, color, start, end, 2)


class Turret(Enemy):
    """炮塔：固定不动，定期发射激光"""

    def __init__(self, x, y, game):
        super().__init__(x, y, game)
        self.rect = pygame.Rect(x, y, 40, 40)
        self.hp = 60
        self.shoot_timer = random.randint(0, 100)

    def update(self):
        # 炮塔受重力影响，需要站在地上
        self.apply_physics(self.game.platforms)
        self.vel.x = 0  # 不移动

        self.shoot_timer += 1
        # 射速较慢
        if self.shoot_timer > 180:
            dist = self.game.player.rect.centerx - self.rect.centerx
            if abs(dist) < 800:
                self.shoot()
            self.shoot_timer = 0

    def shoot(self):
        dx = self.game.player.rect.centerx - self.rect.centerx
        dy = self.game.player.rect.centery - self.rect.centery
        angle = math.atan2(dy, dx)
        bullet = Projectile(self.rect.centerx, self.rect.top, angle, 8, self.game, size=15,
                            color=Config.COLORS['turret'])
        self.game.projectiles.add(bullet)

    def draw(self, surface, camera):
        draw_rect = camera.apply_rect(self.rect)
        pygame.draw.rect(surface, (80, 80, 80), draw_rect)
        # 炮管
        pygame.draw.circle(surface, Config.COLORS['turret'], draw_rect.midtop, 15)

        if self.hp < 60:
            pygame.draw.rect(surface, (255, 0, 0), (draw_rect.x, draw_rect.y - 8, 40 * (self.hp / 60), 3))