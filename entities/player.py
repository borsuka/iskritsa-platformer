"""Героят – Искрица, малък дух-пламъче.

Тук е „усещането“ на играта: ускорение и триене, скок с изчислена сила,
променлива височина, coyote time и jump buffering. Всички числа са в config.py.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import config
from engine.input import PlayerInput
from entities.entity import Entity
from entities.player_states import DeadState, HurtState, IdleState, PlayerState
from level.level import Spawn
from entities.projectiles import Fireball
from physics.collision import CollisionResult, move_body
from physics.kinematics import approach, gravity_step
from physics.tilemap_query import tiles_in_rect

if TYPE_CHECKING:
    from engine.world import World


class Player(Entity):
    """Героят, управляван от играча.

    Args:
        x: лявият ръб.
        y: горният ръб.
    """

    kind = "player"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, config.PLAYER_WIDTH, config.PLAYER_SMALL_HEIGHT)
        self.form = "small"
        self.state: PlayerState = IdleState()
        self.state_time = 0.0
        self.coyote_timer = 0.0
        self.jump_buffer_timer = 0.0
        self.drop_through_timer = 0.0
        self.can_cut_jump = False
        self.invulnerable_timer = 0.0
        self.star_timer = 0.0
        self.previous_bottom = self.body.bottom
        self.death_cause = ""
        self.pending_form: str | None = None
        self.last_collision = CollisionResult()

    @classmethod
    def at_spawn(cls, spawn: Spawn) -> Player:
        """Създава героя така, че да стои на дъното на клетката `P`."""
        x, y = cls.feet_in_cell(spawn.col, spawn.row, config.PLAYER_WIDTH,
                                config.PLAYER_SMALL_HEIGHT)
        return cls(x, y)

    # --- основен цикъл -----------------------------------------------------
    def update_with_input(self, dt: float, inp: PlayerInput, world: World) -> None:
        """Една логическа стъпка: вход → скорости → движение → смяна на състояние."""
        self.anim_time += dt
        self.state_time += dt
        self.previous_bottom = self.body.bottom
        self.invulnerable_timer = max(0.0, self.invulnerable_timer - dt)
        self.star_timer = max(0.0, self.star_timer - dt)
        if self.is_dead:
            self._fall_while_dead(dt)
            return
        if self.state.controllable:
            self._apply_horizontal_input(inp, dt)
            self._handle_jump(inp, dt, world)
            self._handle_shoot(inp, world)
        self._move(dt, world)
        self._apply_pending_form(world)
        self._update_state()

    @property
    def is_dead(self) -> bool:
        """Загинал ли е героят (тече анимацията на смъртта)."""
        return isinstance(self.state, DeadState)

    @property
    def is_big(self) -> bool:
        """В голяма форма ли е (издържа един удар повече)."""
        return self.form != "small"

    def change_state(self, state: PlayerState) -> None:
        """Сменя състоянието и нулира таймера му."""
        self.state = state
        self.state_time = 0.0

    def _update_state(self) -> None:
        """Пита текущото състояние дали иска да премине в друго."""
        next_state = self.state.next_state(self)
        if next_state is not None:
            self.change_state(next_state)

    # --- хоризонтално движение ---------------------------------------------
    def _apply_horizontal_input(self, inp: PlayerInput, dt: float) -> None:
        """Ускорение към желаната скорост или триене до спиране."""
        body = self.body
        direction = inp.direction
        if direction == 0:
            friction = config.GROUND_FRICTION if body.on_ground else config.AIR_FRICTION
            body.vx = approach(body.vx, 0.0, friction * dt)
            return
        self.facing = direction
        max_speed = config.MAX_RUN_SPEED if inp.run else config.MAX_WALK_SPEED
        accel = config.GROUND_ACCELERATION if body.on_ground else config.AIR_ACCELERATION
        if body.vx * direction < 0:
            # Обръщане: добавяме и триенето, за да е завоят „отзивчив“.
            accel += config.GROUND_FRICTION if body.on_ground else config.AIR_FRICTION
        body.vx = approach(body.vx, direction * max_speed, accel * dt)

    # --- скок --------------------------------------------------------------
    def _handle_jump(self, inp: PlayerInput, dt: float, world: World) -> None:
        """Coyote time, jump buffering, пропадане и променлива височина на скока."""
        body = self.body
        # Coyote time: „помним“ земята още малко след като сме слезли от ръба.
        self.coyote_timer = config.COYOTE_TIME if body.on_ground else max(
            0.0, self.coyote_timer - dt)
        # Jump buffering: „помним“ натиснатия скок още малко преди приземяване.
        if inp.jump_pressed:
            self.jump_buffer_timer = config.JUMP_BUFFER_TIME
        else:
            self.jump_buffer_timer = max(0.0, self.jump_buffer_timer - dt)
        self.drop_through_timer = max(0.0, self.drop_through_timer - dt)

        if self.jump_buffer_timer > 0 and self.coyote_timer > 0:
            self.jump_buffer_timer = 0.0
            self.coyote_timer = 0.0
            if inp.down and body.on_ground and body.on_one_way:
                self.drop_through_timer = config.DROP_THROUGH_TIME
            else:
                self.jump(world)
        # Променлива височина: пуснат бутон при издигане → отрязваме скоростта веднъж.
        if self.can_cut_jump and not inp.jump_held and body.vy < 0:
            body.vy *= config.JUMP_CUT_MULTIPLIER
            self.can_cut_jump = False

    def jump(self, world: World) -> None:
        """Започва скок с начална скорост, изчислена от желаната височина."""
        self.body.vy = -config.JUMP_VELOCITY
        self.body.on_ground = False
        self.can_cut_jump = True
        world.emit("jump", self.body.center_x, self.body.bottom)

    # --- движение и колизии ------------------------------------------------
    def _move(self, dt: float, world: World) -> None:
        """Гравитация и преместване с колизии."""
        body = self.body
        dy = gravity_step(body, dt, fall_multiplier=config.FALL_GRAVITY_MULTIPLIER)
        self.last_collision = move_body(body, world.level, body.vx * dt, dy,
                                        ignore_one_way=self.drop_through_timer > 0,
                                        platforms=world.platforms)
        if self.last_collision.landed:
            self.can_cut_jump = False

    def _fall_while_dead(self, dt: float) -> None:
        """След смърт героят подскача и пада през всичко (без колизии)."""
        if self.state_time < config.HURT_STUN_TIME:
            return   # кратка пауза във въздуха преди падането
        self.body.y += gravity_step(self.body, dt)

    # --- щети и смърт --------------------------------------------------------
    @property
    def is_invulnerable(self) -> bool:
        """Не може да бъде наранен (след удар или с Комета)."""
        return self.invulnerable_timer > 0 or self.star_timer > 0 or self.is_dead

    def hurt(self, world: World, source_x: float) -> None:
        """Удар от враг или шипове: голямата форма става малка, малката загива.

        Args:
            world: светът.
            source_x: откъде е дошъл ударът (за посоката на отблъскване).
        """
        if self.is_invulnerable:
            return
        if not self.is_big:
            self.die(world, "enemy")
            return
        self.pending_form = None
        self.set_form("small")
        self.invulnerable_timer = config.INVULNERABILITY_TIME
        direction = 1 if self.body.center_x >= source_x else -1
        self.body.vx = direction * config.KNOCKBACK_SPEED_X
        self.body.vy = -config.KNOCKBACK_SPEED_Y
        self.change_state(HurtState())
        world.emit("hurt", self.body.center_x, self.body.center_y)

    def die(self, world: World, cause: str) -> None:
        """Героят загива: подскок нагоре и падане извън екрана.

        Args:
            world: светът.
            cause: "enemy", "lava", "pit" или "time" (за статистика/дебъг).
        """
        if self.is_dead:
            return
        self.death_cause = cause
        self.star_timer = 0.0
        self.body.vx = 0.0
        self.body.vy = -config.DEATH_HOP_VELOCITY if cause != "pit" else 0.0
        self.change_state(DeadState())
        world.emit("die", self.body.center_x, self.body.center_y)

    def bounce(self, jump_held: bool) -> None:
        """Отскок след скачане върху враг (по-висок, ако скокът е задържан)."""
        speed = config.STOMP_BOUNCE_HELD_VELOCITY if jump_held else config.STOMP_BOUNCE_VELOCITY
        self.body.vy = -speed
        self.can_cut_jump = jump_held

    def set_form(self, form: str) -> None:
        """Сменя формата и височината на хитбокса (краката остават на място)."""
        self.form = form
        height = config.PLAYER_SMALL_HEIGHT if form == "small" else config.PLAYER_BIG_HEIGHT
        self.body.resize_keep_feet(config.PLAYER_WIDTH, height)

    # --- power-up-и ----------------------------------------------------------
    def collect_powerup(self, kind: str, world: World) -> None:
        """Прилага ефекта на събран power-up.

        Args:
            kind: "powerup" (Жарава → голяма), "flame" (Пламък) или "comet" (Комета).
            world: светът (за събития и точки).
        """
        if kind == "comet":
            self.star_timer = config.STAR_DURATION
            world.emit("star", self.body.center_x, self.body.center_y)
            return
        target = "big" if kind == "powerup" else "flame"
        if self.form == "flame" and target == "big":
            target = "flame"   # Жаравата не отнема вече придобития Пламък
        if not self.is_big:
            self.pending_form = target   # растежът изчаква място над главата
        else:
            self.set_form(target)
        world.add_points(config.POINTS["powerup"], self.body.center_x, self.body.top)
        world.emit("powerup", self.body.center_x, self.body.center_y)

    def _apply_pending_form(self, world: World) -> None:
        """Пораства, щом над главата има достатъчно място (иначе би влязъл в тавана)."""
        if self.pending_form is None:
            return
        body = self.body
        new_top = body.bottom - config.PLAYER_BIG_HEIGHT
        blocked = any(tile.solid for _c, _r, tile in tiles_in_rect(
            world.level, body.left, new_top, body.right, body.bottom))
        if not blocked:
            self.set_form(self.pending_form)
            self.pending_form = None

    def _handle_shoot(self, inp: PlayerInput, world: World) -> None:
        """Във форма „Пламък“ изстрелва искров заряд (най-много 2 едновременно)."""
        if not inp.shoot_pressed or self.form != "flame":
            return
        if len(world.fireballs) >= config.MAX_PLAYER_FIREBALLS:
            return
        x = self.body.center_x + self.facing * self.body.width / 2
        y = self.body.center_y + self.body.height * config.FIREBALL_SPAWN_DROP
        world.fireballs.append(Fireball(x, y, self.facing))
        world.emit("shoot", x, y)
