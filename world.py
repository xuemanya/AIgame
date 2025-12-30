import pygame
import random
from config import Config
from entities import Enemy, Trap, Coin, HealthPack, SawBlade, BlockingWall
from advanced_enemies import Bat, Drone, KamikazeBeetle, Turret
from bosses import FloatingFortress, ShadowWalker, InfernoBomber, BossBase
from weapons import WeaponItem, ShieldItem


class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h):
        super().__init__()
        self.rect = pygame.Rect(x, y, w, h)
        self.image = pygame.Surface((w, h))
        self.image.fill(Config.COLORS['platform_border'])
        pygame.draw.rect(self.image, (0, 0, 0), (2, 2, w - 4, h - 4))
        for i in range(0, w, 20):
            pygame.draw.line(self.image, (30, 30, 40), (i, 0), (i, h))

    def draw(self, surface, camera):
        surface.blit(self.image, camera.apply_rect(self.rect))


class LevelManager:
    def __init__(self, game):
        self.game = game
        self.platforms = pygame.sprite.Group()
        self.next_x = -200
        self.ground_height = Config.SCREEN_HEIGHT - 50

        # Boss战逻辑变量
        self.distance_traveled = 0
        self.next_boss_milestone = Config.BOSS_SPAWN_INTERVAL
        self.boss_spawned = False
        self.boss_wall = None

        self.generate_platform(-500, self.ground_height, 1500, 500)
        self.next_x = 1000

    def generate_platform(self, x, y, w, h):
        p = Platform(x, y, w, h)
        self.platforms.add(p)

    def update(self, camera_x):
        self.distance_traveled = -camera_x

        # 检查 Boss 战结束
        if self.boss_spawned:
            boss_alive = False
            for e in self.game.enemies:
                if isinstance(e, BossBase):
                    boss_alive = True
                    break

            if not boss_alive:
                self.boss_spawned = False
                self.next_boss_milestone += Config.BOSS_SPAWN_INTERVAL
                if self.boss_wall:
                    self.boss_wall.kill()
                    if self.boss_wall in self.game.traps:
                        self.game.traps.remove(self.boss_wall)
                    self.boss_wall = None
                self.game.items.add(HealthPack(self.next_x, self.ground_height - 100))

        if self.boss_spawned:
            return

        view_right = -camera_x + Config.SCREEN_WIDTH
        if self.next_x < view_right + 200:
            if self.next_x > self.next_boss_milestone:
                self.spawn_boss_arena()
            else:
                self.spawn_chunk()

        view_left = -camera_x
        for p in self.platforms:
            if p.rect.right < view_left - 500:
                p.kill()

    def spawn_boss_arena(self):
        """随机生成一个 Boss"""
        print("Spawning BOSS ARENA!")
        x = self.next_x + 100
        width = 1500
        y = Config.SCREEN_HEIGHT - 100

        self.generate_platform(x, y, width, 500)

        boss_x = x + 1000
        boss_y = y - 200

        # 随机选择一个 Boss
        BossClass = random.choice([FloatingFortress, ShadowWalker, InfernoBomber])
        boss = BossClass(boss_x, boss_y, self.game)
        self.game.enemies.append(boss)

        wall_x = x + width - 50
        wall = BlockingWall(wall_x, y - 600, 600)
        self.game.traps.append(wall)
        self.boss_wall = wall

        self.boss_spawned = True
        self.ground_height = y
        self.next_x = x + width

    def spawn_chunk(self):
        gap = random.randint(100, 250)
        width = random.randint(400, 800)  # 平台稍微变长，给怪物更多空间

        height_change = random.choice([-60, 0, 60])
        new_y = self.ground_height + height_change
        new_y = max(Config.SCREEN_HEIGHT - 350, min(Config.SCREEN_HEIGHT - 50, new_y))
        self.ground_height = new_y

        x = self.next_x + gap
        self.generate_platform(x, new_y, width, 500)

        # --- 物品生成 ---
        # 武器 (15%)
        if random.random() < 0.15:
            weapon_type = random.choice(["axe", "bow", "laser", "hammer", "boomerang", "guitar"])
            self.game.items.add(WeaponItem(x + random.randint(50, width - 50), new_y - 40, weapon_type))

        # 护盾 (8%)
        if random.random() < 0.08:
            self.game.items.add(ShieldItem(x + random.randint(50, width - 50), new_y - 40))

        # 金币 (50%)
        if random.random() < 0.5:
            start_cx = x + random.randint(20, width - 150)
            for i in range(random.randint(3, 6)):
                self.game.items.add(Coin(start_cx + i * 25, new_y - 40))

        # 血包 (5%)
        if random.random() < 0.05:
            hx = x + random.randint(20, width - 20)
            self.game.items.add(HealthPack(hx, new_y - 40))

        # --- 怪物生成 (权重系统优化) ---
        # 现在的逻辑：80% 概率生成敌人/障碍，然后根据权重决定生成哪种
        if random.random() < 0.8:
            # 定义怪物池和权重 (名称, 权重, 生成函数)
            # 权重越高，出现概率越大
            spawn_pool = [
                ("enemy", 25,
                 lambda: self.game.enemies.append(Enemy(x + random.randint(50, width - 50), new_y - 60, self.game))),
                ("drone", 15,
                 lambda: self.game.enemies.append(Drone(x + width // 2, new_y - random.randint(150, 250), self.game))),
                ("bat", 15, lambda: self._spawn_bats(x + width // 2, new_y - random.randint(80, 150))),
                ("turret", 12,
                 lambda: self.game.enemies.append(Turret(x + random.randint(100, width - 100), new_y - 40, self.game))),
                ("beetle", 15, lambda: self.game.enemies.append(
                    KamikazeBeetle(x + random.randint(50, width - 50), new_y - 20, self.game))),
                ("saw", 10, lambda: self.game.traps.append(SawBlade(x + width // 2, new_y - 40, self.game))),
                ("spikes", 15, lambda: self._spawn_spikes(x + random.randint(50, width - 50), new_y - 20))
            ]

            # 计算总权重
            total_weight = sum(item[1] for item in spawn_pool)
            pick = random.uniform(0, total_weight)
            current = 0

            for name, weight, spawn_func in spawn_pool:
                current += weight
                if pick <= current:
                    spawn_func()
                    break

        self.next_x = x + width

    def _spawn_bats(self, x, y):
        self.game.enemies.append(Bat(x, y, self.game))
        self.game.enemies.append(Bat(x + 50, y + 30, self.game))

    def _spawn_spikes(self, x, y):
        # 确保尖刺周围没有其他敌人重叠 (简单检查)
        safe = True
        for e in self.game.enemies:
            if abs(e.rect.x - x) < 60:
                safe = False
                break
        if safe:
            self.game.traps.append(Trap(x, y, self.game))

    def draw(self, surface, camera):
        for p in self.platforms:
            p.draw(surface, camera)