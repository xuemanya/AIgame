import pygame
import math
import random
from config import Config
from entities import Enemy
from advanced_enemies import Projectile
from vfx import Particle, FloatingText  # 修复：补充导入 FloatingText


class BossBase(Enemy):
    """Boss 基类，处理通用的血条显示和状态"""

    def __init__(self, x, y, game, name, max_hp, color):
        super().__init__(x, y, game)
        self.name = name
        self.max_hp = max_hp
        self.hp = max_hp
        self.color = color
        self.state = "IDLE"
        self.timer = 0
        self.start_y = y

    def draw_health_bar(self, surface, camera):
        # 绘制在 Boss 头顶的血条
        draw_rect = camera.apply_rect(self.rect)
        bar_w = 200
        bar_h = 15
        bar_x = draw_rect.centerx - bar_w // 2
        bar_y = draw_rect.top - 30

        hp_ratio = max(0, self.hp / self.max_hp)

        pygame.draw.rect(surface, (50, 0, 0), (bar_x, bar_y, bar_w, bar_h), border_radius=5)
        pygame.draw.rect(surface, self.color, (bar_x, bar_y, bar_w * hp_ratio, bar_h), border_radius=5)
        pygame.draw.rect(surface, (255, 255, 255), (bar_x, bar_y, bar_w, bar_h), 2, border_radius=5)

        # 名字
        name_surf = self.game.font.render(self.name, True, (255, 255, 255))
        surface.blit(name_surf, (bar_x, bar_y - 25))


class FloatingFortress(BossBase):
    """Boss 1: 浮空要塞 - 发射追踪弹幕"""

    def __init__(self, x, y, game):
        super().__init__(x, y, game, "FLOATING FORTRESS", 1200, Config.COLORS['boss_body'])
        self.rect = pygame.Rect(x, y, 120, 120)
        self.hover_offset = 0

    def update(self):
        self.timer += 1
        self.hover_offset += 0.05

        # 1. 悬浮移动 (正弦波)
        target_y = self.start_y + math.sin(self.hover_offset) * 80
        self.rect.y += (target_y - self.rect.y) * 0.05

        # 2. 水平追踪
        target_x = self.game.player.rect.centerx
        if self.rect.centerx < target_x - 300:
            self.rect.x += 2
        elif self.rect.centerx > target_x + 300:
            self.rect.x -= 2

        # 3. 攻击模式
        # 每 120 帧发射一波环形子弹
        if self.timer % 120 == 0:
            self.fire_ring()

        # 每 250 帧发射一次狙击
        if self.timer % 250 == 0:
            self.fire_sniper()

    def fire_ring(self):
        for i in range(0, 360, 45):
            rad = math.radians(i)
            # 速度较慢的铺场弹幕
            p = Projectile(self.rect.centerx, self.rect.centery, rad, 4, self.game)
            self.game.projectiles.add(p)

    def fire_sniper(self):
        dx = self.game.player.rect.centerx - self.rect.centerx
        dy = self.game.player.rect.centery - self.rect.centery
        angle = math.atan2(dy, dx)
        # 快速狙击弹
        p = Projectile(self.rect.centerx, self.rect.centery, angle, 10, self.game)
        p.image.fill((255, 255, 0))  # 黄色高亮
        self.game.projectiles.add(p)

    def draw(self, surface, camera):
        draw_rect = camera.apply_rect(self.rect)
        pygame.draw.rect(surface, self.color, draw_rect, border_radius=15)
        # 核心
        core_color = (255, 50, 50) if self.timer % 60 < 30 else (100, 0, 0)
        pygame.draw.circle(surface, core_color, draw_rect.center, 30)
        pygame.draw.rect(surface, (50, 50, 60), draw_rect, 5, border_radius=15)
        self.draw_health_bar(surface, camera)


