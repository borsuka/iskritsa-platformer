"""Програмно генерирана графика.

Проектът няма нито един PNG файл: всеки спрайт се рисува с прости форми
(елипси, многоъгълници, градиенти) при първото поискване и се пази в кеш.
Всички функции връщат `pygame.Surface`, така че по-късно всяка от тях може да
бъде заменена с `pygame.image.load("hero.png")` без промяна в останалия код.

Всички спрайтове се рисуват с лице надясно; обърнатите наляво се получават с
`pygame.transform.flip` и също се кешират.
"""
from __future__ import annotations

import math
import random
from typing import Callable

import pygame

import config
from level import tiles

Color = tuple[int, int, int]
TILE = config.TILE_SIZE

# Цветове на героя по форма: (външен пламък, вътрешно ядро, акцент/шал).
HERO_COLORS: dict[str, tuple[Color, Color, Color]] = {
    "small": ((255, 132, 40), (255, 222, 120), (60, 180, 170)),
    "big": ((255, 116, 32), (255, 214, 100), (60, 180, 170)),
    "flame": ((70, 150, 255), (205, 240, 255), (255, 170, 60)),
}
HERO_FRAMES = {"idle": 4, "run": 4, "jump": 1, "fall": 1, "hurt": 1, "dead": 1}
EYE_WHITE = (255, 255, 255)
EYE_DARK = (40, 24, 40)
OUTLINE = (60, 30, 30)


# ---------------------------------------------------------------------------
# Помощни функции
# ---------------------------------------------------------------------------
def new_surface(width: int, height: int) -> pygame.Surface:
    """Прозрачна повърхност с дадения размер."""
    return pygame.Surface((max(1, width), max(1, height)), pygame.SRCALPHA)


def shade(color: Color, factor: float) -> Color:
    """Изсветлява (factor > 1) или затъмнява (factor < 1) цвят."""
    return tuple(max(0, min(255, round(channel * factor))) for channel in color)  # type: ignore


def mix(first: Color, second: Color, amount: float) -> Color:
    """Линейно смесване на два цвята (amount=0 → first, 1 → second)."""
    return tuple(round(a + (b - a) * amount) for a, b in zip(first, second))  # type: ignore


def vertical_gradient(width: int, height: int, top: Color, bottom: Color) -> pygame.Surface:
    """Повърхност с вертикален градиент."""
    surface = pygame.Surface((width, height))
    for y in range(height):
        pygame.draw.line(surface, mix(top, bottom, y / max(1, height - 1)), (0, y), (width, y))
    return surface


def glow(radius: int, color: Color, strength: int = 90) -> pygame.Surface:
    """Мек ореол – концентрични полупрозрачни кръгове."""
    surface = new_surface(radius * 2, radius * 2)
    for step in range(radius, 0, -2):
        alpha = round(strength * (1 - step / radius) ** 1.5)
        pygame.draw.circle(surface, (*color, alpha), (radius, radius), step)
    return surface


def flame_polygon(cx: float, bottom: float, width: float, height: float,
                  sway: float = 0.0) -> list[tuple[float, float]]:
    """Точки на форма „пламък/капка“: кръгла основа и остър, леко наклонен връх."""
    points = []
    for index in range(24):
        angle = math.pi * 2 * index / 24
        x = math.sin(angle) * width / 2
        y = -math.cos(angle)
        if y > 0:   # горната половина се издължава към върха
            lift = y ** 1.6
            x *= (1 - lift) ** 0.8
            points.append((cx + x + sway * lift, bottom - width / 2 - lift * (height - width / 2)))
        else:
            points.append((cx + x, bottom - width / 2 - y * width / 2))
    return points


# ---------------------------------------------------------------------------
# Героят
# ---------------------------------------------------------------------------
def draw_hero(form: str, anim: str, frame: int) -> pygame.Surface:
    """Рисува Искрица (лице надясно).

    Args:
        form: "small", "big" или "flame".
        anim: idle, run, jump, fall, hurt, dead.
        frame: номер на кадъра в анимацията.
    """
    big = form != "small"
    width, height = (36, 64) if big else (32, 38)
    body_h = config.PLAYER_BIG_HEIGHT if big else config.PLAYER_SMALL_HEIGHT
    outer, inner, accent = HERO_COLORS[form]
    surface = new_surface(width, height)
    cx = width / 2
    phase = frame / max(1, HERO_FRAMES[anim]) * math.pi * 2
    stretch = {"jump": (0.88, 1.08), "fall": (1.08, 0.95)}.get(anim, (1.0, 1.0))
    breath = math.sin(phase) * 1.2 if anim == "idle" else 0.0
    bob = abs(math.sin(phase)) * 2 if anim == "run" else 0.0
    feet_y = height - 4
    _draw_feet(surface, cx, feet_y, anim, phase)
    body_w = (26 if big else 22) * stretch[0]
    flame_h = (body_h + 6) * stretch[1] + breath
    sway = math.sin(phase + 1) * 3 - (3 if anim == "run" else 0)
    bottom = feet_y - 1 - bob
    pygame.draw.polygon(surface, OUTLINE, flame_polygon(cx, bottom + 1, body_w + 2,
                                                        flame_h + 2, sway))
    pygame.draw.polygon(surface, outer, flame_polygon(cx, bottom, body_w, flame_h, sway))
    pygame.draw.polygon(surface, inner, flame_polygon(cx + 1, bottom - 2, body_w * 0.6,
                                                      flame_h * 0.62, sway * 0.6))
    if big:
        scarf_y = bottom - body_w * 0.42
        pygame.draw.ellipse(surface, accent, (cx - body_w / 2 + 1, scarf_y, body_w - 2, 6))
        pygame.draw.polygon(surface, accent, [(cx - 6, scarf_y + 3), (cx - 13, scarf_y + 10),
                                              (cx - 8, scarf_y + 11)])
    _draw_hero_eyes(surface, cx + 2, bottom - body_w * 0.62, anim)
    return surface


