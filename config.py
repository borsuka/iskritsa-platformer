"""Всички константи на играта „Искрица: Пътят на светлината“.

Правило на проекта: в кода няма „магически числа“. Всяка стойност, която влияе на
поведението или визията, живее тук, за да може да се настройва от едно място.
Единиците са пиксели (px) и секунди (s), освен ако не е казано друго.
"""
from __future__ import annotations

import math
from pathlib import Path

# ---------------------------------------------------------------------------
# Общи
# ---------------------------------------------------------------------------
GAME_TITLE = "Искрица: Пътят на светлината"
ROOT_DIR = Path(__file__).resolve().parent
LEVELS_DIR = ROOT_DIR / "levels"
SAVE_PATH = ROOT_DIR / "data" / "save.json"
LEVEL_FILE_SUFFIX = ".txt"

# ---------------------------------------------------------------------------
# Екран и време
# ---------------------------------------------------------------------------
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 540
TILE_SIZE = 32
TARGET_FPS = 60                 # колко пъти в секунда рисуваме (ограничение на clock)
FIXED_DT = 1.0 / 60.0           # фиксирана стъпка на логиката в секунди
MAX_FRAME_TIME = 0.25           # защита от „спирала на смъртта“ при много бавен кадър

# ---------------------------------------------------------------------------
# Физика на героя (раздел 8 от заданието)
# ---------------------------------------------------------------------------
GROUND_ACCELERATION = 1800.0    # px/s², ускорение по земята
AIR_ACCELERATION = 1200.0       # px/s², по-малко контрол във въздуха
GROUND_FRICTION = 2000.0        # px/s², забавяне при пуснат клавиш на земята
AIR_FRICTION = 700.0            # px/s², забавяне при пуснат клавиш във въздуха
MAX_WALK_SPEED = 220.0          # px/s
MAX_RUN_SPEED = 340.0           # px/s (задържан Shift)

GRAVITY = 2200.0                # px/s²
FALL_GRAVITY_MULTIPLIER = 1.4   # по-силна гравитация при падане → „стегнат“ скок
MAX_FALL_SPEED = 700.0          # px/s, крайна скорост на падане

JUMP_HEIGHT_TILES = 3.5
JUMP_HEIGHT = JUMP_HEIGHT_TILES * TILE_SIZE          # px
# От закона за запазване на енергията: v0² = 2·g·h  →  v0 = √(2·g·h).
# Така промяна на JUMP_HEIGHT автоматично дава правилната начална скорост.
JUMP_VELOCITY = math.sqrt(2.0 * GRAVITY * JUMP_HEIGHT)
JUMP_CUT_MULTIPLIER = 0.45      # пуснат бутон при издигане → по-нисък скок
COYOTE_TIME = 0.1               # s, скок малко след слизане от ръба
JUMP_BUFFER_TIME = 0.12         # s, запомнен скок малко преди приземяване
DROP_THROUGH_TIME = 0.25        # s, колко време игнорираме one-way платформите

# Защита от тунелиране: не местим тяло повече от половин тайл наведнъж.
MAX_SUBSTEP_DISTANCE = TILE_SIZE / 2
COLLISION_EPSILON = 0.01        # px, толеранс при сравнение на ръбове

# ---------------------------------------------------------------------------
# Размери на героя
# ---------------------------------------------------------------------------
PLAYER_WIDTH = 22
PLAYER_SMALL_HEIGHT = 28
PLAYER_BIG_HEIGHT = 52

# ---------------------------------------------------------------------------
# Щети, неуязвимост, животи
# ---------------------------------------------------------------------------
START_LIVES = 3
COINS_PER_EXTRA_LIFE = 100
INVULNERABILITY_TIME = 1.5      # s след нараняване
HURT_STUN_TIME = 0.3            # s, в които героят не се управлява след удар
KNOCKBACK_SPEED_X = 220.0       # px/s
KNOCKBACK_SPEED_Y = 380.0       # px/s (нагоре)
STOMP_BOUNCE_VELOCITY = 480.0   # px/s, отскок след скачане върху враг
STOMP_BOUNCE_HELD_VELOCITY = 700.0  # по-висок отскок, ако скокът е задържан
STOMP_TOLERANCE = 0.5           # дял от височината на врага, който се брои за „отгоре“
DEATH_HOP_VELOCITY = 520.0      # px/s, подскок на героя при смърт
DEATH_ANIMATION_TIME = 2.0      # s преди да се загуби живот и нивото да рестартира
BLINK_FREQUENCY = 15.0          # Hz, мигане при неуязвимост
PIT_DEATH_MARGIN = 64           # px под картата → смърт от пропаст
STAR_DURATION = 8.0             # s неуязвимост от „Комета“