class ShadowWalker(BossBase):
    """Boss 2: 暗影行者 - 地面单位，冲刺攻击"""

    def __init__(self, x, y, game):
        super().__init__(x, y, game, "SHADOW WALKER", 1000, Config.COLORS['shadow_boss'])
        self.rect = pygame.Rect(x, y, 60, 90)  # 人形，较高
        self.vel.x = 0
        self.dash_timer = 0

    def update(self):
        # 物理重置：防止加速度累积导致瞬移
        self.acc = pygame.math.Vector2(0, 0)

        self.apply_physics(self.game.platforms)
        self.dash_timer += 1

        dist = self.game.player.rect.centerx - self.rect.centerx

        # 简单的状态机
        if self.state == "IDLE":
            # 缓慢走向玩家
            if abs(dist) > 100:
                self.vel.x = 2 if dist > 0 else -2
            else:
                self.vel.x = 0

            # 准备冲刺
            if self.dash_timer > 180:
                self.state = "CHARGE"
                self.dash_timer = 0
                # 提示文字 (之前这里报错了)
                self.game.floating_texts.append(FloatingText(self.rect.centerx, self.rect.top - 20, "!", (255, 0, 0)))

        elif self.state == "CHARGE":
            self.vel.x = 0
            # 蓄力 1 秒后冲刺
            if self.dash_timer > 60:
                self.state = "DASHING"
                self.dash_timer = 0
                direction = 1 if dist > 0 else -1
                self.vel.x = direction * 15  # 极快速度

        elif self.state == "DASHING":
            # 产生残影
            if random.random() < 0.8:
                self.game.particles.append(Particle(self.rect.centerx, self.rect.bottom, self.color, (0, 0), size=10))

            # 冲刺持续 20 帧
            if self.dash_timer > 20:
                self.state = "IDLE"
                self.dash_timer = 0
                self.vel.x = 0

    def draw(self, surface, camera):
        draw_rect = camera.apply_rect(self.rect)
        color = self.color
        if self.state == "CHARGE": color = (255, 255, 255)  # 蓄力变白

        pygame.draw.rect(surface, color, draw_rect)
        # 眼睛
        eye_x = draw_rect.right - 10 if self.game.player.rect.centerx > self.rect.centerx else draw_rect.left + 5
        pygame.draw.rect(surface, (0, 255, 0), (eye_x, draw_rect.y + 20, 5, 5))

        self.draw_health_bar(surface, camera)


class InfernoBomber(BossBase):
    """Boss 3: 地狱轰炸机 - 在顶部飞行并投掷炸弹"""

    def __init__(self, x, y, game):
        super().__init__(x, y, game, "INFERNO BOMBER", 800, Config.COLORS['bomber_boss'])
        self.rect = pygame.Rect(x, y - 200, 100, 60)  # 扁平形状
        self.bomb_timer = 0

    def update(self):
        # 在玩家头顶盘旋
        target_x = self.game.player.rect.centerx
        self.rect.x += (target_x - self.rect.x) * 0.03
        # 保持高度
        self.rect.y = self.start_y - 250 + math.sin(pygame.time.get_ticks() * 0.01) * 30

        self.bomb_timer += 1
        if self.bomb_timer > 60:  # 每秒投弹
            self.drop_bomb()
            self.bomb_timer = 0

    def drop_bomb(self):
        # 投掷炸弹
        bomb = Projectile(self.rect.centerx, self.rect.bottom, math.pi / 2, 2, self.game)
        bomb.image.fill((255, 100, 0))
        bomb.rect.width = 20
        bomb.rect.height = 20
        bomb.timer = 300
        # 赋予初始向下速度
        bomb.vel_y = 5
        self.game.projectiles.add(bomb)

    def draw(self, surface, camera):
        draw_rect = camera.apply_rect(self.rect)
        pygame.draw.ellipse(surface, self.color, draw_rect)
        pygame.draw.line(surface, (200, 200, 200), (draw_rect.centerx, draw_rect.top),
                         (draw_rect.centerx, draw_rect.top - 20), 5)  # 螺旋桨
        pygame.draw.line(surface, (200, 200, 200), (draw_rect.centerx - 20, draw_rect.top - 20),
                         (draw_rect.centerx + 20, draw_rect.top - 20), 2)
        self.draw_health_bar(surface, camera)