"""Героят – Искрица, малък дух-пламъче.

Тук е „усещането“ на играта: ускорение и триене, скок с изчислена сила,
променлива височина, coyote time и jump buffering. Всички числа са в config.py.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import config
from engine.input import PlayerInput
from entities.entity import Entity
from entities.player_states import IdleState, PlayerState
from level.level import Spawn
from physics.collision import CollisionResult, move_body
from physics.kinematics import approach, gravity_step

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
        self.state: PlayerState = IdleState()
        self.state_time = 0.0
        self.coyote_timer = 0.0
        self.jump_buffer_timer = 0.0
        self.drop_through_timer = 0.0
        self.can_cut_jump = False
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
        if self.state.controllable:
            self._apply_horizontal_input(inp, dt)
            self._handle_jump(inp, dt, world)
        self._move(dt, world)
        self._update_state()

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
                                        ignore_one_way=self.drop_through_timer > 0)
        if self.last_collision.landed:
            self.can_cut_jump = False