def _draw_feet(surface: pygame.Surface, cx: float, feet_y: float, anim: str,
               phase: float) -> None:
    """Две малки крачета; при тичане се редуват."""
    if anim == "dead":
        return
    swing = math.sin(phase) * 4 if anim == "run" else 0.0
    lift_a = max(0.0, math.sin(phase)) * 3 if anim == "run" else 0.0
    lift_b = max(0.0, -math.sin(phase)) * 3 if anim == "run" else 0.0
    spread = 3 if anim in ("jump", "fall") else 0
    pygame.draw.ellipse(surface, OUTLINE, (cx - 9 + swing - spread, feet_y - 3 - lift_a, 8, 5))
    pygame.draw.ellipse(surface, OUTLINE, (cx + 1 - swing + spread, feet_y - 3 - lift_b, 8, 5))


def _draw_hero_eyes(surface: pygame.Surface, cx: float, eye_y: float, anim: str) -> None:
    """Очите показват настроението: нормални, стиснати (удар) или X (смърт)."""
    for offset in (-3, 4):
        x = cx + offset
        if anim == "hurt":
            pygame.draw.line(surface, EYE_DARK, (x - 2, eye_y - 2), (x + 2, eye_y), 2)
            pygame.draw.line(surface, EYE_DARK, (x - 2, eye_y + 2), (x + 2, eye_y), 2)
        elif anim == "dead":
            pygame.draw.line(surface, EYE_DARK, (x - 2, eye_y - 2), (x + 2, eye_y + 2), 2)
            pygame.draw.line(surface, EYE_DARK, (x - 2, eye_y + 2), (x + 2, eye_y - 2), 2)
        else:
            look_up = -1 if anim == "jump" else (1 if anim == "fall" else 0)
            pygame.draw.ellipse(surface, EYE_WHITE, (x - 2.5, eye_y - 4, 5, 8))
            pygame.draw.ellipse(surface, EYE_DARK, (x - 0.5, eye_y - 2 + look_up, 3, 4))


# ---------------------------------------------------------------------------
# Врагове
# ---------------------------------------------------------------------------
def draw_walker(frame: int) -> pygame.Surface:
    """Мъхчо – мъхест бръмбар с черупка (2 кадъра ходене)."""
    surface = new_surface(32, 28)
    shell, dark = (96, 150, 60), (50, 90, 40)
    legs = (-3, 3) if frame % 2 else (3, -3)
    for index, x in enumerate((8, 16, 22)):
        pygame.draw.line(surface, OUTLINE, (x, 20), (x + legs[index % 2], 27), 3)
    pygame.draw.ellipse(surface, OUTLINE, (1, 5, 30, 20))
    pygame.draw.ellipse(surface, shell, (2, 6, 28, 18))
    pygame.draw.rect(surface, (0, 0, 0, 0), (0, 17, 32, 11))
    pygame.draw.ellipse(surface, (160, 110, 70), (6, 14, 22, 10))
    for spot in ((9, 10), (16, 8), (22, 11)):
        pygame.draw.circle(surface, dark, spot, 2)
    pygame.draw.circle(surface, EYE_WHITE, (25, 16), 4)
    pygame.draw.circle(surface, EYE_DARK, (26, 16), 2)
    pygame.draw.line(surface, EYE_DARK, (21, 11), (28, 13), 2)
    return surface


def draw_hopper(frame: int) -> pygame.Surface:
    """Скокльо – кръгло лилаво създание с големи очи (0 = клекнал, 1 = в скок)."""
    surface = new_surface(32, 32)
    body, belly = (150, 80, 190), (220, 170, 230)
    squash = (30, 20) if frame == 0 else (24, 28)
    rect = pygame.Rect(0, 0, *squash)
    rect.midbottom = (16, 32)
    pygame.draw.ellipse(surface, OUTLINE, rect.inflate(2, 2))
    pygame.draw.ellipse(surface, body, rect)
    pygame.draw.ellipse(surface, belly, rect.inflate(-12, -10).move(2, 4))
    for x in (rect.centerx - 5, rect.centerx + 5):
        pygame.draw.circle(surface, EYE_WHITE, (x, rect.top + 5), 5)
        pygame.draw.circle(surface, EYE_DARK, (x + 2, rect.top + 5), 2)
    return surface


