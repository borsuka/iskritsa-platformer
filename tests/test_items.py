"""Тестове за предметите, блоковете и power-up-ите."""
from __future__ import annotations

import config
from engine.input import PlayerInput
from engine.world import World
from entities.enemies import Walker
from level import tiles
from tests.helpers import level_from_rows, run, settle, world_from_rows

T = config.TILE_SIZE
DT = config.FIXED_DT

# Героят стои под блок на височина 3 тайла над земята.
BLOCK_ROWS = ("..........", "..........", "..?.......", "..........", "..P......X",
              "##########")


def jump_into_block(world: World) -> None:
    """Скача веднъж право нагоре и изчаква приземяването."""
    world.update(DT, PlayerInput(jump_pressed=True, jump_held=True))
    run(world, 1.2, PlayerInput(jump_held=True))


def test_surprise_block_gives_content_only_once() -> None:
    """Блокът с изненада дава монета само при първия удар и става празен."""
    world = world_from_rows(*BLOCK_ROWS)
    settle(world)
    jump_into_block(world)
    assert world.session.coins == 1
    assert world.level.symbol_at(2, 2) == tiles.USED_BLOCK
    jump_into_block(world)
    assert world.session.coins == 1


def test_block_bump_emits_event() -> None:
    """Ударът на блок пуска събитие за звук и анимация."""
    world = world_from_rows(*BLOCK_ROWS)
    settle(world)
    world.drain_events()
    jump_into_block(world)
    kinds = [event.kind for event in world.drain_events()]
    assert "bump" in kinds and "coin" in kinds


def test_powerup_block_releases_ember_for_small_player() -> None:
    """Блок „!“ пуска Жарава за малката форма."""
    world = world_from_rows(*[row.replace("?", "!") for row in BLOCK_ROWS])
    settle(world)
    jump_into_block(world)
    assert [item.kind for item in world.powerups] == ["powerup"]


def test_powerup_block_releases_flame_for_big_player() -> None:
    """Блок „!“ пуска Пламък, ако героят вече е голям."""
    world = world_from_rows("..........", "..!.......", "..........", "..........",
                            "..P......X", "##########")
    settle(world)
    world.player.set_form("big")
    jump_into_block(world)
    assert [item.kind for item in world.powerups] == ["flame"]


def test_breakable_block_needs_big_form() -> None:
    """Малката форма само побутва чупливия блок; голямата го чупи."""
    world = world_from_rows(*[row.replace("?", "B") for row in BLOCK_ROWS])
    settle(world)
    jump_into_block(world)
    assert world.level.symbol_at(2, 2) == tiles.BREAKABLE
    world.player.set_form("big")
    run(world, 0.2)
    jump_into_block(world)
    assert world.level.symbol_at(2, 2) == tiles.EMPTY
    assert world.session.score == config.POINTS["brick"]


def test_form_transitions_small_big_flame_and_back() -> None:
    """малка → (Жарава) голяма → (Пламък) огнена → (удар) малка."""
    world = world_from_rows("P........X", "##########")
    settle(world)
    player = world.player
    player.collect_powerup("powerup", world)
    run(world, DT)
    assert player.form == "big" and player.body.height == config.PLAYER_BIG_HEIGHT
    player.collect_powerup("flame", world)
    assert player.form == "flame"
    player.hurt(world, player.body.center_x + 5)
    assert player.form == "small" and player.body.height == config.PLAYER_SMALL_HEIGHT
    assert not player.is_dead


def test_growing_waits_for_space_under_low_ceiling() -> None:
    """Под нисък таван героят пораства едва когато излезе отдолу."""
    world = world_from_rows("." * 30, ".########" + "." * 21, "P" + "." * 28 + "X", "#" * 30)
    settle(world)
    player = world.player
    player.body.x = 3 * T
    player.collect_powerup("powerup", world)
    run(world, DT)
    assert player.form == "small"
    run(world, 1.2, PlayerInput(right=True))
    assert player.form == "big"
    assert player.body.top >= 0


def test_powerup_emerges_and_is_collected() -> None:
    """Power-up излиза от блока и героят го взима при допир."""
    world = world_from_rows(*[row.replace("?", "!") for row in BLOCK_ROWS])
    settle(world)
    jump_into_block(world)
    item = world.powerups[0]
    run(world, 1.0)
    assert not item.emerging
    world.player.body.x = item.body.x
    world.player.body.y = item.body.y
    run(world, DT * 2)
    assert world.player.form == "big" or world.player.pending_form == "big"


def test_coins_and_crystals_are_collected() -> None:
    """Монетите и кристалите се събират при допир и дават точки."""
    world = world_from_rows("P.C.G....X", "##########")
    settle(world)
    run(world, 1.0, PlayerInput(right=True))
    assert world.session.coins == 1
    assert world.session.crystals == {0}
    assert world.session.score == config.POINTS["coin"] + config.POINTS["crystal"]


def test_collected_crystal_stays_collected_after_respawn() -> None:
    """Събран кристал не се появява отново след загубен живот."""
    level = level_from_rows("P.G.G....X", "##########")
    world = World(level)
    settle(world)
    run(world, 0.5, PlayerInput(right=True))
    assert world.session.crystals == {0}
    respawned = World(level, world.session)
    assert [crystal.index for crystal in respawned.crystals] == [1]


def test_hundred_coins_in_world_give_life() -> None:
    """100 монети в света добавят живот."""
    world = world_from_rows("P" + "C" * 100 + "X", "#" * 102)
    settle(world)
    lives = world.session.lives
    run(world, 12.0, PlayerInput(right=True, run=True))
    assert world.session.lives == lives + 1


def test_comet_makes_player_invincible_and_defeats_enemies() -> None:
    """С Комета врагът пада при допир, а героят не се наранява."""
    world = world_from_rows("P...E" + "." * 25 + "X", "#" * 31)
    settle(world)
    world.player.collect_powerup("comet", world)
    run(world, 1.5, PlayerInput(right=True))
    assert not any(isinstance(enemy, Walker) for enemy in world.enemies)
    assert not world.player.is_dead
    assert world.player.star_timer > 0
    run(world, config.STAR_DURATION)
    assert world.player.star_timer == 0


def test_fireball_only_in_flame_form_and_defeats_walker() -> None:
    """Изстрел има само във форма „Пламък“; зарядът побеждава Мъхчо."""
    world = world_from_rows("P......E.X", "##########")
    settle(world)
    world.update(DT, PlayerInput(shoot_pressed=True))
    assert not world.fireballs
    world.player.set_form("flame")
    world.update(DT, PlayerInput(shoot_pressed=True))
    assert len(world.fireballs) == 1
    run(world, 1.0)
    assert not world.enemies
    assert world.session.score == config.POINTS["walker"]


def test_at_most_two_fireballs() -> None:
    """Едновременно може да има най-много MAX_PLAYER_FIREBALLS заряда."""
    world = world_from_rows("P" + "." * 30 + "X", "#" * 32)
    settle(world)
    world.player.set_form("flame")
    for _ in range(5):
        world.update(DT, PlayerInput(shoot_pressed=True))
    assert len(world.fireballs) == config.MAX_PLAYER_FIREBALLS


def test_bumping_block_defeats_enemy_on_top() -> None:
    """Враг върху блока, ударен отдолу, е победен."""
    world = world_from_rows("..........", "..E.......", "..?.......", "..........",
                            "..P......X", "##########")
    world.enemies[0].active = False     # „спящ“ враг, за да не избяга от блока
    settle(world)
    jump_into_block(world)
    assert not world.enemies
