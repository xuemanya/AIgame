import pygame
import math
import random
from config import Config
from vfx import Particle


class ProjectileBase(pygame.sprite.Sprite):
    """投射物基类，处理伤害和穿透"""

    def __init__(self, x, y, image_surf, damage):
        super().__init__()
        self.image = image_surf
        self.rect = self.image.get_rect(center=(x, y))
        self.damage = damage
        self.hit_list = []  # 记录已攻击过的敌人，防止穿透时每帧都造成伤害
        self.penetrate = False  # 是否穿透


class PlayerArrow(ProjectileBase):
    def __init__(self, x, y, facing_right, game):
        surf = pygame.Surface((20, 4))
        surf.fill(Config.COLORS['arrow'])
        super().__init__(x, y, surf, 35)  # 伤害 35
        self.game = game
        self.speed = 18 if facing_right else -18
        self.timer = 120
        self.penetrate = False

    def update(self):
        self.rect.x += self.speed
        self.timer -= 1
        if random.random() < 0.5:
            self.game.particles.append(
                Particle(self.rect.centerx, self.rect.centery, Config.COLORS['arrow'], (0, 0), size=2))
        if self.timer <= 0:
            self.kill()

    def draw(self, surface, camera):
        surface.blit(self.image, camera.apply_rect(self.rect))


class PlayerLaser(ProjectileBase):
    """激光束"""

    def __init__(self, x, y, facing_right, game):
        surf = pygame.Surface((40, 6))
        surf.fill(Config.COLORS['laser_beam'])
        super().__init__(x, y, surf, 15)  # 单次伤害较低，但频射高
        self.game = game
        self.speed = 30 if facing_right else -30
        self.timer = 60
        self.penetrate = True  # 激光穿透

    def update(self):
        self.rect.x += self.speed
        self.timer -= 1
        self.game.particles.append(
            Particle(self.rect.centerx, self.rect.centery, Config.COLORS['laser_beam'], (0, 0), size=4, decay=0.3))
        if self.timer <= 0:
            self.kill()

    def draw(self, surface, camera):
        draw_rect = camera.apply_rect(self.rect)
        glow = pygame.Surface((60, 16), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*Config.COLORS['laser_beam'], 100), (0, 0, 60, 16), border_radius=8)
        surface.blit(glow, (draw_rect.centerx - 30, draw_rect.centery - 8), special_flags=pygame.BLEND_ADD)
        surface.blit(self.image, draw_rect)


class PlayerBoomerang(ProjectileBase):
    """回旋镖：加强版"""

    def __init__(self, x, y, facing_right, game):
        # 绘制一个V型图标作为基础
        surf = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.lines(surf, Config.COLORS['weapon_boomerang'], False, [(5, 5), (15, 25), (25, 5)], 5)

        super().__init__(x, y, surf, 45)  # 伤害 45
        self.game = game
        self.speed = 22 if facing_right else -22  # 初始速度更快
        self.acc = -0.8 if facing_right else 0.8  # 减速更快
        self.timer = 300
        self.rotation = 0
        self.penetrate = True  # 核心加强：无限穿透！
        self.returning = False
        self.base_image = surf  # 保存原始图像用于旋转

    def update(self):
        self.rect.x += self.speed
        self.speed += self.acc
        self.timer -= 1

        # 旋转效果
        self.rotation = (self.rotation + 30) % 360
        self.image = pygame.transform.rotate(self.base_image, self.rotation)
        self.rect = self.image.get_rect(center=self.rect.center)

        # 状态判断
        if (self.acc < 0 and self.speed < 0) or (self.acc > 0 and self.speed > 0):
            self.returning = True
            # 回来的时候重置打击列表，可以对同一敌人造成二次伤害！
            if len(self.hit_list) > 0:
                self.hit_list = []

        if self.returning:
            # 追踪玩家
            dx = self.game.player.rect.centerx - self.rect.centerx
            dy = self.game.player.rect.centery - self.rect.centery
            self.rect.x += dx * 0.1
            self.rect.y += dy * 0.1

            if self.rect.colliderect(self.game.player.rect):
                self.kill()

        if self.timer <= 0:
            self.kill()

    def draw(self, surface, camera):
        surface.blit(self.image, camera.apply_rect(self.rect))