# ---------------------------------------------------------------------------
# Снаряди
# ---------------------------------------------------------------------------
FIREBALL_SPEED = 420.0
FIREBALL_BOUNCE_VELOCITY = 250.0  # връх ≈ v²/(2g) ≈ 16 px – ниско, за да уцелва враговете
FIREBALL_GRAVITY = 2000.0
FIREBALL_SPAWN_DROP = 0.2       # дял от височината на героя под центъра
FIREBALL_LIFETIME = 2.5
FIREBALL_SIZE = 12
MAX_PLAYER_FIREBALLS = 2
ENEMY_PROJECTILE_SPEED = 230.0
ENEMY_PROJECTILE_SIZE = 12
ENEMY_PROJECTILE_LIFETIME = 5.0

# ---------------------------------------------------------------------------
# Врагове
# ---------------------------------------------------------------------------
WALKER_SPEED = 60.0
WALKER_SIZE = (28, 24)
HOPPER_SIZE = (26, 26)
HOPPER_WAIT_TIME = 1.2
HOPPER_JUMP_VELOCITY = 560.0
HOPPER_JUMP_SPEED_X = 130.0
HOPPER_SIGHT_RANGE = 10 * TILE_SIZE
FLYER_SIZE = (28, 20)
FLYER_SPEED = 70.0
FLYER_AMPLITUDE = 40.0          # px, амплитуда на синусоидата
FLYER_FREQUENCY = 1.2           # Hz
FLYER_PATROL_RANGE = 4 * TILE_SIZE
SHOOTER_SIZE = (28, 30)
SHOOTER_INTERVAL = 2.2          # s между изстрелите
SHOOTER_RANGE_X = 9 * TILE_SIZE
SHOOTER_RANGE_Y = 5 * TILE_SIZE
ENEMY_ACTIVATION_DISTANCE = SCREEN_WIDTH  # врагове далеч от героя „спят“

BOSS_SIZE = (60, 60)
BOSS_MAX_HP = 3
BOSS_SPEED = 90.0
BOSS_INVULNERABLE_TIME = 1.5
BOSS_JUMP_VELOCITY = 720.0
BOSS_JUMP_INTERVAL = (2.6, 2.0, 1.5)       # s, по фази
BOSS_SHOT_INTERVAL = 2.4
BOSS_SHOT_SPREAD = (-0.35, 0.0, 0.35)      # rad, ветрило от снаряди
BOSS_SUMMON_INTERVAL = 4.0
BOSS_MAX_MINIONS = 3
BOSS_SPEED_MULTIPLIER = (1.0, 1.3, 1.6)    # по фази
SCREEN_SHAKE_TIME = 0.4
SCREEN_SHAKE_STRENGTH = 8.0

# ---------------------------------------------------------------------------
# Предмети и блокове
# ---------------------------------------------------------------------------
POWERUP_SPEED = 80.0
POWERUP_EMERGE_SPEED = 32.0     # px/s, излизане от блока
COMET_BOUNCE_VELOCITY = 520.0
BLOCK_BUMP_TIME = 0.15          # s, анимация на подскачащ блок
BLOCK_BUMP_HEIGHT = 8           # px
COIN_POP_TIME = 0.45            # s, анимация на монета от блок
COIN_POP_VELOCITY = 420.0

# ---------------------------------------------------------------------------
# Платформи
# ---------------------------------------------------------------------------
MOVING_PLATFORM_WIDTH_TILES = 3
MOVING_PLATFORM_RANGE_TILES = 4
MOVING_PLATFORM_PERIOD = 4.0    # s за пълен цикъл напред-назад
FALLING_PLATFORM_WIDTH_TILES = 2
FALLING_PLATFORM_DELAY = 0.5    # s клатене преди падане
FALLING_PLATFORM_RESPAWN = 3.0  # s до връщане на мястото
PLATFORM_THICKNESS = 12         # px, само за рисуване

# ---------------------------------------------------------------------------
# Опасности
# ---------------------------------------------------------------------------
SPIKE_HITBOX_HEIGHT = 18        # px от долния ръб на тайла
LAVA_HITBOX_HEIGHT = 22         # px от долния ръб на тайла

