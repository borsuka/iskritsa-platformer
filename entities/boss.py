"""Сенкоглав – босът на последното ниво.

Фазите зависят от оставащите точки живот (HP):
* **фаза 1** (3 HP): ходи към героя и периодично скача; приземяването разклаща екрана;
* **фаза 2** (2 HP): като фаза 1, по-бърз, и изстрелва ветрило от 3 сенчести кълба;
* **фаза 3** (1 HP): още по-бърз и призовава Мъхчовци (най-много 3 наведнъж).

Побеждава се с 3 скока отгоре. След всеки удар е неуязвим и безвреден за
`BOSS_INVULNERABLE_TIME` секунди – героят има време да се отдалечи. Искровите
заряди и Кометата не му вредят. Докато е жив, изходът на нивото е затворен.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import config
from entities.enemies import Enemy, Walker
from entities.projectiles import EnemyProjectile

if TYPE_CHECKING:
    from engine.world import World


class Boss(Enemy):
    """Босът с три фази и HP."""

    kind = "boss"
    fireball_vulnerable = False

    def __init__(self, x: float, y: float, width: float, height: float) -> None:
        super().__init__(x, y, width, height)
        self.hp = config.BOSS_MAX_HP
        self.invulnerable_timer = 0.0
        self.jump_timer = 0.0
        self.shot_timer = 0.0
        self.summon_timer = 0.0
        self.was_airborne = False
        self.minions: list[Walker] = []

    @classmethod
    def size(cls) -> tuple[int, int]:
        """Размер от config."""
        return config.BOSS_SIZE

    @property
    def phase(self) -> int:
        """Текуща фаза: 0, 1 или 2 (колкото по-малко HP, толкова по-висока)."""
        return min(config.BOSS_MAX_HP - self.hp, config.BOSS_MAX_HP - 1)

    @property
    def harmful(self) -> bool:
        """Наранява ли при допир (не и докато е неуязвим след удар)."""
        return self.invulnerable_timer <= 0

    def behave(self, dt: float, world: World) -> None:
        """Движение към героя, скокове и атаките на текущата фаза."""
        self.invulnerable_timer = max(0.0, self.invulnerable_timer - dt)
        self._walk_and_jump(dt, world)
        if self.phase >= 1:
            self._shoot(dt, world)
        if self.phase >= 2:
            self._summon(dt, world)

    def _walk_and_jump(self, dt: float, world: World) -> None:
        """Върви към героя; на интервал скача; приземяването разклаща екрана."""
        body = self.body
        player = world.player.body
        if body.on_ground:
            self.facing = 1 if player.center_x > body.center_x else -1
            self.jump_timer += dt
            if self.jump_timer >= config.BOSS_JUMP_INTERVAL[self.phase]:
                self.jump_timer = 0.0
                body.vy = -config.BOSS_JUMP_VELOCITY
        body.vx = self.facing * config.BOSS_SPEED * config.BOSS_SPEED_MULTIPLIER[self.phase]
        result = self.fall_and_move(dt, world)
        if result.hit_wall:
            self.facing = -self.facing
        if result.landed and self.was_airborne:
            world.emit("boss_land", body.center_x, body.bottom)
        self.was_airborne = not body.on_ground

    def _shoot(self, dt: float, world: World) -> None:
        """Ветрило от кълба по посока на героя (ъглите са в BOSS_SHOT_SPREAD)."""
        self.shot_timer += dt
        if self.shot_timer < config.BOSS_SHOT_INTERVAL:
            return
        self.shot_timer = 0.0
        player = world.player.body
        base = math.atan2(player.center_y - self.body.center_y,
                          player.center_x - self.body.center_x)
        speed = config.ENEMY_PROJECTILE_SPEED
        for spread in config.BOSS_SHOT_SPREAD:
            angle = base + spread
            world.add_projectile(EnemyProjectile(self.body.center_x, self.body.center_y,
                                                 math.cos(angle) * speed,
                                                 math.sin(angle) * speed, "boss_orb"))
        world.emit("enemy_shoot", self.body.center_x, self.body.center_y)

    def _summon(self, dt: float, world: World) -> None:
        """Призовава Мъхчо пред себе си, ако живите помощници са под лимита."""
        self.summon_timer += dt
        self.minions = [minion for minion in self.minions if minion.alive]
        if self.summon_timer < config.BOSS_SUMMON_INTERVAL:
            return
        self.summon_timer = 0.0
        if len(self.minions) >= config.BOSS_MAX_MINIONS:
            return
        width, height = config.WALKER_SIZE
        x = self.body.center_x + self.facing * (self.body.width / 2 + width) - width / 2
        minion = Walker(x, self.body.bottom - height, width, height)
        minion.facing = self.facing
        minion.active = True
        self.minions.append(minion)
        world.enemies.append(minion)
        world.emit("boss_summon", minion.body.center_x, minion.body.center_y)

    def stomped(self, world: World) -> None:
        """Скок отгоре: −1 HP и кратка неуязвимост; при 0 HP – победа."""
        if self.invulnerable_timer > 0:
            return
        self.hp -= 1
        self.invulnerable_timer = config.BOSS_INVULNERABLE_TIME
        world.emit("boss_hit", self.body.center_x, self.body.top)
        if self.hp <= 0:
            self.defeat(world, "stomp")

    def star_touch(self, world: World) -> None:
        """Кометата не вреди на боса."""
