import pygame


class Config:
    SCREEN_WIDTH = 1280
    SCREEN_HEIGHT = 720
    FPS = 60
    TITLE = "NEON BLADE: ROCK & ROLL"

    # 物理与手感
    GRAVITY = 0.9
    FRICTION = -0.15
    PLAYER_ACC = 1.2
    PLAYER_MAX_SPEED = 9
    PLAYER_JUMP = -22
    HIT_STOP_DURATION = 5

    # 游戏机制
    BOSS_SPAWN_INTERVAL = 10000

    # 颜色库 (赛博朋克调色板)
    COLORS = {
        'bg_sky': (10, 10, 20),
        'bg_stars': (200, 200, 255),
        'bg_far': (30, 20, 40),
        'bg_mid': (50, 30, 60),
        'ground': (20, 20, 25),
        'platform_border': (0, 255, 255),
        'player': (255, 255, 255),
        'player_scarf': (0, 255, 255),
        'enemy': (20, 20, 20),
        'enemy_eye': (255, 0, 50),
        'damage_text': (255, 50, 50),
        'sword_arc': (0, 255, 255),
        'gold': (255, 215, 0),
        'health_pack': (0, 255, 100),
        'saw_blade': (180, 180, 190),
        'saw_danger': (255, 0, 0),

        # 武器颜色
        'weapon_axe': (255, 100, 0),
        'weapon_bow': (100, 255, 100),
        'weapon_laser': (0, 255, 255),
        'weapon_hammer': (200, 0, 255),
        'weapon_boomerang': (220, 255, 0),  # 柠檬黄 (新)
        'weapon_guitar': (255, 0, 150),  # 霓虹粉 (新)

        'arrow': (150, 255, 150),
        'laser_beam': (200, 255, 255),
        'lightning': (220, 220, 255),
        'sound_wave': (255, 100, 200),  # 音波颜色 (新)

        'shield': (0, 150, 255),
        'shield_aura': (0, 100, 255),

        # Boss 和 新怪物
        'boss_body': (150, 0, 50),
        'boss_armor': (50, 0, 20),
        'boss_core': (255, 50, 50),
        'wall': (255, 50, 50),
        'shadow_boss': (50, 0, 100),
        'bomber_boss': (200, 100, 0),
        'turret': (100, 100, 120),
        'beetle': (0, 200, 50)
    }