# ---------------------------------------------------------------------------
# Точки
# ---------------------------------------------------------------------------
POINTS = {
    "coin": 10,
    "crystal": 500,
    "walker": 100,
    "hopper": 150,
    "flyer": 200,
    "shooter": 200,
    "boss": 5000,
    "powerup": 1000,
    "brick": 50,
}
POINTS_PER_SECOND_LEFT = 10
CRYSTALS_PER_LEVEL = 5

# ---------------------------------------------------------------------------
# Камера
# ---------------------------------------------------------------------------
CAMERA_DEAD_ZONE_WIDTH = 120
CAMERA_DEAD_ZONE_HEIGHT = 140
CAMERA_SMOOTHING = 8.0          # 1/s, колко бързо камерата догонва целта
CAMERA_LOOK_AHEAD = 90.0        # px напред по посока на движението
CAMERA_LOOK_AHEAD_SPEED = 3.0   # 1/s, плавност на look-ahead
CAMERA_LOOK_AHEAD_MIN_SPEED = 40.0  # px/s, под тази скорост не гледаме напред
PARALLAX_FACTORS = (0.15, 0.35, 0.6)    # далечен, среден, близък слой

# ---------------------------------------------------------------------------
# Анимации
# ---------------------------------------------------------------------------
ANIMATION_FPS = 10
IDLE_BREATH_SPEED = 3.0         # rad/s
FADE_TIME = 0.35                # s за fade out / fade in
PARTICLE_GRAVITY = 900.0
PARTICLE_LIFETIME = 0.6

# ---------------------------------------------------------------------------
# Звук
# ---------------------------------------------------------------------------
AUDIO_SAMPLE_RATE = 22050
AUDIO_VOLUME = 0.35
AUDIO_ENABLED = True

# ---------------------------------------------------------------------------
# Цветове (RGB)
# ---------------------------------------------------------------------------
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
HUD_TEXT = (255, 248, 230)
HUD_SHADOW = (20, 16, 30)
HUD_ACCENT = (255, 200, 80)
MENU_BG_TOP = (28, 22, 58)
MENU_BG_BOTTOM = (92, 44, 88)
MENU_SELECTED = (255, 210, 90)
MENU_NORMAL = (220, 214, 240)
MENU_DISABLED = (110, 104, 130)
DEBUG_HITBOX = (255, 0, 255)
DEBUG_TEXT = (0, 255, 120)
BOSS_BAR_BG = (40, 10, 20)
BOSS_BAR_FG = (220, 50, 90)

# Палитри по светове: ключът е стойността на `background` в [meta].
PALETTES: dict[str, dict[str, tuple[int, int, int]]] = {
    "forest": {
        "sky_top": (110, 180, 230), "sky_bottom": (200, 235, 225),
        "far": (120, 170, 170), "mid": (70, 130, 100), "near": (40, 95, 70),
        "ground": (120, 82, 50), "ground_dark": (90, 60, 38), "ground_top": (90, 190, 80),
        "platform": (170, 120, 70), "brick": (190, 110, 70), "accent": (255, 220, 110),
    },
    "cave": {
        "sky_top": (20, 18, 40), "sky_bottom": (50, 40, 80),
        "far": (45, 40, 75), "mid": (60, 55, 95), "near": (80, 70, 115),
        "ground": (85, 85, 110), "ground_dark": (60, 60, 82), "ground_top": (120, 200, 220),
        "platform": (110, 110, 140), "brick": (130, 100, 150), "accent": (140, 240, 255),
    },
    "castle": {
        "sky_top": (40, 10, 30), "sky_bottom": (120, 40, 50),
        "far": (70, 25, 45), "mid": (55, 30, 50), "near": (35, 22, 38),
        "ground": (95, 90, 100), "ground_dark": (65, 60, 72), "ground_top": (150, 145, 160),
        "platform": (120, 90, 80), "brick": (140, 70, 60), "accent": (255, 120, 80),
    },
}
DEFAULT_BACKGROUND = "forest"

# ---------------------------------------------------------------------------
# Клавиши: действие → списък с имена на клавиши (pygame.key.key_code имена).
# Държим имена, а не pygame константи, за да не зависи config от pygame.
# ---------------------------------------------------------------------------
KEY_BINDINGS: dict[str, tuple[str, ...]] = {
    "left": ("left", "a"),
    "right": ("right", "d"),
    "up": ("up", "w"),
    "down": ("down", "s"),
    "jump": ("space", "w", "up"),
    "run": ("left shift", "right shift"),
    "shoot": ("x", "j"),
    "pause": ("escape", "p"),
    "confirm": ("return", "space"),
    "back": ("escape", "backspace"),
    "debug": ("f1",),
}
