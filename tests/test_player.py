"""Тестове за героя: coyote time, jump buffering, пропадане, състояния."""
from __future__ import annotations

import config
from engine.input import PlayerInput
from tests.helpers import run, settle, world_from_rows

T = config.TILE_SIZE

# Героят стои на тясна площадка (3 тайла) и вдясно от нея има пропаст.
LEDGE = (
    "............",
    "............",
    "............",
    "............",
    "P..........X",
    "###.......##",
    "###.......##",
)


def walk_off_ledge(world) -> None:
    """Ходи надясно, докато героят излезе от ръба."""
    for _ in range(200):
        world.update(config.FIXED_DT, PlayerInput(right=True))
        if not world.player.body.on_ground:
            return
    raise AssertionError("героят не слезе от ръба")


def test_coyote_time_allows_late_jump() -> None:
    """Скок 0.05 s след слизане от ръба все пак се изпълнява."""
    world = world_from_rows(*LEDGE)
    settle(world)
    walk_off_ledge(world)
    run(world, 0.05, PlayerInput(right=True))
    world.update(config.FIXED_DT, PlayerInput(right=True, jump_pressed=True, jump_held=True))
    assert world.player.body.vy < -config.JUMP_VELOCITY * 0.9


def test_no_jump_after_coyote_time() -> None:
    """Скок 0.2 s след слизане от ръба НЕ се изпълнява."""
    world = world_from_rows(*LEDGE)
    settle(world)
    walk_off_ledge(world)
    run(world, 0.2, PlayerInput(right=True))
    world.update(config.FIXED_DT, PlayerInput(right=True, jump_pressed=True, jump_held=True))
    assert world.player.body.vy > 0


def fall_until_near_ground(world, frames_before_landing: int) -> None:
    """Пуска героя от височина и спира `frames_before_landing` стъпки преди земята."""
    # Предварително изчисляваме в кой кадър героят каца, после повтаряме до по-рано.
    probe = world_from_rows(*TOWER)
    for frame in range(300):
        probe.update(config.FIXED_DT, PlayerInput())
        if probe.player.body.on_ground:
            landing_frame = frame
            break
    run(world, (landing_frame - frames_before_landing) * config.FIXED_DT)


TOWER = ("P..X",) + ("....",) * 8 + ("####",)


def test_jump_buffer_executes_on_landing() -> None:
    """Скок, натиснат 0.1 s преди приземяване, се изпълнява при допира."""
    world = world_from_rows(*TOWER)
    fall_until_near_ground(world, frames_before_landing=6)
    world.update(config.FIXED_DT, PlayerInput(jump_pressed=True, jump_held=True))
    jumped = False
    for _ in range(12):
        world.update(config.FIXED_DT, PlayerInput(jump_held=True))
        jumped = jumped or world.player.body.vy < -config.JUMP_VELOCITY * 0.9
    assert jumped


def test_too_early_jump_is_forgotten() -> None:
    """Скок, натиснат 0.3 s преди приземяване, се забравя."""
    world = world_from_rows(*TOWER)
    fall_until_near_ground(world, frames_before_landing=18)
    world.update(config.FIXED_DT, PlayerInput(jump_pressed=True, jump_held=True))
    run(world, 0.4, PlayerInput(jump_held=True))
    assert world.player.body.on_ground


def test_drop_through_one_way_platform() -> None:
    """Надолу + скок върху one-way платформа → героят пропада през нея."""
    world = world_from_rows("P..X", "....", "====", "....", "....", "####")
    settle(world)
    assert world.player.body.bottom == 2 * T
    world.update(config.FIXED_DT, PlayerInput(down=True, jump_pressed=True, jump_held=True))
    run(world, 0.5)
    assert world.player.body.bottom == 5 * T


def test_down_jump_on_solid_ground_is_normal_jump() -> None:
    """Надолу + скок на твърда земя е обикновен скок."""
    world = world_from_rows("P..X", "....", "....", "####")
    settle(world)
    world.update(config.FIXED_DT, PlayerInput(down=True, jump_pressed=True, jump_held=True))
    assert world.player.body.vy < 0


def test_state_machine_transitions() -> None:
    """Idle → Run → Jump → Fall → Idle."""
    world = world_from_rows("." * 20, "." * 20, "." * 20, "." * 20, "P" + "." * 18 + "X",
                            "#" * 20)
    settle(world)
    assert world.player.state.name == "idle"
    run(world, 0.2, PlayerInput(right=True))
    assert world.player.state.name == "run"
    world.update(config.FIXED_DT, PlayerInput(jump_pressed=True, jump_held=True))
    assert world.player.state.name == "jump"
    run(world, 0.4, PlayerInput(jump_held=True))
    assert world.player.state.name == "fall"
    run(world, 1.0)
    assert world.player.state.name == "idle"


def test_jump_emits_event() -> None:
    """Скокът записва събитие за звук."""
    world = world_from_rows("P..X", "....", "####")
    settle(world)
    world.drain_events()
    world.update(config.FIXED_DT, PlayerInput(jump_pressed=True, jump_held=True))
    assert [event.kind for event in world.drain_events()] == ["jump"]