def draw_flyer(frame: int) -> pygame.Surface:
    """Нощниче – нощна пеперуда с пърхащи криле (3 кадъра)."""
    surface = new_surface(36, 28)
    wing, body = (120, 90, 170), (60, 40, 80)
    lift = (-8, 0, 8)[frame % 3]
    for side in (-1, 1):
        tip = (18 + side * 17, 12 + lift)
        pygame.draw.polygon(surface, wing, [(18, 12), tip, (18 + side * 12, 22)])
        pygame.draw.circle(surface, (230, 200, 120), (18 + side * 10, 14 + lift // 2), 2)
    pygame.draw.ellipse(surface, OUTLINE, (11, 6, 16, 18))
    pygame.draw.ellipse(surface, body, (12, 7, 14, 16))
    pygame.draw.circle(surface, (255, 220, 90), (22, 12), 3)
    pygame.draw.circle(surface, EYE_DARK, (23, 12), 1)
    pygame.draw.line(surface, body, (20, 7), (25, 1), 1)
    return surface


def draw_shooter(frame: int) -> pygame.Surface:
    """Бодлоцвет – бодливо цвете, което плюе семена (1 = отворена уста)."""
    surface = new_surface(32, 34)
    stem, head, petal = (60, 130, 60), (190, 60, 90), (240, 120, 150)
    pygame.draw.rect(surface, stem, (14, 16, 4, 18))
    pygame.draw.ellipse(surface, stem, (4, 22, 11, 6))
    pygame.draw.ellipse(surface, stem, (17, 24, 11, 6))
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        pygame.draw.circle(surface, petal, (16 + math.cos(rad) * 9, 11 + math.sin(rad) * 9), 5)
    pygame.draw.circle(surface, OUTLINE, (16, 11), 9)
    pygame.draw.circle(surface, head, (16, 11), 8)
    mouth = pygame.Rect(18, 8, 8, 6 if frame else 2)
    pygame.draw.ellipse(surface, EYE_DARK, mouth)
    pygame.draw.circle(surface, EYE_WHITE, (15, 8), 2)
    return surface


def draw_boss(phase: int, frame: int) -> pygame.Surface:
    """Сенкоглав – голяма сянка с корона от рога; очите сменят цвета си по фази."""
    surface = new_surface(76, 76)
    eye_colors = ((255, 220, 90), (255, 140, 60), (255, 60, 80))
    body = (50, 30, 70)
    wobble = math.sin(frame * math.pi / 2) * 2
    pygame.draw.ellipse(surface, (20, 10, 30), (6, 16 + wobble, 64, 60 - wobble))
    pygame.draw.ellipse(surface, body, (8, 18 + wobble, 60, 56 - wobble))
    for x in (18, 38, 58):
        pygame.draw.polygon(surface, (200, 170, 90), [(x - 7, 24), (x, 2 + wobble), (x + 7, 24)])
    eye = eye_colors[min(phase, 2)]
    for x in (30, 50):
        pygame.draw.ellipse(surface, eye, (x - 6, 36, 12, 9))
        pygame.draw.ellipse(surface, EYE_DARK, (x - 1, 38, 5, 5))
    pygame.draw.arc(surface, eye, (26, 48, 28, 14), math.pi * 1.1, math.pi * 1.9, 3)
    return surface


# ---------------------------------------------------------------------------
# Предмети, снаряди и обекти
# ---------------------------------------------------------------------------
def draw_coin(frame: int) -> pygame.Surface:
    """Искра-монета, която се върти (ширината следва |cos|)."""
    surface = new_surface(20, 20)
    width = max(3, round(16 * abs(math.cos(frame / 8 * math.pi))))
    rect = pygame.Rect(0, 0, width, 18)
    rect.center = (10, 10)
    pygame.draw.ellipse(surface, (170, 110, 20), rect)
    pygame.draw.ellipse(surface, (255, 205, 60), rect.inflate(-2, -2))
    if width > 8:
        pygame.draw.ellipse(surface, (255, 245, 170), rect.inflate(-width // 2, -8))
    return surface


def draw_crystal(frame: int) -> pygame.Surface:
    """Голям слънчев кристал – шестоъгълен скъпоценен камък с проблясък."""
    surface = new_surface(26, 32)
    points = [(13, 1), (24, 9), (24, 22), (13, 31), (2, 22), (2, 9)]
    pygame.draw.polygon(surface, (40, 110, 160), points)
    pygame.draw.polygon(surface, (110, 220, 255), [(13, 3), (22, 10), (13, 16), (4, 10)])
    pygame.draw.polygon(surface, (60, 170, 220), [(4, 10), (13, 16), (13, 29), (4, 21)])
    pygame.draw.polygon(surface, (220, 250, 255), points, 2)
    sparkle = (6 + frame * 4) % 20
    pygame.draw.line(surface, EYE_WHITE, (sparkle, 6), (sparkle + 3, 3), 2)
    return surface


def draw_ember() -> pygame.Surface:
    """Жарава – power-up за голяма форма: топла светеща топка."""
    surface = new_surface(28, 28)
    surface.blit(glow(14, (255, 170, 60)), (0, 0))
    pygame.draw.circle(surface, (230, 90, 30), (14, 16), 8)
    pygame.draw.circle(surface, (255, 200, 90), (13, 15), 5)
    pygame.draw.polygon(surface, (255, 150, 40), flame_polygon(14, 12, 7, 12, 2))
    return surface


def draw_flame_item() -> pygame.Surface:
    """Пламък – power-up за изстрелване на искрови заряди: син огън."""
    surface = new_surface(28, 28)
    surface.blit(glow(14, (120, 180, 255)), (0, 0))
    pygame.draw.polygon(surface, (60, 130, 255), flame_polygon(14, 25, 14, 22, 3))
    pygame.draw.polygon(surface, (210, 240, 255), flame_polygon(14, 24, 7, 12, 1))
    return surface


def draw_comet(frame: int) -> pygame.Surface:
    """Комета – временна неуязвимост: блестящо ядро с опашка."""
    surface = new_surface(30, 30)
    colors = ((255, 250, 200), (255, 200, 240), (200, 240, 255))
    color = colors[frame % len(colors)]
    for index in range(3):
        start = (6 + index * 3, 22 - index * 6)
        pygame.draw.line(surface, (*color, 150), start, (start[0] - 6, start[1] + 6), 3)
    surface.blit(glow(10, color), (10, 2))
    pygame.draw.circle(surface, color, (20, 12), 7)
    pygame.draw.circle(surface, EYE_WHITE, (21, 11), 3)
    return surface


def draw_lantern(size: int = 24) -> pygame.Surface:
    """Фенерче – допълнителен живот (използва се и като икона в HUD)."""
    surface = new_surface(size, size)
    scale = size / 24
    frame = pygame.Rect(round(5 * scale), round(7 * scale), round(14 * scale), round(15 * scale))
    pygame.draw.arc(surface, (90, 70, 50), (round(7 * scale), 0, round(10 * scale),
                                            round(12 * scale)), 0, math.pi, 2)
    pygame.draw.rect(surface, (90, 70, 50), frame, border_radius=3)
    pygame.draw.rect(surface, (255, 200, 90), frame.inflate(-4, -4), border_radius=2)
    pygame.draw.circle(surface, (255, 120, 40), frame.center, max(2, round(3 * scale)))
    return surface


def draw_projectile(kind: str, frame: int) -> pygame.Surface:
    """Снаряди: искров заряд на героя, семе-бодил и сенчесто кълбо на боса."""
    colors = {"fireball": ((90, 160, 255), (230, 250, 255)),
              "thorn": ((60, 120, 40), (170, 220, 90)),
              "boss_orb": ((120, 40, 160), (230, 150, 255))}
    outer, inner = colors[kind]
    surface = new_surface(18, 18)
    if kind == "thorn":
        for angle in range(0, 360, 60):
            rad = math.radians(angle + frame * 30)
            tip = (9 + math.cos(rad) * 8, 9 + math.sin(rad) * 8)
            pygame.draw.line(surface, outer, (9, 9), tip, 2)
    else:
        surface.blit(glow(9, inner, 120), (0, 0))
    pygame.draw.circle(surface, outer, (9, 9), 5 + frame % 2)
    pygame.draw.circle(surface, inner, (8, 8), 3)
    return surface


def draw_checkpoint(active: bool) -> pygame.Surface:
    """Чекпойнт – стълб с фенер: сив, докато не бъде запален."""
    surface = new_surface(28, 64)
    pygame.draw.rect(surface, (90, 70, 60), (12, 18, 4, 46))
    pygame.draw.rect(surface, (70, 55, 50), (6, 60, 16, 4))
    light = (255, 200, 80) if active else (120, 120, 130)
    if active:
        surface.blit(glow(14, (255, 190, 80)), (0, 0))
    pygame.draw.rect(surface, (80, 60, 50), (7, 4, 14, 16), border_radius=3)
    pygame.draw.rect(surface, light, (9, 6, 10, 12), border_radius=2)
    return surface


def draw_exit(is_open: bool, frame: int) -> pygame.Surface:
    """Изход – каменна арка с въртяща се светлина (затворена с решетка, докато босът е жив)."""
    surface = new_surface(44, 70)
    stone = (120, 110, 130)
    pygame.draw.rect(surface, stone, (2, 16, 8, 54))
    pygame.draw.rect(surface, stone, (34, 16, 8, 54))
    pygame.draw.arc(surface, stone, (2, 0, 40, 36), 0, math.pi, 8)
    inner = pygame.Rect(10, 10, 24, 60)
    if is_open:
        pygame.draw.ellipse(surface, (255, 230, 150), inner)
        for index in range(3):
            angle = frame * 0.6 + index * 2.1
            start = math.pi * 2 * index / 3 + angle
            pygame.draw.arc(surface, (255, 255, 255), inner.inflate(-6, -10), start, start + 1.4, 2)
    else:
        pygame.draw.ellipse(surface, (30, 20, 40), inner)
        for x in range(13, 34, 6):
            pygame.draw.line(surface, (90, 80, 90), (x, 12), (x, 70), 2)
    return surface


def draw_platform(kind: str, width: int, background: str) -> pygame.Surface:
    """Движеща се (дъска с нитове) или пропадаща (напукана дъска) платформа."""
    palette = config.PALETTES[background]
    base = palette["platform"] if kind != "platform_falling" else shade(palette["brick"], 0.9)
    height = config.PLATFORM_THICKNESS + 4
    surface = new_surface(width, height)
    pygame.draw.rect(surface, shade(base, 0.6), (0, 2, width, height - 2), border_radius=4)
    pygame.draw.rect(surface, base, (0, 0, width, height - 4), border_radius=4)
    pygame.draw.line(surface, shade(base, 1.3), (3, 2), (width - 4, 2), 2)
    if kind == "platform_falling":
        for x in range(10, width, 22):
            pygame.draw.lines(surface, shade(base, 0.5), False, [(x, 1), (x + 4, 6), (x + 1, 11)])
    else:
        for x in (6, width - 7):
            pygame.draw.circle(surface, shade(base, 0.5), (x, 7), 2)
    return surface


# ---------------------------------------------------------------------------
# Тайлове
# ---------------------------------------------------------------------------
def draw_solid_tile(background: str, top_exposed: bool, seed: int) -> pygame.Surface:
    """Земя/камък/тухли според света; горният ред получава „трева“."""
    palette = config.PALETTES[background]
    surface = pygame.Surface((TILE, TILE))
    surface.fill(palette["ground"])
    rng = random.Random(seed)
    if background == "castle":
        _draw_bricks(surface, palette["ground"], palette["ground_dark"])
    else:
        for _ in range(6):
            x, y = rng.randrange(2, TILE - 4), rng.randrange(8, TILE - 3)
            pygame.draw.rect(surface, palette["ground_dark"], (x, y, 3, 2))
    pygame.draw.line(surface, palette["ground_dark"], (0, TILE - 1), (TILE, TILE - 1))
    if top_exposed:
        _draw_tile_top(surface, background, palette, rng)
    return surface


def _draw_bricks(surface: pygame.Surface, face: Color, mortar: Color) -> None:
    """Зидария от тухли, разместени през ред."""
    brick_h = TILE // 4
    for row in range(4):
        y = row * brick_h
        pygame.draw.line(surface, mortar, (0, y), (TILE, y))
        shift = 0 if row % 2 == 0 else TILE // 2
        for x in (shift, shift + TILE // 2):
            pygame.draw.line(surface, mortar, (x % TILE, y), (x % TILE, y + brick_h))
        pygame.draw.line(surface, shade(face, 1.12), (0, y + 1), (TILE, y + 1))


def _draw_tile_top(surface: pygame.Surface, background: str, palette: dict[str, Color],
                   rng: random.Random) -> None:
    """Горен ръб: трева (гора), светещ мъх (пещера) или каменен корниз (крепост)."""
    top = palette["ground_top"]
    if background == "castle":
        pygame.draw.rect(surface, top, (0, 0, TILE, 6))
        pygame.draw.line(surface, shade(top, 1.2), (0, 0), (TILE, 0), 2)
        return
    pygame.draw.rect(surface, top, (0, 0, TILE, 6))
    pygame.draw.rect(surface, shade(top, 0.75), (0, 6, TILE, 2))
    for _ in range(5):
        x = rng.randrange(0, TILE - 3)
        pygame.draw.polygon(surface, top, [(x, 8), (x + 2, 10 + rng.randrange(3)), (x + 4, 8)])


def draw_one_way_tile(background: str) -> pygame.Surface:
    """Тънка дъска с подпори – минава се отдолу."""
    palette = config.PALETTES[background]
    surface = new_surface(TILE, TILE)
    wood = palette["platform"]
    pygame.draw.rect(surface, shade(wood, 0.6), (0, 2, TILE, 9))
    pygame.draw.rect(surface, wood, (0, 0, TILE, 8))
    pygame.draw.line(surface, shade(wood, 1.25), (0, 1), (TILE, 1))
    for x in (5, TILE - 8):
        pygame.draw.line(surface, shade(wood, 0.5), (x, 10), (x + 3, 18), 2)
    return surface


def draw_surprise_tile(background: str, frame: int) -> pygame.Surface:
    """Руническа плоча със светещ знак-искра – крие изненада."""
    palette = config.PALETTES[background]
    surface = pygame.Surface((TILE, TILE))
    stone = (200, 150, 60)
    surface.fill(shade(stone, 0.7))
    pygame.draw.rect(surface, stone, (2, 2, TILE - 4, TILE - 4))
    pygame.draw.line(surface, shade(stone, 1.3), (2, 2), (TILE - 3, 2), 2)
    brightness = 0.8 + 0.2 * math.sin(frame / 4 * math.pi * 2)
    rune = shade(palette["accent"], brightness * 1.1)
    center = (TILE // 2, TILE // 2)
    pygame.draw.circle(surface, rune, center, 5)
    for angle in range(0, 360, 90):
        rad = math.radians(angle + 45)
        pygame.draw.line(surface, rune, (center[0] + math.cos(rad) * 7, center[1] + math.sin(rad) * 7),
                         (center[0] + math.cos(rad) * 11, center[1] + math.sin(rad) * 11), 2)
    for corner in ((4, 4), (TILE - 5, 4), (4, TILE - 5), (TILE - 5, TILE - 5)):
        pygame.draw.circle(surface, shade(stone, 0.6), corner, 1)
    return surface


def draw_used_tile(background: str) -> pygame.Surface:
    """Изразходвана плоча – угаснала."""
    base = config.PALETTES[background]["ground_dark"]
    surface = pygame.Surface((TILE, TILE))
    surface.fill(shade(base, 0.8))
    pygame.draw.rect(surface, base, (2, 2, TILE - 4, TILE - 4))
    return surface


def draw_breakable_tile(background: str) -> pygame.Surface:
    """Чуплив блок – напукани тухли."""
    brick = config.PALETTES[background]["brick"]
    surface = pygame.Surface((TILE, TILE))
    surface.fill(brick)
    _draw_bricks(surface, brick, shade(brick, 0.55))
    pygame.draw.lines(surface, shade(brick, 0.45), False, [(6, 4), (11, 12), (8, 20), (14, 27)])
    return surface


def draw_spikes_tile() -> pygame.Surface:
    """Три метални шипа в долната част на клетката."""
    surface = new_surface(TILE, TILE)
    base_y = TILE
    tip_y = TILE - config.SPIKE_HITBOX_HEIGHT
    for index in range(3):
        left = index * TILE / 3
        points = [(left + 1, base_y), (left + TILE / 6, tip_y), (left + TILE / 3 - 1, base_y)]
        pygame.draw.polygon(surface, (200, 205, 215), points)
        pygame.draw.polygon(surface, (110, 115, 130), points, 1)
    return surface


def draw_lava_tile(frame: int, surface_row: bool) -> pygame.Surface:
    """Лава с вълнист горен ръб (4 кадъра анимация)."""
    surface = new_surface(TILE, TILE)
    top = TILE - config.LAVA_HITBOX_HEIGHT if surface_row else 0
    pygame.draw.rect(surface, (200, 60, 20), (0, top, TILE, TILE - top))
    if surface_row:
        points = [(x, top + 3 + math.sin((x + frame * 8) / 5) * 3) for x in range(0, TILE + 1, 2)]
        pygame.draw.polygon(surface, (255, 140, 40), [(0, TILE), *points, (TILE, TILE)])
        pygame.draw.polygon(surface, (200, 60, 20), [(0, TILE), *[(x, y + 6) for x, y in points],
                                                     (TILE, TILE)])
        pygame.draw.circle(surface, (255, 210, 90), ((frame * 7) % TILE, top + 10), 2)
    return surface


# ---------------------------------------------------------------------------
# Фон с паралакс
# ---------------------------------------------------------------------------
LAYER_WIDTH = 1024


def draw_background_layers(background: str) -> list[pygame.Surface]:
    """Три прозрачни слоя (далечен, среден, близък), които се повтарят хоризонтално."""
    palette = config.PALETTES[background]
    rng = random.Random(background)
    painters: dict[str, tuple[Callable[..., None], ...]] = {
        "forest": (_paint_hills, _paint_pines, _paint_bushes),
        "cave": (_paint_stalactites, _paint_pillars, _paint_crystals),
        "castle": (_paint_mountains, _paint_towers, _paint_pillars),
    }
    layers = []
    for painter, key in zip(painters[background], ("far", "mid", "near")):
        layer = new_surface(LAYER_WIDTH, config.SCREEN_HEIGHT)
        painter(layer, palette[key], rng)
        layers.append(layer)
    return layers


def _wrap_x(layer: pygame.Surface, x: float, draw: Callable[[float], None]) -> None:
    """Рисува фигура и копие от другата страна, за да се повтаря слоят без шев."""
    draw(x)
    draw(x - layer.get_width())
    draw(x + layer.get_width())


def _paint_hills(layer: pygame.Surface, color: Color, rng: random.Random) -> None:
    """Меки хълмове – сума от синусоиди с цял брой периоди (за да се повтарят)."""
    height = layer.get_height()
    points = [(0, height)]
    for x in range(0, LAYER_WIDTH + 1, 8):
        wave = math.sin(x / LAYER_WIDTH * math.pi * 4) * 30 + math.sin(x / LAYER_WIDTH * math.pi * 10) * 12
        points.append((x, height * 0.55 + wave))
    points.append((LAYER_WIDTH, height))
    pygame.draw.polygon(layer, color, points)


def _paint_pines(layer: pygame.Surface, color: Color, rng: random.Random) -> None:
    """Силуети на иглолистни дървета."""
    height = layer.get_height()
    for _ in range(18):
        x, size = rng.uniform(0, LAYER_WIDTH), rng.uniform(40, 80)
        base = height * 0.78 + rng.uniform(-10, 20)

        def tree(px: float, s: float = size, b: float = base) -> None:
            pygame.draw.rect(layer, shade(color, 0.7), (px - 3, b - 4, 6, height - b + 4))
            for tier in range(3):
                top = b - s * (0.5 + tier * 0.3)
                pygame.draw.polygon(layer, color, [(px - s / 2.5 + tier * 4, b - tier * s * 0.28),
                                                   (px, top), (px + s / 2.5 - tier * 4, b - tier * s * 0.28)])
        _wrap_x(layer, x, tree)
    pygame.draw.rect(layer, color, (0, height * 0.86, LAYER_WIDTH, height))


def _paint_bushes(layer: pygame.Surface, color: Color, rng: random.Random) -> None:
    """Храсти и туфи трева най-отпред."""
    height = layer.get_height()
    for _ in range(14):
        x, radius = rng.uniform(0, LAYER_WIDTH), rng.uniform(18, 34)

        def bush(px: float, r: float = radius) -> None:
            for dx in (-r * 0.8, 0, r * 0.8):
                pygame.draw.circle(layer, color, (px + dx, height - r * 0.4), r * 0.75)
        _wrap_x(layer, x, bush)


def _paint_stalactites(layer: pygame.Surface, color: Color, rng: random.Random) -> None:
    """Сталактити отгоре и сталагмити отдолу."""
    height = layer.get_height()
    for _ in range(26):
        x, length, width = rng.uniform(0, LAYER_WIDTH), rng.uniform(60, 180), rng.uniform(20, 50)

        def spike(px: float, ln: float = length, w: float = width) -> None:
            pygame.draw.polygon(layer, color, [(px - w / 2, 0), (px, ln), (px + w / 2, 0)])
            pygame.draw.polygon(layer, color, [(px - w / 2, height), (px + 7, height - ln * 0.8),
                                               (px + w / 2, height)])
        _wrap_x(layer, x, spike)


def _paint_pillars(layer: pygame.Surface, color: Color, rng: random.Random) -> None:
    """Каменни колони."""
    height = layer.get_height()
    for _ in range(7):
        x, width = rng.uniform(0, LAYER_WIDTH), rng.uniform(30, 60)

        def pillar(px: float, w: float = width) -> None:
            pygame.draw.rect(layer, color, (px, height * 0.25, w, height))
            pygame.draw.rect(layer, shade(color, 1.2), (px - 6, height * 0.25, w + 12, 12))
            pygame.draw.line(layer, shade(color, 0.8), (px + w * 0.3, height * 0.3),
                             (px + w * 0.3, height), 3)
        _wrap_x(layer, x, pillar)


def _paint_crystals(layer: pygame.Surface, color: Color, rng: random.Random) -> None:
    """Светещи кристали по земята на пещерата."""
    height = layer.get_height()
    glow_color = config.PALETTES["cave"]["accent"]
    for _ in range(12):
        x, size = rng.uniform(0, LAYER_WIDTH), rng.uniform(20, 45)

        def crystal(px: float, s: float = size) -> None:
            pygame.draw.polygon(layer, color, [(px - s / 3, height), (px, height - s * 1.6),
                                               (px + s / 3, height)])
            pygame.draw.line(layer, (*glow_color, 140), (px, height - s * 1.5), (px, height), 2)
        _wrap_x(layer, x, crystal)


def _paint_mountains(layer: pygame.Surface, color: Color, rng: random.Random) -> None:
    """Назъбени планини и бледа луна."""
    height = layer.get_height()
    pygame.draw.circle(layer, (240, 200, 190, 120), (LAYER_WIDTH * 0.7, height * 0.2), 40)
    points = [(0, height)]
    for index in range(17):
        points.append((index * LAYER_WIDTH / 16, height * (0.45 + 0.15 * ((index * 7) % 3) / 2)))
    points.append((LAYER_WIDTH, height))
    pygame.draw.polygon(layer, color, points)


def _paint_towers(layer: pygame.Surface, color: Color, rng: random.Random) -> None:
    """Кули с бойници."""
    height = layer.get_height()
    for _ in range(6):
        x, width, top = rng.uniform(0, LAYER_WIDTH), rng.uniform(50, 90), rng.uniform(0.3, 0.55)

        def tower(px: float, w: float = width, t: float = top) -> None:
            y = height * t
            pygame.draw.rect(layer, color, (px, y, w, height - y))
            for merlon in range(0, round(w), 16):
                pygame.draw.rect(layer, color, (px + merlon, y - 10, 9, 10))
            pygame.draw.rect(layer, (255, 180, 90, 160), (px + w / 2 - 4, y + 30, 8, 14))
        _wrap_x(layer, x, tower)


# ---------------------------------------------------------------------------
# Кеш
# ---------------------------------------------------------------------------
class Assets:
    """Кешира генерираните спрайтове, за да се рисуват само веднъж."""

    def __init__(self) -> None:
        self._cache: dict[tuple, pygame.Surface] = {}
        self._backgrounds: dict[str, tuple[pygame.Surface, list[pygame.Surface]]] = {}

    def _get(self, key: tuple, factory: Callable[[], pygame.Surface],
             facing: int = 1) -> pygame.Surface:
        """Взима от кеша или създава; при facing=-1 връща огледален образ."""
        full_key = (*key, facing)
        if full_key not in self._cache:
            if facing < 0:
                self._cache[full_key] = pygame.transform.flip(self._get(key, factory), True, False)
            else:
                self._cache[full_key] = factory()
        return self._cache[full_key]

    def player(self, form: str, anim: str, frame: int, facing: int) -> pygame.Surface:
        """Кадър от анимацията на героя."""
        frame %= HERO_FRAMES[anim]
        return self._get(("hero", form, anim, frame), lambda: draw_hero(form, anim, frame), facing)

    def enemy(self, kind: str, frame: int, facing: int, phase: int = 0) -> pygame.Surface:
        """Кадър на враг."""
        painters: dict[str, Callable[[], pygame.Surface]] = {
            "walker": lambda: draw_walker(frame % 2),
            "hopper": lambda: draw_hopper(frame % 2),
            "flyer": lambda: draw_flyer(frame % 3),
            "shooter": lambda: draw_shooter(frame % 2),
            "boss": lambda: draw_boss(phase, frame % 4),
        }
        return self._get(("enemy", kind, frame, phase), painters[kind], facing)

    def item(self, kind: str, frame: int = 0) -> pygame.Surface:
        """Предмет или снаряд."""
        painters: dict[str, Callable[[], pygame.Surface]] = {
            "coin": lambda: draw_coin(frame % 8),
            "crystal": lambda: draw_crystal(frame % 5),
            "powerup": draw_ember,
            "flame": draw_flame_item,
            "comet": lambda: draw_comet(frame % 3),
            "life": draw_lantern,
            "fireball": lambda: draw_projectile("fireball", frame % 2),
            "thorn": lambda: draw_projectile("thorn", frame % 2),
            "boss_orb": lambda: draw_projectile("boss_orb", frame % 2),
        }
        return self._get(("item", kind, frame), painters[kind])

    def checkpoint(self, active: bool) -> pygame.Surface:
        """Чекпойнт (запален или не)."""
        return self._get(("checkpoint", active), lambda: draw_checkpoint(active))

    def exit_portal(self, is_open: bool, frame: int) -> pygame.Surface:
        """Изходът."""
        frame %= 8
        return self._get(("exit", is_open, frame), lambda: draw_exit(is_open, frame))

    def platform(self, kind: str, width: int, background: str) -> pygame.Surface:
        """Движеща се или пропадаща платформа."""
        return self._get(("platform", kind, width, background),
                         lambda: draw_platform(kind, width, background))

    def lantern_icon(self, size: int) -> pygame.Surface:
        """Икона за живот в HUD."""
        return self._get(("lantern", size), lambda: draw_lantern(size))

    def tile(self, symbol: str, background: str, top_exposed: bool, frame: int,
             col: int) -> pygame.Surface | None:
        """Спрайт на тайл или None за празна клетка."""
        if symbol == tiles.EMPTY:
            return None
        if symbol == tiles.SOLID:
            seed = col % 4
            return self._get(("solid", background, top_exposed, seed),
                             lambda: draw_solid_tile(background, top_exposed, seed))
        if symbol in tiles.SURPRISE_CONTENTS:
            return self._get(("surprise", background, frame % 4),
                             lambda: draw_surprise_tile(background, frame % 4))
        if symbol == tiles.LAVA:
            return self._get(("lava", frame % 4, top_exposed),
                             lambda: draw_lava_tile(frame % 4, top_exposed))
        simple: dict[str, Callable[[], pygame.Surface]] = {
            tiles.ONE_WAY: lambda: draw_one_way_tile(background),
            tiles.USED_BLOCK: lambda: draw_used_tile(background),
            tiles.BREAKABLE: lambda: draw_breakable_tile(background),
            tiles.SPIKES: draw_spikes_tile,
        }
        return self._get(("tile", symbol, background), simple[symbol])

    def background(self, background: str) -> tuple[pygame.Surface, list[pygame.Surface]]:
        """Небе (градиент с размера на екрана) и трите паралакс слоя."""
        if background not in self._backgrounds:
            palette = config.PALETTES[background]
            sky = vertical_gradient(config.SCREEN_WIDTH, config.SCREEN_HEIGHT,
                                    palette["sky_top"], palette["sky_bottom"])
            self._backgrounds[background] = (sky, draw_background_layers(background))
        return self._backgrounds[background]
