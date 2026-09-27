"""Враговете: Walker (Мъхчо), Hopper (Скокльо), Flyer (Нощниче), Shooter (Бодлоцвет).

Всеки враг наследява `Enemy` и променя само метода `behave` – как решава
накъде да се движи. Гравитацията, колизиите и побеждаването са общи.
Босът е в отделен модул (`entities/boss.py`), защото е много по-сложен.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import config
from entities.entity import Entity
from entities.projectiles import EnemyProjectile
from level.level import Spawn
from physics.collision import CollisionResult, move_body
from physics.kinematics import gravity_step
from physics.tilemap_query import to_cell

if TYPE_CHECKING:
    from engine.world import World


class Enemy(Entity):
    """Общото за всички врагове.

    Args:
        x: лявият ръб.
        y: горният ръб.
        width: ширина.
        height: височина.
    """

    kind = "enemy"
    #: Врагът пада ли под действие на гравитацията.
    uses_gravity = True
    #: Може ли да бъде победен със скок отгоре.
    stompable = True
    #: Може ли да бъде победен от снаряд на героя.
    fireball_vulnerable = True

    def __init__(self, x: float, y: float, width: float, height: float) -> None:
        super().__init__(x, y, width, height)
        self.facing = -1
        self.active = False
        self.last_collision = CollisionResult()

    @classmethod
    def at_spawn(cls, spawn: Spawn) -> Enemy:
        """Създава врага така, че да стои на дъното на клетката си."""
        width, height = cls.size()
        x, y = cls.feet_in_cell(spawn.col, spawn.row, width, height)
        return cls(x, y, width, height)

    @classmethod
    def size(cls) -> tuple[int, int]:
        """Размерът на хитбокса (всеки подклас задава своя)."""
        return config.WALKER_SIZE

    @property
    def points(self) -> int:
        """Точки за побеждаване."""
        return config.POINTS.get(self.kind, 0)

    def update(self, dt: float, world: World) -> None:
        """Събужда се близо до героя, после изпълнява поведението си."""
        super().update(dt, world)
        distance = abs(self.body.center_x - world.player.body.center_x)
        if distance < config.ENEMY_ACTIVATION_DISTANCE:
            self.active = True
        if not self.active:
            return
        self.behave(dt, world)
        if self.body.top > world.level.pixel_height + config.PIT_DEATH_MARGIN:
            self.kill()

    def behave(self, dt: float, world: World) -> None:
        """Поведението на конкретния враг (подкласовете го заменят)."""
        self.fall_and_move(dt, world)

    def fall_and_move(self, dt: float, world: World) -> CollisionResult:
        """Гравитация + хоризонтална скорост + колизии с картата."""
        dy = gravity_step(self.body, dt) if self.uses_gravity else self.body.vy * dt
        self.last_collision = move_body(self.body, world.level, self.body.vx * dt, dy,
                                        platforms=world.platforms)
        return self.last_collision

    def defeat(self, world: World, how: str) -> None:
        """Врагът е победен: дава точки и изчезва (визуалният ефект е в Playing).

        Args:
            world: светът.
            how: "stomp" (скок отгоре), "fireball" или "star".
        """
        if not self.alive:
            return
        self.kill()
        world.add_points(self.points, self.body.center_x, self.body.top)
        world.emit(f"enemy_{how}", self.body.center_x, self.body.center_y,
                   data=f"{self.kind}:{self.facing}")


class Walker(Enemy):
    """Мъхчо: ходи напред и се обръща при стена или ръб на платформа."""

    kind = "walker"

    @classmethod
    def size(cls) -> tuple[int, int]:
        """Размер от config."""
        return config.WALKER_SIZE

    def behave(self, dt: float, world: World) -> None:
        """Ходи; при стена или липса на земя отпред се обръща."""
        self.body.vx = self.facing * config.WALKER_SPEED
        result = self.fall_and_move(dt, world)
        if result.hit_wall or (self.body.on_ground and not self.ground_ahead(world)):
            self.facing = -self.facing
            self.body.vx = self.facing * config.WALKER_SPEED

    def ground_ahead(self, world: World) -> bool:
        """Има ли земя точно пред предния крак (иначе ще падне от ръба)."""
        front_x = self.body.right + 1 if self.facing > 0 else self.body.left - 1
        col, row = to_cell(front_x), to_cell(self.body.bottom + 1)
        if world.level.tile_at(col, row).supports_standing:
            return True
        return any(platform.left <= front_x <= platform.right
                   and abs(platform.top - self.body.bottom) < 2 for platform in world.platforms)


class Hopper(Enemy):
    """Скокльо: чака на земята и периодично подскача към героя."""

    kind = "hopper"

    def __init__(self, x: float, y: float, width: float, height: float) -> None:
        super().__init__(x, y, width, height)
        self.wait_timer = 0.0

    @classmethod
    def size(cls) -> tuple[int, int]:
        """Размер от config."""
        return config.HOPPER_SIZE

    def behave(self, dt: float, world: World) -> None:
        """На земята брои до скок; скача, ако героят е наблизо."""
        body = self.body
        if body.on_ground:
            body.vx = 0.0
            self.wait_timer += dt
            player = world.player.body
            self.facing = 1 if player.center_x > body.center_x else -1
            near = abs(player.center_x - body.center_x) < config.HOPPER_SIGHT_RANGE
            if self.wait_timer >= config.HOPPER_WAIT_TIME and near:
                self.wait_timer = 0.0
                body.vy = -config.HOPPER_JUMP_VELOCITY
                body.vx = self.facing * config.HOPPER_JUMP_SPEED_X
        self.fall_and_move(dt, world)

    @property
    def airborne(self) -> bool:
        """Във въздуха ли е (за анимацията)."""
        return not self.body.on_ground


class Flyer(Enemy):
    """Нощниче: лети напред-назад по синусоида и не пада."""

    kind = "flyer"
    uses_gravity = False

    def __init__(self, x: float, y: float, width: float, height: float) -> None:
        super().__init__(x, y, width, height)
        self.origin_x = x
        self.base_y = y

    @classmethod
    def at_spawn(cls, spawn: Spawn) -> Enemy:
        """Нощничето се появява в центъра на клетката си (не на земята)."""
        width, height = cls.size()
        size = config.TILE_SIZE
        return cls(spawn.col * size + (size - width) / 2, spawn.row * size + (size - height) / 2,
                   width, height)

    @classmethod
    def size(cls) -> tuple[int, int]:
        """Размер от config."""
        return config.FLYER_SIZE

    def behave(self, dt: float, world: World) -> None:
        """Хоризонтален патрул + вертикална синусоида y = y0 + A·sin(2π·f·t)."""
        body = self.body
        body.x += self.facing * config.FLYER_SPEED * dt
        front = body.right if self.facing > 0 else body.left
        blocked = world.level.is_solid(to_cell(front), to_cell(body.center_y))
        too_far = abs(body.x - self.origin_x) > config.FLYER_PATROL_RANGE
        if blocked or (too_far and (body.x - self.origin_x) * self.facing > 0):
            self.facing = -self.facing
        wave = math.sin(2 * math.pi * config.FLYER_FREQUENCY * self.anim_time)
        body.y = self.base_y + config.FLYER_AMPLITUDE * wave


class Shooter(Enemy):
    """Бодлоцвет: стои на място и изстрелва бодил към героя, ако е в обхват."""

    kind = "shooter"
    MOUTH_OPEN_TIME = 0.3

    def __init__(self, x: float, y: float, width: float, height: float) -> None:
        super().__init__(x, y, width, height)
        self.cooldown = config.SHOOTER_INTERVAL / 2
        self.since_shot = 1.0

    @classmethod
    def size(cls) -> tuple[int, int]:
        """Размер от config."""
        return config.SHOOTER_SIZE

    def behave(self, dt: float, world: World) -> None:
        """Обръща се към героя и стреля през интервал, ако той е в обхват."""
        self.body.vx = 0.0
        self.fall_and_move(dt, world)
        self.since_shot += dt
        player = world.player.body
        dx = player.center_x - self.body.center_x
        dy = player.center_y - self.body.center_y
        self.facing = 1 if dx > 0 else -1
        in_range = abs(dx) < config.SHOOTER_RANGE_X and abs(dy) < config.SHOOTER_RANGE_Y
        self.cooldown -= dt
        if in_range and self.cooldown <= 0:
            self.shoot(world, dx, dy)

    def shoot(self, world: World, dx: float, dy: float) -> None:
        """Изстрелва снаряд по посока на героя (нормализиран вектор × скорост)."""
        self.cooldown = config.SHOOTER_INTERVAL
        self.since_shot = 0.0
        length = math.hypot(dx, dy) or 1.0
        speed = config.ENEMY_PROJECTILE_SPEED
        projectile = EnemyProjectile(self.body.center_x, self.body.top + 8,
                                     dx / length * speed, dy / length * speed, "thorn")
        world.add_projectile(projectile)
        world.emit("enemy_shoot", self.body.center_x, self.body.top)

    @property
    def mouth_open(self) -> bool:
        """Отворена ли е устата (за анимацията)."""
        return self.since_shot < self.MOUTH_OPEN_TIME


ENEMY_CLASSES: dict[str, type[Enemy]] = {
    "walker": Walker,
    "hopper": Hopper,
    "flyer": Flyer,
    "shooter": Shooter,
}


def create_enemy(spawn: Spawn) -> Enemy:
    """Фабрика: създава правилния враг според вида на spawn-а."""
    return ENEMY_CLASSES[spawn.kind].at_spawn(spawn)
