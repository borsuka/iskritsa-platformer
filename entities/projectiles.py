"""Снаряди: искровите заряди на героя и семената/кълбата на враговете."""
from __future__ import annotations

from typing import TYPE_CHECKING

import config
from entities.entity import Entity
from physics.collision import move_body
from physics.kinematics import gravity_step
from physics.tilemap_query import to_cell

if TYPE_CHECKING:
    from engine.world import World


class EnemyProjectile(Entity):
    """Снаряд на враг: лети по права линия и изчезва в стена.

    Args:
        center_x: център по X при изстрелване.
        center_y: център по Y при изстрелване.
        vx: скорост по X.
        vy: скорост по Y.
        kind: вид (за рисуване) – "thorn" или "boss_orb".
    """

    def __init__(self, center_x: float, center_y: float, vx: float, vy: float,
                 kind: str = "thorn") -> None:
        size = config.ENEMY_PROJECTILE_SIZE
        super().__init__(center_x - size / 2, center_y - size / 2, size, size)
        self.kind = kind
        self.body.vx, self.body.vy = vx, vy
        self.lifetime = config.ENEMY_PROJECTILE_LIFETIME

    def update(self, dt: float, world: World) -> None:
        """Праволинейно движение; изчезва при стена или след време."""
        super().update(dt, world)
        self.body.x += self.body.vx * dt
        self.body.y += self.body.vy * dt
        self.lifetime -= dt
        hits_wall = world.level.is_solid(to_cell(self.body.center_x), to_cell(self.body.center_y))
        if hits_wall or self.lifetime <= 0:
            self.kill()


class Fireball(Entity):
    """Искров заряд на героя: подскача по земята и побеждава враговете.

    Args:
        center_x: център по X при изстрелване.
        center_y: център по Y при изстрелване.
        direction: -1 наляво, 1 надясно.
    """

    kind = "fireball"

    def __init__(self, center_x: float, center_y: float, direction: int) -> None:
        size = config.FIREBALL_SIZE
        super().__init__(center_x - size / 2, center_y - size / 2, size, size)
        self.body.vx = direction * config.FIREBALL_SPEED
        self.facing = direction
        self.lifetime = config.FIREBALL_LIFETIME

    def update(self, dt: float, world: World) -> None:
        """Гравитация, отскок от земята, изчезване при стена."""
        super().update(dt, world)
        speed = self.body.vx
        dy = gravity_step(self.body, dt, gravity=config.FIREBALL_GRAVITY)
        result = move_body(self.body, world.level, speed * dt, dy, platforms=world.platforms)
        if result.landed:
            self.body.vy = -config.FIREBALL_BOUNCE_VELOCITY
        self.lifetime -= dt
        if result.hit_wall or self.lifetime <= 0:
            self.kill()
            world.emit("fireball_pop", self.body.center_x, self.body.center_y)
