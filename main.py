import pygame
import random
import sys
from config import Config
from vfx import Camera, SwordVFX, FloatingText
from entities import Player, Coin, HealthPack, BlockingWall
from world import LevelManager
from weapons import WeaponItem, ShieldItem, SoundWave
from store import PersistentStorage, Shop
from bosses import BossBase


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT))
        pygame.display.set_caption(Config.TITLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 20, bold=True)
        self.title_font = pygame.font.SysFont("arial", 80, bold=True)
        self.menu_font = pygame.font.SysFont("arial", 40, bold=True)

        self.storage = PersistentStorage()
        self.shop = Shop(self.storage)
        self.shop_selection = 0

        self.state = "MENU"
        self.previous_state = "MENU"  # 新增：记录进入商店前的状态
        self.reset_game()

    def reset_game(self):
        self.camera = Camera()
        self.enemies = []
        self.traps = []
        self.items = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.player_projectiles = pygame.sprite.Group()
        self.particles = []
        self.floating_texts = []
        self.sword_vfxs = []
        self.hit_stop = 0

        self.level_manager = LevelManager(self)
        self.platforms = self.level_manager.platforms

        self.player = Player(100, 300, self)
        self.apply_shop_upgrades()
        self.coins_collected = 0

        self.stars = []
        for _ in range(100):
            self.stars.append([random.randint(0, Config.SCREEN_WIDTH), random.randint(0, Config.SCREEN_HEIGHT),
                               random.uniform(0.5, 2)])

    def apply_shop_upgrades(self):
        purchased = self.shop.purchased_items
        if "double_jump" in purchased: self.player.max_jumps = 2
        if "extra_health" in purchased:
            self.player.max_hp = 150
            self.player.hp = 150
        if "speed_boost" in purchased: self.player.speed_mult = 1.3
        if "special_sword" in purchased: self.player.damage_mult = 1.5

    def add_sword_vfx(self, rect, facing_right):
        self.sword_vfxs.append(SwordVFX(rect, facing_right))

    def draw_background(self):
        self.screen.fill(Config.COLORS['bg_sky'])
        for star in self.stars:
            bx = (star[0] - self.camera.offset_x * 0.05) % Config.SCREEN_WIDTH
            by = (star[1] - self.camera.offset_y * 0.05) % Config.SCREEN_HEIGHT
            pygame.draw.circle(self.screen, Config.COLORS['bg_stars'], (bx, by), star[2])
        mx = self.camera.offset_x * 0.2
        offset = mx % Config.SCREEN_WIDTH
        for i in range(-1, 2):
            base_x = i * Config.SCREEN_WIDTH + offset
            pygame.draw.polygon(self.screen, Config.COLORS['bg_far'], [
                (base_x, Config.SCREEN_HEIGHT),
                (base_x + 200, 300),
                (base_x + 600, 600),
                (base_x + 900, 250),
                (base_x + 1280, Config.SCREEN_HEIGHT)
            ])

    def draw_menu(self):
        self.draw_background()
        overlay = pygame.Surface((Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT))
        overlay.set_alpha(150)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        title_surf = self.title_font.render("NEON BLADE", True, Config.COLORS['player_scarf'])
        title_rect = title_surf.get_rect(center=(Config.SCREEN_WIDTH // 2, Config.SCREEN_HEIGHT // 3))
        shadow_surf = self.title_font.render("NEON BLADE", True, (0, 100, 100))
        self.screen.blit(shadow_surf, (title_rect.x + 4, title_rect.y + 4))
        self.screen.blit(title_surf, title_rect)

        if pygame.time.get_ticks() % 1000 < 600:
            start_text = self.menu_font.render("- Press SPACE to Start -", True, (255, 255, 255))
            start_rect = start_text.get_rect(center=(Config.SCREEN_WIDTH // 2, Config.SCREEN_HEIGHT // 2))
            self.screen.blit(start_text, start_rect)

        high_score = self.storage.get_high_score()
        coins = self.storage.get_coins()
        high_score_text = self.font.render(f"Max Dist: {high_score}m", True, Config.COLORS['gold'])
        coins_text = self.font.render(f"Total Coins: {coins}", True, Config.COLORS['gold'])
        self.screen.blit(high_score_text, (20, 20))
        self.screen.blit(coins_text, (20, 50))

        # 绘制操作说明装饰
        controls = [
            "[WASD] Move & Jump",
            "[J] Attack",
            "[Z] Shop / [ESC] Quit"
        ]
        for i, line in enumerate(controls):
            ct = self.font.render(line, True, (150, 150, 150))
            cr = ct.get_rect(center=(Config.SCREEN_WIDTH // 2, Config.SCREEN_HEIGHT // 2 + 80 + i * 35))
            self.screen.blit(ct, cr)

    def draw_pause_menu(self):
        """绘制暂停界面：在当前游戏画面上叠加"""
        # 注意：这里我们不重新绘制背景，而是利用上一帧的画面残影，或者显式重绘一次游戏场景
        # 为了简单，我们只绘制一个半透明层
        overlay = pygame.Surface((Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 20))  # 深蓝色遮罩
        self.screen.blit(overlay, (0, 0))

        # 暂停标题
        title_surf = self.title_font.render("PAUSED", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(Config.SCREEN_WIDTH // 2, Config.SCREEN_HEIGHT // 3))
        self.screen.blit(title_surf, title_rect)

        # 选项
        options = [
            "Press [ESC] to Resume",
            "Press [Q] to Main Menu",
            "Press [Z] to Shop"
        ]

        for i, text in enumerate(options):
            opt_surf = self.menu_font.render(text, True, (200, 200, 255))
            opt_rect = opt_surf.get_rect(center=(Config.SCREEN_WIDTH // 2, Config.SCREEN_HEIGHT // 2 + i * 60))
            self.screen.blit(opt_surf, opt_rect)

    def draw_game_over(self):
        self.draw_background()
        self.level_manager.draw(self.screen, self.camera)
        self.player.draw(self.screen, self.camera)
        overlay = pygame.Surface((Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((50, 0, 0))
        self.screen.blit(overlay, (0, 0))

        go_surf = self.title_font.render("GAME OVER", True, (255, 50, 50))
        go_rect = go_surf.get_rect(center=(Config.SCREEN_WIDTH // 2, Config.SCREEN_HEIGHT // 3))
        self.screen.blit(go_surf, go_rect)

        dist_score = int(self.player.rect.x / 10)
        score_surf = self.menu_font.render(f"Distance: {dist_score}m", True, Config.COLORS['gold'])
        score_rect = score_surf.get_rect(center=(Config.SCREEN_WIDTH // 2, Config.SCREEN_HEIGHT // 2))
        self.screen.blit(score_surf, score_rect)

        coins_surf = self.font.render(f"Coins Collected: {self.coins_collected}", True, (255, 255, 255))
        coins_rect = coins_surf.get_rect(center=(Config.SCREEN_WIDTH // 2, Config.SCREEN_HEIGHT // 2 + 50))
        self.screen.blit(coins_surf, coins_rect)

        retry_surf = self.font.render("Press SPACE to Retry  |  ESC to Menu", True, (200, 200, 200))
        retry_rect = retry_surf.get_rect(center=(Config.SCREEN_WIDTH // 2, Config.SCREEN_HEIGHT // 2 + 120))
        self.screen.blit(retry_surf, retry_rect)

        shop_surf = self.font.render("Press Z to Open Shop", True, (100, 255, 255))
        shop_rect = shop_surf.get_rect(center=(Config.SCREEN_WIDTH // 2, Config.SCREEN_HEIGHT // 2 + 130))
        self.screen.blit(shop_surf, shop_rect)

    def draw_shop(self):
        self.draw_background()
        overlay = pygame.Surface((Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT))
        overlay.set_alpha(240)
        overlay.fill((10, 10, 20))
        self.screen.blit(overlay, (0, 0))

        title_surf = self.title_font.render("SHOP", True, (0, 255, 255))
        title_rect = title_surf.get_rect(center=(Config.SCREEN_WIDTH // 2, Config.SCREEN_HEIGHT // 6))
        title_shadow = self.title_font.render("SHOP", True, (0, 100, 100))
        self.screen.blit(title_shadow, (title_rect.x + 4, title_rect.y + 4))
        self.screen.blit(title_surf, title_rect)

        coins = self.storage.get_coins()
        coins_text = f"My Coins: {coins}"
        coins_surf = self.font.render(coins_text, True, Config.COLORS['gold'])
        coins_bg_rect = coins_surf.get_rect(topright=(Config.SCREEN_WIDTH - 30, 30))
        coins_bg_rect.inflate_ip(20, 10)
        pygame.draw.rect(self.screen, (50, 40, 0), coins_bg_rect, border_radius=5)
        pygame.draw.rect(self.screen, Config.COLORS['gold'], coins_bg_rect, 2, border_radius=5)
        self.screen.blit(coins_surf, coins_surf.get_rect(center=coins_bg_rect.center))

        items = self.shop.get_shop_items()
        start_y = Config.SCREEN_HEIGHT // 4 + 20
        item_height = 90

        tip_surf = self.font.render("UP/DOWN to Select, ENTER to Buy, ESC to Back", True, (150, 150, 150))
        self.screen.blit(tip_surf, (100, start_y - 30))

        for i, item in enumerate(items):
            item_y = start_y + i * item_height
            item_rect = pygame.Rect(100, item_y, Config.SCREEN_WIDTH - 200, 70)
            is_selected = (i == self.shop_selection)

            if is_selected:
                bg_color = (60, 60, 90)
            else:
                bg_color = (30, 30, 45) if i % 2 == 0 else (25, 25, 40)

            pygame.draw.rect(self.screen, bg_color, item_rect, border_radius=8)

            border_color = (60, 60, 80)
            if is_selected:
                border_color = (255, 255, 0)
            elif not item.purchased and coins >= item.price:
                border_color = (0, 200, 0)

            pygame.draw.rect(self.screen, border_color, item_rect, 2 if not is_selected else 4, border_radius=8)

            name_font = pygame.font.SysFont("arial", 24, bold=True)
            name_color = (255, 255, 255) if is_selected else (200, 200, 200)
            name_surf = name_font.render(item.name, True, name_color)
            self.screen.blit(name_surf, (item_rect.x + 20, item_rect.y + 10))

            price_color = Config.COLORS['gold'] if coins >= item.price else (200, 80, 80)
            price_surf = self.font.render(f"{item.price} G", True, price_color)
            self.screen.blit(price_surf, (item_rect.right - 120, item_rect.y + 12))

            desc_surf = self.font.render(item.description, True, (180, 180, 180))
            self.screen.blit(desc_surf, (item_rect.x + 20, item_rect.y + 40))

            if item.purchased:
                status_text = "OWNED"
                status_color = (100, 100, 100)
            elif coins >= item.price:
                status_text = "Buy"
                status_color = (0, 255, 0)
            else:
                status_text = "No $"
                status_color = (200, 50, 50)

            status_surf = self.font.render(status_text, True, status_color)
            self.screen.blit(status_surf, (item_rect.right - 180, item_rect.y + 40))

        back_surf = self.font.render("Press ESC to Return", True, (180, 180, 180))
        back_rect = back_surf.get_rect(center=(Config.SCREEN_WIDTH // 2, Config.SCREEN_HEIGHT - 40))
        self.screen.blit(back_surf, back_rect)

    def handle_shop_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return "QUIT"
            if event.type == pygame.KEYDOWN:
                # 修复逻辑：按 ESC 返回上一个状态
                if event.key == pygame.K_ESCAPE:
                    return self.previous_state

                if event.key == pygame.K_UP or event.key == pygame.K_w:
                    self.shop_selection = max(0, self.shop_selection - 1)
                if event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    self.shop_selection = min(len(self.shop.get_shop_items()) - 1, self.shop_selection + 1)
                if event.key == pygame.K_RETURN:
                    items = self.shop.get_shop_items()
                    if items and 0 <= self.shop_selection < len(items):
                        success, message = self.shop.purchase_item(items[self.shop_selection].id)
                        color = (100, 255, 100) if success else (255, 100, 100)
                        self.floating_texts.append(
                            FloatingText(Config.SCREEN_WIDTH // 2, Config.SCREEN_HEIGHT // 2, message, color))
                        self.apply_shop_upgrades()
        return "SHOP"

    def save_game_data(self):
        dist_score = int(self.player.rect.x / 10)
        self.storage.set_high_score(dist_score)
        if self.coins_collected > 0:
            self.storage.add_coins(self.coins_collected)
            self.coins_collected = 0

    def run(self):
        running = True
        while running:
            if self.state == "MENU":
                for event in pygame.event.get():
                    if event.type == pygame.QUIT: running = False
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_SPACE:
                            self.state = "PLAYING"
                            self.reset_game()
                        elif event.key == pygame.K_z:  # 菜单界面进商店
                            self.previous_state = "MENU"  # 记录来源
                            self.state = "SHOP"
                        elif event.key == pygame.K_ESCAPE:
                            running = False  # 菜单按ESC退出游戏
                self.draw_menu()

            elif self.state == "PAUSED":
                for event in pygame.event.get():
                    if event.type == pygame.QUIT: running = False
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:  # 继续游戏
                            self.state = "PLAYING"
                        elif event.key == pygame.K_q:  # 返回主菜单
                            self.state = "MENU"
                            self.save_game_data()
                        elif event.key == pygame.K_z:  # 暂停界面进商店
                            self.previous_state = "PAUSED"  # 记录来源
                            self.state = "SHOP"
                self.draw_pause_menu()

            elif self.state == "SHOP":
                action = self.handle_shop_events()
                if action == "QUIT":
                    running = False
                elif action == "SHOP":
                    pass
                else:
                    # action 返回的是 self.previous_state (MENU / PAUSED / GAME_OVER)
                    self.state = action

                for ft in self.floating_texts[:]:
                    ft.update()
                    if ft.life <= 0: self.floating_texts.remove(ft)
                self.draw_shop()
                for ft in self.floating_texts:
                    ft.draw(self.screen, self.camera, self.font)

            elif self.state == "PLAYING":
                for event in pygame.event.get():
                    if event.type == pygame.QUIT: running = False
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_r:
                            self.reset_game()
                        elif event.key == pygame.K_z:
                            self.previous_state = "PAUSED"  # 游戏中进商店，退出来应该是暂停状态比较安全
                            self.state = "SHOP"
                        elif event.key == pygame.K_ESCAPE:
                            self.state = "PAUSED"  # 游戏中按ESC暂停
                        elif event.key == pygame.K_SPACE:
                            self.player.jump()

                if self.hit_stop > 0:
                    self.hit_stop -= 1
                    self.clock.tick(Config.FPS)
                    continue

                self.level_manager.update(self.camera.offset_x)
                self.platforms = self.level_manager.platforms
                self.player.update()

                item_hits = pygame.sprite.spritecollide(self.player, self.items, True)
                for item in item_hits:
                    if isinstance(item, Coin):
                        self.coins_collected += 1
                        self.floating_texts.append(
                            FloatingText(item.rect.centerx, item.rect.top, "+1 Gold", Config.COLORS['gold']))
                    elif isinstance(item, HealthPack):
                        self.player.heal(30)
                    elif isinstance(item, WeaponItem):
                        self.player.equip_weapon(item.weapon_type)
                    elif isinstance(item, ShieldItem):
                        self.player.add_shield()

                bullet_hits = pygame.sprite.spritecollide(self.player, self.projectiles, True)
                for bullet in bullet_hits: self.player.take_damage(10)

                for proj in self.player_projectiles:
                    hits = pygame.sprite.spritecollide(proj, self.enemies, False)
                    for enemy in hits:
                        if hasattr(proj, 'hit_list') and enemy in proj.hit_list: continue
                        dmg = getattr(proj, 'damage', 25)
                        enemy.take_damage(dmg)
                        if isinstance(proj, SoundWave):
                            dist = enemy.rect.centerx - self.player.rect.centerx
                            direction = 1 if dist > 0 else -1
                            enemy.rect.x += direction * 20
                            enemy.vel.x = 0
                        if hasattr(proj, 'hit_list'): proj.hit_list.append(enemy)
                        if not getattr(proj, 'penetrate', False):
                            proj.kill()
                            break

                if pygame.sprite.spritecollideany(self.player, self.traps):
                    hits = pygame.sprite.spritecollide(self.player, self.traps, False)
                    for t in hits:
                        if isinstance(t, BlockingWall):
                            self.player.rect.right = t.rect.left
                            self.player.vel.x = 0
                        else:
                            self.player.take_damage(20)

                if pygame.sprite.spritecollideany(self.player, self.enemies):
                    self.player.take_damage(15)

                if self.player.hp <= 0:
                    self.save_game_data()
                    self.state = "GAME_OVER"

                for e in self.enemies: e.update()
                for t in self.traps: t.update()
                self.items.update()
                self.projectiles.update()
                self.player_projectiles.update()
                self.camera.update(self.player)

                for p in self.particles[:]:
                    p.update()
                    if p.life <= 0: self.particles.remove(p)
                for ft in self.floating_texts[:]:
                    ft.update()
                    if ft.life <= 0: self.floating_texts.remove(ft)
                self.sword_vfxs = [v for v in self.sword_vfxs if v.life > 0]

                self.draw_background()
                self.level_manager.draw(self.screen, self.camera)
                for t in self.traps: t.draw(self.screen, self.camera)
                for item in self.items:
                    if hasattr(item, 'draw'): item.draw(self.screen, self.camera)
                for e in self.enemies: e.draw(self.screen, self.camera)
                for p in self.projectiles: p.draw(self.screen, self.camera)
                for p in self.player_projectiles: p.draw(self.screen, self.camera)

                self.player.draw(self.screen, self.camera)
                for vfx in self.sword_vfxs: vfx.draw(self.screen, self.camera)
                for p in self.particles: p.draw(self.screen, self.camera)
                for ft in self.floating_texts: ft.draw(self.screen, self.camera, self.font)

                # UI
                pygame.draw.rect(self.screen, (0, 0, 0), (0, 0, Config.SCREEN_WIDTH, 60))
                pygame.draw.line(self.screen, (50, 50, 50), (0, 60), (Config.SCREEN_WIDTH, 60))

                hp_color = (0, 255, 0) if self.player.hp > 30 else (255, 0, 0)
                self.screen.blit(self.font.render(f"HP: {int(self.player.hp)}/{self.player.max_hp}", True, hp_color),
                                 (20, 20))

                dist_score = int(self.player.rect.x / 10)
                current_total_coins = self.storage.get_coins() + self.coins_collected

                self.screen.blit(self.font.render(f"Distance: {dist_score}m", True, (200, 200, 255)), (200, 20))
                self.screen.blit(self.font.render(f"Coins: {current_total_coins}", True, Config.COLORS['gold']),
                                 (400, 20))

                shield_text = f"SHIELD: {self.player.shield_durability}"
                shield_color = Config.COLORS['shield'] if self.player.shield_durability > 0 else (100, 100, 100)
                self.screen.blit(self.font.render(shield_text, True, shield_color), (600, 20))

                self.screen.blit(
                    self.font.render("[WASD] Move [J] Atk [SPC] Jump [Z] Shop [ESC] Pause", True, (150, 150, 150)),
                    (Config.SCREEN_WIDTH - 500, 20))

            elif self.state == "GAME_OVER":
                for event in pygame.event.get():
                    if event.type == pygame.QUIT: running = False
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_SPACE:
                            self.state = "PLAYING"
                            self.reset_game()
                        elif event.key == pygame.K_z:
                            self.previous_state = "GAME_OVER"
                            self.state = "SHOP"
                        elif event.key == pygame.K_ESCAPE:
                            self.state = "MENU"
                self.draw_game_over()

            pygame.display.flip()
            self.clock.tick(Config.FPS)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()