"""Тестове за боса Сенкоглав."""
from __future__ import annotations

import config
from engine.input import PlayerInput
from engine.world import COMPLETE, World
from entities.boss import Boss
from entities.enemies import Walker
from tests.helpers import run, settle, world_from_rows

DT = config.FIXED_DT


def arena() -> World:
    """Арена 40×12 с героя вляво, боса вдясно и изхода в края."""
    rows = ["#" * 40] + ["." * 40] * 9 + ["P" + "." * 26 + "@" + "." * 10 + "X", "#" * 40]
    return world_from_rows(*rows)


def boss_of(world: World) -> Boss:
    """Босът в света."""
    assert world.boss is not None
    return world.boss


def stomp(world: World, boss: Boss) -> None:
    """Поставя героя над боса и го пуска – един скок отгоре."""
    body = world.player.body
    body.x = boss.body.center_x - body.width / 2
    body.y = boss.body.top - 40
    body.vy = 200.0
    for _ in range(30):
        world.update(DT, PlayerInput())
        if body.vy < 0:     # отскочил е – скокът отгоре е регистриран
            return
    raise AssertionError("героят не стъпи върху боса")


def test_exit_is_locked_while_boss_alive() -> None:
    """Докато босът е жив, изходът е затворен."""
    world = arena()
    assert not world.exit.is_open


def test_three_stomps_defeat_boss_and_open_exit() -> None:
    """3 скока отгоре с пауза за неуязвимостта побеждават боса и отварят изхода."""
    world = arena()
    boss = boss_of(world)
    for expected_hp in (2, 1, 0):
        stomp(world, boss)
        assert boss.hp == expected_hp
        boss.invulnerable_timer = 0.0
    world.update(DT, PlayerInput())
    assert not boss.alive
    assert world.exit.is_open
    assert world.session.score >= config.POINTS["boss"]


def test_boss_is_invulnerable_right_after_hit() -> None:
    """Втори скок веднага след удара не отнема HP и не наранява героя."""
    world = arena()
    boss = boss_of(world)
    stomp(world, boss)
    stomp(world, boss)
    assert boss.hp == config.BOSS_MAX_HP - 1
    assert not world.player.is_dead


def test_boss_phases_follow_hp() -> None:
    """Фазата расте, когато HP намалява."""
    world = arena()
    boss = boss_of(world)
    assert boss.phase == 0
    boss.hp = 2
    assert boss.phase == 1
    boss.hp = 1
    assert boss.phase == 2


def test_phase_two_shoots_spread() -> None:
    """Във фаза 2 босът изстрелва ветрило от 3 кълба."""
    world = arena()
    boss = boss_of(world)
    boss.hp = 2
    boss.active = True
    world.player.star_timer = 100.0   # героят е неуязвим, за да не прекъсне теста
    run(world, config.BOSS_SHOT_INTERVAL + 0.1)
    orbs = [shot for shot in world.enemy_projectiles if shot.kind == "boss_orb"]
    assert len(orbs) == len(config.BOSS_SHOT_SPREAD)


def test_phase_three_summons_limited_minions() -> None:
    """Във фаза 3 босът призовава Мъхчовци, но не повече от лимита."""
    world = arena()
    boss = boss_of(world)
    boss.hp = 1
    boss.active = True
    world.player.star_timer = 100.0
    world.player.body.x = boss.body.x   # героят е до боса → не „поваля“ помощниците
    world.player.body.y = -500
    run(world, config.BOSS_SUMMON_INTERVAL * (config.BOSS_MAX_MINIONS + 2))
    minions = [enemy for enemy in world.enemies if isinstance(enemy, Walker)]
    assert 1 <= len(minions) <= config.BOSS_MAX_MINIONS


def test_boss_landing_shakes_screen() -> None:
    """Приземяването след скок пуска събитие за разклащане на екрана."""
    world = arena()
    boss_of(world).active = True
    world.player.star_timer = 100.0
    kinds: list[str] = []
    for _ in range(int(4 / DT)):
        world.update(DT, PlayerInput())
        kinds += [event.kind for event in world.drain_events()]
    assert "boss_land" in kinds


def test_fireballs_do_not_hurt_boss() -> None:
    """Искровите заряди не вредят на боса."""
    world = arena()
    boss = boss_of(world)
    settle(world)
    world.player.set_form("flame")
    for _ in range(int(3 / DT)):
        world.update(DT, PlayerInput(shoot_pressed=True))
        if world.player.is_dead:
            break
    assert boss.hp == config.BOSS_MAX_HP


def test_level_complete_after_boss() -> None:
    """След победата героят може да стигне изхода и да завърши нивото."""
    world = arena()
    boss = boss_of(world)
    boss.hp = 1
    stomp(world, boss)
    world.update(DT, PlayerInput())
    world.player.body.x = world.exit.body.x
    world.player.body.y = world.exit.body.y
    world.update(DT, PlayerInput())
    assert world.status == COMPLETE
