import pygame
import random
import math
from config import Config
from vfx import Particle, Trail, FloatingText, draw_glow_circle
from weapons import PlayerArrow, PlayerLaser, PlayerBoomerang


class PhysicsEntity(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.rect = pygame.Rect(x, y, w, h)
        self.vel = pygame.math.Vector2(0, 0)
        self.acc = pygame.math.Vector2(0, 0)
        self.on_ground = False
        self.facing_right = True

    def apply_physics(self, platforms):
        self.acc.y = Config.GRAVITY
        self.acc.x += self.vel.x * Config.FRICTION
        self.vel += self.acc
        if abs(self.vel.x) < 0.1: self.vel.x = 0

        self.rect.x += self.vel.x + 0.5 * self.acc.x
        hits = pygame.sprite.spritecollide(self, platforms, False)
        for p in hits:
            if self.vel.x > 0:
                self.rect.right = p.rect.left
            elif self.vel.x < 0:
                self.rect.left = p.rect.right
            self.vel.x = 0

        self.rect.y += self.vel.y + 0.5 * self.acc.y
        self.on_ground = False
        hits = pygame.sprite.spritecollide(self, platforms, False)
        for p in hits:
            if self.vel.y > 0:
                self.rect.bottom = p.rect.top
                self.vel.y = 0
                self.on_ground = True
            elif self.vel.y < 0:
                self.rect.top = p.rect.bottom
                self.vel.y = 0


class Player(PhysicsEntity):
    def __init__(self, x, y, game):
        super().__init__(x, y, 30, 50)
        self.game = game
        self.color = Config.COLORS['player']
        self.trails = []
        self.scarf_points = []
        for i in range(5): self.scarf_points.append([x, y])

        self.max_hp = 100
        self.hp = self.max_hp
        self.score = 0
        self.attack_cooldown = 0
        self.squash_factor = 1.0
        self.invincible_timer = 0

        self.weapon = "sword"
        self.shield_durability = 0
        self.max_jumps = 1
        self.jumps_left = 0
        self.speed_mult = 1.0
        self.damage_mult = 1.0

    def update(self):
        self.acc = pygame.math.Vector2(0, 0)
        keys = pygame.key.get_pressed()

        base_acc = Config.PLAYER_ACC * self.speed_mult
        # 拿重型武器时移动变慢
        if self.weapon in ["axe", "hammer"]: base_acc *= 0.8

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.acc.x = -base_acc
            self.facing_right = False
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.acc.x = base_acc
            self.facing_right = True

        if keys[pygame.K_j] and self.attack_cooldown == 0:
            self.attack()

        head_pos = (self.rect.centerx, self.rect.top + 10)
        self.scarf_points[0] = list(head_pos)
        for i in range(1, len(self.scarf_points)):
            prev = self.scarf_points[i - 1]
            curr = self.scarf_points[i]
            target_x = prev[0] - (20 if self.facing_right else -20)
            target_y = prev[1] + (self.vel.y * 0.5) + math.sin(pygame.time.get_ticks() * 0.01) * 2
            curr[0] += (target_x - curr[0]) * 0.2
            curr[1] += (target_y - curr[1]) * 0.2

        self.apply_physics(self.game.platforms)

        if self.on_ground:
            self.jumps_left = self.max_jumps

        self.squash_factor += (1.0 - self.squash_factor) * 0.1

        if abs(self.vel.x) > 3:
            if pygame.time.get_ticks() % 5 == 0:
                trail_color = Config.COLORS['player_scarf']
                if self.weapon == "axe":
                    trail_color = Config.COLORS['weapon_axe']
                elif self.weapon == "hammer":
                    trail_color = Config.COLORS['weapon_hammer']
                elif self.weapon == "laser":
                    trail_color = Config.COLORS['weapon_laser']
                elif self.weapon == "boomerang":
                    trail_color = Config.COLORS['weapon_boomerang']
                elif self.weapon == "guitar":
                    trail_color = Config.COLORS['weapon_guitar']
                self.trails.append(Trail(self.rect, trail_color, 100))

        if self.attack_cooldown > 0: self.attack_cooldown -= 1
        if self.invincible_timer > 0: self.invincible_timer -= 1

        for t in self.trails: t.update()
        self.trails = [t for t in self.trails if t.alpha > 0]

        if self.rect.y > Config.SCREEN_HEIGHT + 500:
            self.hp = 0

    def jump(self):
        if self.jumps_left > 0:
            self.vel.y = Config.PLAYER_JUMP
            self.jumps_left -= 1
            self.squash_factor = 0.6
            for _ in range(5):
                self.game.particles.append(
                    Particle(self.rect.centerx, self.rect.bottom, (200, 200, 200), (random.uniform(-2, 2), -1)))
            if self.jumps_left < self.max_jumps - 1:
                self.game.particles.append(
                    Particle(self.rect.centerx, self.rect.bottom, (100, 255, 255), (0, 0), size=6))
            return True
        return False

    def attack(self):
        dmg_mult = self.damage_mult

        if self.weapon == "sword":
            self.attack_cooldown = 20
            self.game.camera.shake(3)
            attack_rect = pygame.Rect(0, 0, 80, 60)
            if self.facing_right:
                attack_rect.midleft = self.rect.midright
            else:
                attack_rect.midright = self.rect.midleft
            self.game.add_sword_vfx(attack_rect, self.facing_right)
            self.check_melee_hit(attack_rect, int(25 * dmg_mult), int(40 * dmg_mult))

        elif self.weapon == "axe":
            self.attack_cooldown = 45
            self.game.camera.shake(6)
            attack_rect = pygame.Rect(0, 0, 100, 80)
            if self.facing_right:
                attack_rect.midleft = self.rect.midright
            else:
                attack_rect.midright = self.rect.midleft
            self.game.add_sword_vfx(attack_rect, self.facing_right)
            self.check_melee_hit(attack_rect, int(60 * dmg_mult), int(90 * dmg_mult))

        elif self.weapon == "bow":
            self.attack_cooldown = 10
            arrow = PlayerArrow(self.rect.centerx, self.rect.centery, self.facing_right, self.game)
            self.game.player_projectiles.add(arrow)
            self.vel.x = -3 if self.facing_right else 3

        elif self.weapon == "laser":
            self.attack_cooldown = 6
            self.game.camera.shake(2)
            laser = PlayerLaser(self.rect.centerx, self.rect.centery, self.facing_right, self.game)
            self.game.player_projectiles.add(laser)
            self.vel.x = -1 if self.facing_right else 1

        elif self.weapon == "hammer":
            self.attack_cooldown = 80
            self.game.camera.shake(15)
            attack_rect = pygame.Rect(0, 0, 160, 120)
            attack_rect.center = self.rect.center
            for _ in range(10):
                self.game.particles.append(
                    Particle(attack_rect.centerx, attack_rect.bottom, Config.COLORS['weapon_hammer'],
                             (random.uniform(-10, 10), random.uniform(-5, -1)), size=5, decay=0.1))
            self.check_melee_hit(attack_rect, int(80 * dmg_mult), int(120 * dmg_mult))

        elif self.weapon == "boomerang":
            self.attack_cooldown = 40
            boomerang = PlayerBoomerang(self.rect.centerx, self.rect.centery, self.facing_right, self.game)
            self.game.player_projectiles.add(boomerang)
            self.game.camera.shake(3)

        elif self.weapon == "guitar":
            self.attack_cooldown = 45
            self.game.camera.shake(5)
            # 全方位音波攻击
            attack_radius = 120
            attack_rect = pygame.Rect(0, 0, attack_radius * 2, attack_radius * 2)
            attack_rect.center = self.rect.center

            # 音波特效
            for _ in range(3):
                self.game.particles.append(Particle(self.rect.centerx, self.rect.centery, Config.COLORS['sound_wave'],
                                                    (random.uniform(-5, 5), random.uniform(-5, 5)), size=8, decay=0.1))

            # 绘制扩散圆圈特效 (逻辑在 main.py 或 vfx 系统中更佳，这里简化为粒子)

            hits = [e for e in self.game.enemies if attack_rect.colliderect(e.rect)]
            for enemy in hits:
                dmg = int(35 * dmg_mult)
                enemy.take_damage(dmg)
                # 击退效果
                direction = 1 if enemy.rect.centerx > self.rect.centerx else -1
                enemy.vel.x = direction * 10
                enemy.vel.y = -5

    def check_melee_hit(self, attack_rect, min_dmg, max_dmg):
        hits = [e for e in self.game.enemies if attack_rect.colliderect(e.rect)]
        if hits:
            self.game.hit_stop = Config.HIT_STOP_DURATION
            if self.weapon == "hammer": self.game.hit_stop = 10

        for enemy in hits:
            dmg = random.randint(min_dmg, max_dmg)
            enemy.take_damage(dmg)
            for _ in range(8):
                self.game.particles.append(Particle(enemy.rect.centerx, enemy.rect.centery, Config.COLORS['enemy_eye'],
                                                    (random.uniform(-4, 4), random.uniform(-4, 4)), gravity=0.2))

    def take_damage(self, amount):
        if self.invincible_timer == 0:
            if self.shield_durability > 0:
                self.shield_durability -= 1
                self.invincible_timer = 40
                self.game.floating_texts.append(
                    FloatingText(self.rect.centerx, self.rect.top, "BLOCKED", Config.COLORS['shield']))
                self.game.camera.shake(5)
                self.vel.y = -5
                self.vel.x = -8 if self.facing_right else 8
                return

            self.hp -= amount
            self.invincible_timer = 60
            self.game.camera.shake(10)
            self.vel.y = -8
            self.vel.x = -8 if self.facing_right else 8
            self.game.floating_texts.append(FloatingText(self.rect.centerx, self.rect.top, f"-{amount}", (255, 50, 50)))

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)
        self.game.floating_texts.append(FloatingText(self.rect.centerx, self.rect.top, f"+{amount}", (0, 255, 100)))

    def equip_weapon(self, w_type):
        self.weapon = w_type
        text = "SWORD"
        color = (255, 255, 255)
        if w_type == "axe":
            text = "HEAVY AXE"
            color = Config.COLORS['weapon_axe']
        elif w_type == "bow":
            text = "RAPID BOW"
            color = Config.COLORS['weapon_bow']
        elif w_type == "laser":
            text = "LASER RIFLE"
            color = Config.COLORS['weapon_laser']
        elif w_type == "hammer":
            text = "THUNDER HAMMER"
            color = Config.COLORS['weapon_hammer']
        elif w_type == "boomerang":
            text = "BOOMERANG"
            color = Config.COLORS['weapon_boomerang']
        elif w_type == "guitar":
            text = "ROCK GUITAR"
            color = Config.COLORS['weapon_guitar']

        self.game.floating_texts.append(FloatingText(self.rect.centerx, self.rect.top - 20, f"EQUIP: {text}", color))

    def add_shield(self):
        self.shield_durability = 3
        self.game.floating_texts.append(
            FloatingText(self.rect.centerx, self.rect.top - 20, "SHIELD MAX", Config.COLORS['shield']))

    def draw(self, surface, camera):
        for t in self.trails: t.draw(surface, camera)

        scarf_color = Config.COLORS['player_scarf']
        if self.weapon == "axe":
            scarf_color = Config.COLORS['weapon_axe']
        elif self.weapon == "bow":
            scarf_color = Config.COLORS['weapon_bow']
        elif self.weapon == "laser":
            scarf_color = Config.COLORS['weapon_laser']
        elif self.weapon == "hammer":
            scarf_color = Config.COLORS['weapon_hammer']
        elif self.weapon == "boomerang":
            scarf_color = Config.COLORS['weapon_boomerang']
        elif self.weapon == "guitar":
            scarf_color = Config.COLORS['weapon_guitar']

        points = [camera.apply_coords(*p) for p in self.scarf_points]
        if len(points) > 1:
            pygame.draw.lines(surface, scarf_color, False, points, 4)

        draw_rect = camera.apply_rect(self.rect)
        w = self.rect.width * (2 - self.squash_factor)
        h = self.rect.height * self.squash_factor
        draw_x = draw_rect.centerx - w / 2
        draw_y = draw_rect.y + (self.rect.height - h)

        if self.invincible_timer > 0 and (pygame.time.get_ticks() // 100) % 2 == 0:
            pass
        else:
            if self.shield_durability > 0:
                shield_radius = 40
                s_surf = pygame.Surface((shield_radius * 2, shield_radius * 2), pygame.SRCALPHA)
                alpha = 100 + self.shield_durability * 40
                pygame.draw.circle(s_surf, (*Config.COLORS['shield_aura'], alpha), (shield_radius, shield_radius),
                                   shield_radius, 2)
                surface.blit(s_surf, (draw_rect.centerx - shield_radius, draw_rect.centery - shield_radius),
                             special_flags=pygame.BLEND_ADD)

            glow_surf = pygame.Surface((w + 20, h + 20), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (*scarf_color, 50), (10, 10, w, h), border_radius=4)
            surface.blit(glow_surf, (draw_x - 10, draw_y - 10), special_flags=pygame.BLEND_ADD)
            pygame.draw.rect(surface, self.color, (draw_x, draw_y, w, h), border_radius=4)
            eye_offset = 6 if self.facing_right else -6
            pygame.draw.circle(surface, (0, 0, 0), (draw_rect.centerx + eye_offset, draw_rect.top + 15), 3)


class Enemy(PhysicsEntity):
    def __init__(self, x, y, game):
        super().__init__(x, y, 40, 40)
        self.game = game
        self.hp = 100
        self.patrol_center = x
        self.speed = 2

    def update(self):
        if self.rect.x > self.patrol_center + 100:
            self.vel.x = -self.speed
        elif self.rect.x < self.patrol_center - 100:
            self.vel.x = self.speed
        if self.vel.x == 0: self.vel.x = self.speed
        self.apply_physics(self.game.platforms)
        if self.rect.y > Config.SCREEN_HEIGHT + 200: self.die(silent=True)

    def take_damage(self, amount):
        self.hp -= amount
        self.game.floating_texts.append(
            FloatingText(self.rect.centerx, self.rect.top, str(amount), Config.COLORS['damage_text']))
        if self.hp <= 0: self.die()

    def die(self, silent=False):
        if not silent:
            for _ in range(15):
                self.game.particles.append(Particle(self.rect.centerx, self.rect.centery, Config.COLORS['enemy'],
                                                    (random.uniform(-5, 5), random.uniform(-5, -2)), size=6,
                                                    gravity=0.5))
        if self in self.game.enemies: self.game.enemies.remove(self)

    def draw(self, surface, camera):
        draw_rect = camera.apply_rect(self.rect)
        pygame.draw.rect(surface, Config.COLORS['enemy'], draw_rect)
        pygame.draw.rect(surface, (100, 0, 0), draw_rect, 2)
        eye_glow = int(150 + math.sin(pygame.time.get_ticks() * 0.01) * 100)
        draw_glow_circle(surface, Config.COLORS['enemy_eye'], draw_rect.center, 8, eye_glow)
        pygame.draw.circle(surface, (255, 255, 255), draw_rect.center, 3)
        if self.hp < 100:
            hp_w = (self.hp / 100) * self.rect.width
            pygame.draw.rect(surface, (50, 0, 0), (draw_rect.x, draw_rect.y - 10, self.rect.width, 4))
            pygame.draw.rect(surface, (255, 0, 0), (draw_rect.x, draw_rect.y - 10, hp_w, 4))


class BlockingWall(pygame.sprite.Sprite):
    def __init__(self, x, y, h):
        super().__init__()
        self.rect = pygame.Rect(x, y, 50, h)
        self.image = pygame.Surface((50, h), pygame.SRCALPHA)
        self.image.fill(Config.COLORS['wall'])
        for i in range(0, h, 20):
            pygame.draw.line(self.image, (255, 255, 255, 100), (0, i), (50, i + 10), 1)

    def draw(self, surface, camera):
        surface.blit(self.image, camera.apply_rect(self.rect))


class Trap(pygame.sprite.Sprite):
    def __init__(self, x, y, game):
        super().__init__()
        self.game = game
        self.rect = pygame.Rect(x, y, 40, 20)
        self.image = pygame.Surface((40, 20), pygame.SRCALPHA)
        points = [(0, 20), (10, 0), (20, 20), (30, 0), (40, 20)]
        pygame.draw.polygon(self.image, (255, 50, 50), points)

    def update(self):
        if self.rect.right < self.game.camera.offset_x - 500:
            if self in self.game.traps: self.game.traps.remove(self)

    def draw(self, surface, camera):
        surface.blit(self.image, camera.apply_rect(self.rect))


class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.rect = pygame.Rect(x, y, 20, 20)
        self.start_y = y
        self.offset = random.random() * 100

    def update(self):
        self.rect.y = self.start_y + math.sin((pygame.time.get_ticks() + self.offset) * 0.005) * 5

    def draw(self, surface, camera):
        draw_rect = camera.apply_rect(self.rect)
        pygame.draw.circle(surface, Config.COLORS['gold'], draw_rect.center, 8)
        pygame.draw.circle(surface, (255, 255, 200), (draw_rect.centerx - 2, draw_rect.centery - 2), 3)


class HealthPack(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.rect = pygame.Rect(x, y, 24, 24)

    def draw(self, surface, camera):
        draw_rect = camera.apply_rect(self.rect)
        pygame.draw.rect(surface, Config.COLORS['health_pack'], draw_rect, border_radius=4)
        cx, cy = draw_rect.center
        pygame.draw.line(surface, (255, 255, 255), (cx - 6, cy), (cx + 6, cy), 4)
        pygame.draw.line(surface, (255, 255, 255), (cx, cy - 6), (cx, cy + 6), 4)


class SawBlade(pygame.sprite.Sprite):
    def __init__(self, x, y, game, dist=150):
        super().__init__()
        self.game = game
        self.rect = pygame.Rect(x, y, 40, 40)
        self.center_x = x
        self.dist = dist
        self.speed = 3
        self.angle = 0

    def update(self):
        self.rect.x += self.speed
        if self.rect.x > self.center_x + self.dist or self.rect.x < self.center_x - self.dist:
            self.speed *= -1
        self.angle = (self.angle + 10) % 360
        if self.rect.right < self.game.camera.offset_x - 500:
            if self in self.game.traps: self.game.traps.remove(self)

    def draw(self, surface, camera):
        draw_rect = camera.apply_rect(self.rect)
        center = draw_rect.center
        radius = 20
        s = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(s, Config.COLORS['saw_blade'], (20, 20), radius)
        pygame.draw.circle(s, Config.COLORS['saw_danger'], (20, 20), 8)
        for i in range(0, 360, 45):
            rad = math.radians(i + self.angle)
            end_x = 20 + math.cos(rad) * 22
            end_y = 20 + math.sin(rad) * 22
            pygame.draw.line(s, (200, 200, 200), (20, 20), (end_x, end_y), 2)
        surface.blit(s, draw_rect)