class SoundWave(ProjectileBase):
    """音波：全屏扩散"""

    def __init__(self, x, y, game):
        surf = pygame.Surface((10, 10), pygame.SRCALPHA)  # 初始大小无关紧要，动态绘制
        super().__init__(x, y, surf, 20)  # 伤害 20 (多段)
        self.game = game
        self.radius = 10
        self.max_radius = 250  # 超大范围
        self.expansion_speed = 15
        self.penetrate = True
        self.life = 20

    def update(self):
        self.radius += self.expansion_speed
        self.life -= 1

        # 更新碰撞矩形
        self.rect = pygame.Rect(0, 0, self.radius * 2, self.radius * 2)
        self.rect.center = (self.game.player.rect.centerx, self.game.player.rect.centery)

        if self.life <= 0:
            self.kill()

    def draw(self, surface, camera):
        # 绘制扩散的圆环
        draw_center = camera.apply_coords(self.rect.centerx, self.rect.centery)

        # 多层光环
        for i in range(3):
            r = self.radius - i * 20
            if r > 0:
                alpha = int(255 * (self.life / 20))
                color = (*Config.COLORS['sound_wave'], alpha)

                # 必须创建一个带alpha的surface来画半透明圆
                s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, color, (r, r), r, 4)
                surface.blit(s, (draw_center[0] - r, draw_center[1] - r), special_flags=pygame.BLEND_ADD)


class WeaponItem(pygame.sprite.Sprite):
    """地上的武器掉落物"""

    def __init__(self, x, y, weapon_type):
        super().__init__()
        self.weapon_type = weapon_type
        self.rect = pygame.Rect(x, y, 30, 30)
        self.start_y = y
        self.float_offset = random.random() * 100

        self.color = (200, 200, 200)
        if self.weapon_type == "axe":
            self.color = Config.COLORS['weapon_axe']
        elif self.weapon_type == "bow":
            self.color = Config.COLORS['weapon_bow']
        elif self.weapon_type == "laser":
            self.color = Config.COLORS['weapon_laser']
        elif self.weapon_type == "hammer":
            self.color = Config.COLORS['weapon_hammer']
        elif self.weapon_type == "boomerang":
            self.color = Config.COLORS['weapon_boomerang']
        elif self.weapon_type == "guitar":
            self.color = Config.COLORS['weapon_guitar']

    def update(self):
        self.rect.y = self.start_y + math.sin((pygame.time.get_ticks() * 0.005) + self.float_offset) * 5

    def draw(self, surface, camera):
        draw_rect = camera.apply_rect(self.rect)
        s = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, 50), (20, 20), 18)
        surface.blit(s, (draw_rect.centerx - 20, draw_rect.centery - 20), special_flags=pygame.BLEND_ADD)

        if self.weapon_type == "axe":
            pygame.draw.rect(surface, self.color, draw_rect, border_radius=5)
            pygame.draw.line(surface, (255, 255, 255), draw_rect.topleft, draw_rect.bottomright, 3)
        elif self.weapon_type == "bow":
            pygame.draw.arc(surface, self.color, draw_rect, 0, 3.14, 3)
            pygame.draw.line(surface, (255, 255, 255), (draw_rect.left, draw_rect.centery),
                             (draw_rect.right, draw_rect.centery), 2)
        elif self.weapon_type == "laser":
            pygame.draw.rect(surface, self.color, (draw_rect.x, draw_rect.y + 10, 30, 10))
            pygame.draw.rect(surface, (255, 255, 255), (draw_rect.x + 5, draw_rect.y + 10, 20, 3))
        elif self.weapon_type == "hammer":
            pygame.draw.rect(surface, self.color, (draw_rect.x + 5, draw_rect.y, 20, 15))
            pygame.draw.line(surface, (200, 200, 200), (draw_rect.centerx, draw_rect.y + 15),
                             (draw_rect.centerx, draw_rect.bottom), 4)
        elif self.weapon_type == "boomerang":
            # V 形
            pygame.draw.lines(surface, self.color, False, [draw_rect.topleft, draw_rect.midbottom, draw_rect.topright],
                              4)
        elif self.weapon_type == "guitar":
            # 吉他形状 (简化)
            pygame.draw.circle(surface, self.color, (draw_rect.centerx, draw_rect.bottom - 5), 8)
            pygame.draw.line(surface, self.color, (draw_rect.centerx, draw_rect.bottom - 5),
                             (draw_rect.centerx + 10, draw_rect.top), 4)


class ShieldItem(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.rect = pygame.Rect(x, y, 25, 25)
        self.start_y = y
        self.color = Config.COLORS['shield']

    def update(self):
        self.rect.y = self.start_y + math.sin(pygame.time.get_ticks() * 0.008) * 5

    def draw(self, surface, camera):
        draw_rect = camera.apply_rect(self.rect)
        pygame.draw.circle(surface, self.color, draw_rect.center, 12, 3)
        pygame.draw.circle(surface, self.color, draw_rect.center, 6)