"""Проверка дали изходът е достижим от старта („reachability“).

Идея: нивото се превръща в ГРАФ.
* **Възел** е „клетка за стоене“ – празна клетка, под която има опора (земя,
  one-way платформа или траекторията на подвижна платформа).
* **Ребро** A → B съществува, ако героят може да стигне от A до B: като ходи до
  съседна клетка, като скочи или като слезе от ръба.

Дали даден скок е възможен НЕ гадаем с формули „на око“. Симулираме го със
същите константи (`GRAVITY`, `JUMP_VELOCITY`, `AIR_ACCELERATION`...) и със
същата функция за колизии `move_body`, която ползва и самата игра. Така, ако
променим физиката в config.py, проверката автоматично се съобразява.

Началната хоризонтална скорост зависи от засилването: от покой, с ускорение a,
на разстояние s се достига v = √(2·a·s) (ограничено до максималната скорост).

Накрая BFS (търсене в ширина) обхожда графа от старта. Ако стигне клетката на
изхода – нивото е проходимо. Сложност: O(V · P · S), където V е броят клетки за
стоене, P е броят на пробните скокове от клетка (константа ≈ 17), а S е броят
стъпки на симулация на един скок (≤ 180).

Опростявания (консервативни, т.е. по-скоро отхвърляме, отколкото приемаме):
* героят е в малка форма (най-малкият хитбокс);
* враговете се пренебрегват (могат да бъдат победени);
* чупливите блокове се смятат за стени (малката форма не може да ги чупи);
* подвижната платформа се представя като one-way повърхност по целия си път.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

import config
from entities.hazards import touching_hazard
from level import tiles
from level.level import Level, Spawn
from level.tiles import TileType
from physics.body import Body
from physics.collision import move_body
from physics.kinematics import approach, gravity_step

T = config.TILE_SIZE
Cell = tuple[int, int]
MAX_SIMULATION_STEPS = 180          # 3 секунди полет – повече не е нужно
CUT_JUMP_TIME = 0.12                # s, кога „пускаме“ бутона при нисък скок
MAX_RUN_UP_TILES = 20               # по-дълго засилване не променя скоростта
ONE_WAY = tiles.TILE_TYPES[tiles.ONE_WAY]


@dataclass(frozen=True)
class JumpProfile:
    """Един пробен скок.

    Attributes:
        direction: -1 наляво, 1 надясно, 0 право нагоре.
        target_speed: към каква хоризонтална скорост се стреми героят във въздуха.
        launch_vy: начална вертикална скорост (−JUMP_VELOCITY за скок, 0 за слизане).
        cut: дали бутонът за скок се пуска рано (нисък скок).
    """

    direction: int
    target_speed: float
    launch_vy: float
    cut: bool = False


def _build_profiles() -> list[JumpProfile]:
    """Всички пробни движения от една клетка."""
    jump = -config.JUMP_VELOCITY
    speeds = (config.MAX_RUN_SPEED, config.MAX_WALK_SPEED, config.MAX_WALK_SPEED / 2)
    profiles = [JumpProfile(0, 0.0, jump)]
    for direction in (-1, 1):
        for speed in speeds:
            profiles.append(JumpProfile(direction, speed, jump))
            profiles.append(JumpProfile(direction, speed, jump, cut=True))
        profiles.append(JumpProfile(direction, config.MAX_RUN_SPEED, 0.0))
        profiles.append(JumpProfile(direction, config.MAX_WALK_SPEED / 2, 0.0))
    return profiles


PROFILES = _build_profiles()


class ReachGrid:
    """Картата на нивото + „виртуални“ one-way тайлове по пътя на платформите.

    Пази типовете тайлове в списък за бърз достъп (симулацията пита милиони пъти).
    """

    def __init__(self, level: Level) -> None:
        self.level = level
        self.width = level.width
        self.height = level.height
        self.pixel_height = level.pixel_height
        self._rows: list[list[TileType]] = [
            [level.tile_at(col, row) for col in range(level.width)] for row in range(level.height)]
        for col, row in platform_cells(level):
            if 0 <= col < self.width and 0 <= row < self.height and not self._rows[row][col].solid:
                self._rows[row][col] = ONE_WAY

    def tile_at(self, col: int, row: int) -> TileType:
        """Същата семантика като `Level.tile_at` (стени отстрани, празно горе/долу)."""
        if col < 0 or col >= self.width:
            return tiles.TILE_TYPES[tiles.SOLID]
        if row < 0 or row >= self.height:
            return tiles.TILE_TYPES[tiles.EMPTY]
        return self._rows[row][col]

    def is_free(self, col: int, row: int) -> bool:
        """Може ли героят да бъде в тази клетка (не е стена и не е опасна)."""
        tile = self.tile_at(col, row)
        return not (tile.solid or tile.hazard or tile.deadly)

    def is_stand_cell(self, cell: Cell) -> bool:
        """Клетка за стоене: свободна, с опора точно под нея."""
        col, row = cell
        return self.is_free(col, row) and self.tile_at(col, row + 1).supports_standing


def platform_cells(level: Level) -> list[Cell]:
    """Клетките, през които минава горният ръб на всяка подвижна/пропадаща платформа."""
    cells: list[Cell] = []
    travel = config.MOVING_PLATFORM_RANGE_TILES
    for spawn in level.spawns:
        if spawn.kind == "platform_h":
            width = config.MOVING_PLATFORM_WIDTH_TILES + travel
            cells += [(spawn.col + dc, spawn.row) for dc in range(width)]
        elif spawn.kind == "platform_v":
            cells += [(spawn.col + dc, spawn.row - dr)
                      for dc in range(config.MOVING_PLATFORM_WIDTH_TILES)
                      for dr in range(travel + 1)]
        elif spawn.kind == "platform_falling":
            cells += [(spawn.col + dc, spawn.row)
                      for dc in range(config.FALLING_PLATFORM_WIDTH_TILES)]
    return cells


# --- симулация на един скок -----------------------------------------------------
def _start_body(cell: Cell, direction: int) -> Body:
    """Тяло на малкия герой, стоящо в клетката, до ръба по посоката на скока."""
    col, row = cell
    width, height = config.PLAYER_WIDTH, config.PLAYER_SMALL_HEIGHT
    x = col * T + (T - width) / 2
    if direction > 0:
        x = (col + 1) * T - width - config.COLLISION_EPSILON
    elif direction < 0:
        x = col * T + config.COLLISION_EPSILON
    return Body(x, (row + 1) * T - height, width, height)


def _run_up_speed(grid: ReachGrid, cell: Cell, profile: JumpProfile) -> float:
    """Скоростта при отскок според засилването: v = √(2·a·s)."""
    if profile.direction == 0:
        return 0.0
    col, row = cell
    run_up = 1
    while run_up < MAX_RUN_UP_TILES and grid.is_stand_cell((col - profile.direction * run_up, row)):
        run_up += 1
    speed = math.sqrt(2 * config.GROUND_ACCELERATION * run_up * T)
    return profile.direction * min(speed, profile.target_speed)


def _landing_cell(grid: ReachGrid, body: Body) -> Cell | None:
    """Клетката за стоене под тялото след приземяване."""
    row = math.floor(body.bottom / T + 0.5) - 1
    candidates = [math.floor(body.center_x / T), math.floor(body.left / T),
                  math.floor((body.right - config.COLLISION_EPSILON) / T)]
    for col in candidates:
        if grid.is_stand_cell((col, row)):
            return col, row
    return None


def simulate_jump(grid: ReachGrid, cell: Cell, profile: JumpProfile) -> Cell | None:
    """Симулира един скок от клетка и връща клетката на приземяване (или None).

    None означава: героят е паднал в пропаст, докоснал е опасност или не се е
    приземил на клетка за стоене.
    """
    body = _start_body(cell, profile.direction)
    body.vx = _run_up_speed(grid, cell, profile)
    body.vy = profile.launch_vy
    airborne = profile.launch_vy < 0
    can_cut = profile.cut
    target_vx = profile.direction * profile.target_speed
    for step in range(MAX_SIMULATION_STEPS):
        dt = config.FIXED_DT
        body.vx = approach(body.vx, target_vx, config.AIR_ACCELERATION * dt)
        if can_cut and step * dt >= CUT_JUMP_TIME and body.vy < 0:
            body.vy *= config.JUMP_CUT_MULTIPLIER
            can_cut = False
        dy = gravity_step(body, dt, fall_multiplier=config.FALL_GRAVITY_MULTIPLIER)
        result = move_body(body, grid, body.vx * dt, dy)
        if touching_hazard(grid, body) is not None or body.top > grid.pixel_height:
            return None
        if not result.landed:
            airborne = True
        elif airborne:
            return _landing_cell(grid, body)
    return None


# --- графово търсене --------------------------------------------------------------
def find_start_cell(grid: ReachGrid, spawn: Spawn) -> Cell | None:
    """Героят се появява в клетката на `P` и пада право надолу до първата опора."""
    for row in range(spawn.row, grid.height):
        if grid.is_stand_cell((spawn.col, row)):
            return spawn.col, row
        if not grid.is_free(spawn.col, row):
            return None
    return None


def neighbours(grid: ReachGrid, cell: Cell) -> set[Cell]:
    """Всички клетки, достижими с едно движение (ходене или скок) от `cell`."""
    col, row = cell
    result = {(col + step, row) for step in (-1, 1) if grid.is_stand_cell((col + step, row))}
    for profile in PROFILES:
        if profile.launch_vy == 0 and grid.is_stand_cell((col + profile.direction, row)):
            continue   # слизане от ръб има смисъл само ако отпред няма опора
        landing = simulate_jump(grid, cell, profile)
        if landing is not None:
            result.add(landing)
    result.discard(cell)
    return result


def reachable_cells(level: Level) -> set[Cell]:
    """BFS от старта: множеството от всички достижими клетки за стоене."""
    grid = ReachGrid(level)
    if level.player_start is None:
        return set()
    start = find_start_cell(grid, level.player_start)
    if start is None:
        return set()
    visited = {start}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        for nxt in neighbours(grid, cell):
            if nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)
    return visited


def exit_is_reachable(level: Level) -> bool:
    """Може ли героят да стигне изхода. Изходът е портал, висок 2 тайла."""
    exit_spawn = level.exit
    if exit_spawn is None:
        return False
    goal_cells = {(exit_spawn.col, exit_spawn.row), (exit_spawn.col, exit_spawn.row - 1)}
    return not goal_cells.isdisjoint(reachable_cells(level))
