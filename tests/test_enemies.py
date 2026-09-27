"""Тестове за враговете, нараняването, опасностите и чекпойнтите."""
from __future__ import annotations

import config
from engine.input import PlayerInput
from engine.session import Session
from engine.world import COMPLETE, LIFE_LOST, World
from entities.enemies import Flyer, Hopper, Shooter, Walker
from entities.projectiles import EnemyProjectile
from tests.helpers import level_from_rows, run, settle, world_from_rows

T = config.TILE_SIZE
DT = config.FIXED_DT


def only(world: World, cls: type):
    """Единственият враг от даден клас в света."""
    found = [enemy for enemy in world.enemies if isinstance(enemy, cls)]
    assert len(found) == 1
    return found[0]


def park_player_far_left(world: World) -> None:
    """Слага героя встрани, за да не пречи на теста."""
    world.player.body.x = 0.0


# --- Walker ------------------------------------------------------------------
def test_walker_turns_at_ledge() -> None:
    """Мъхчо не пада от платформа – обръща се на ръба."""
    world = world_from_rows(
        "P..................X",
        "....................",
        ".......#####........",
        "......E.............",
        "......#####.........",
        "....................",
        "####################",
    )
    walker = only(world, Walker)
    start_row_bottom = walker.body.bottom
    turned = False
    for _ in range(int(6 / DT)):
        facing_before = walker.facing
        world.update(DT, PlayerInput())
        turned = turned or walker.facing != facing_before
        assert walker.body.left >= 6 * T - 1 and walker.body.right <= 11 * T + 1
    assert turned
    assert walker.body.bottom == start_row_bottom


def test_walker_turns_at_wall() -> None:
    """Мъхчо се обръща, когато удари стена."""
    world = world_from_rows("P.........X", "..#...E....", "###########")
    walker = only(world, Walker)
    run(world, 3.0)
    assert walker.facing == 1


# --- скачане върху враг и нараняване ----------------------------------------
STOMP_ROWS = ("..........", "..........", "..........", "..........", "P...E....X",
              "##########")


def drop_player_on(world: World, enemy) -> None:
    """Поставя героя точно над врага и го пуска да пада."""
    player = world.player.body
    player.x = enemy.body.center_x - player.width / 2
    player.y = enemy.body.top - 3 * T
    player.vy = 0.0


def test_stomp_defeats_enemy_and_bounces_player() -> None:
    """Скок отгоре побеждава врага, дава точки и героят отскача нагоре."""
    world = world_from_rows(*STOMP_ROWS)
    walker = only(world, Walker)
    drop_player_on(world, walker)
    bounced = False
    for _ in range(60):
        world.update(DT, PlayerInput())
        if not walker.alive:
            bounced = world.player.body.vy < 0
            break
    assert not walker.alive and bounced
    assert world.session.score == config.POINTS["walker"]
    assert not world.player.is_dead


def test_side_collision_kills_small_player() -> None:
    """Страничен допир с враг наранява: малката форма загива."""
    world = world_from_rows(*STOMP_ROWS)
    settle(world)
    run(world, 2.0, PlayerInput(right=True))
    assert world.player.is_dead


def test_side_collision_shrinks_big_player_with_invulnerability() -> None:
    """Голямата форма става малка, получава неуязвимост и отблъскване."""
    world = world_from_rows(*STOMP_ROWS)
    settle(world)
    world.player.set_form("big")
    walker = only(world, Walker)
    for _ in range(200):
        world.update(DT, PlayerInput(right=True))
        if world.player.form == "small":
            break
    player = world.player
    assert player.form == "small" and not player.is_dead
    assert player.invulnerable_timer > 1.0
    assert player.state.name == "hurt"
    assert (player.body.vx < 0) == (player.body.center_x < walker.body.center_x)


def test_invulnerability_blocks_second_hit_then_expires() -> None:
    """По време на неуязвимостта нов удар не вреди; после – вреди."""
    world = world_from_rows(*STOMP_ROWS)
    settle(world)
    player = world.player
    player.set_form("big")
    player.hurt(world, player.body.center_x + 10)
    assert player.form == "small"
    player.hurt(world, player.body.center_x + 10)
    assert not player.is_dead
    player.invulnerable_timer = 0.0
    player.hurt(world, player.body.center_x + 10)
    assert player.is_dead


def test_life_lost_after_death_animation() -> None:
    """След анимацията на смъртта светът сигнализира загубен живот."""
    world = world_from_rows(*STOMP_ROWS)
    world.player.die(world, "enemy")
    run(world, config.DEATH_ANIMATION_TIME + 0.1)
    assert world.status == LIFE_LOST


# --- Hopper, Flyer, Shooter ---------------------------------------------------
def test_hopper_jumps_toward_player() -> None:
    """Скокльо подскача по посока на героя."""
    world = world_from_rows("..........", "..........", "P.......HX", "##########")
    hopper = only(world, Hopper)
    start_x = hopper.body.x
    jumped = False
    for _ in range(int(3 / DT)):
        world.update(DT, PlayerInput())
        jumped = jumped or hopper.body.vy < 0
    assert jumped
    assert hopper.body.x < start_x


def test_flyer_follows_sine_and_does_not_fall() -> None:
    """Нощничето остава в лентата y0 ± амплитуда."""
    world = world_from_rows("P.........", "..........", "....F.....", "..........",
                            "..........", ".........X", "##########")
    flyer = only(world, Flyer)
    base = flyer.base_y
    lowest = highest = flyer.body.y
    for _ in range(int(3 / DT)):
        world.update(DT, PlayerInput())
        lowest, highest = max(lowest, flyer.body.y), min(highest, flyer.body.y)
    assert highest >= base - config.FLYER_AMPLITUDE - 0.01
    assert lowest <= base + config.FLYER_AMPLITUDE + 0.01
    assert lowest - highest > config.FLYER_AMPLITUDE


def test_shooter_fires_toward_player_in_range() -> None:
    """Бодлоцветът стреля към героя, ако е в обхват."""
    world = world_from_rows("P.....S...X", "###########")
    for _ in range(int(config.SHOOTER_INTERVAL / DT)):
        world.update(DT, PlayerInput())
        if world.enemy_projectiles:
            break
    assert world.enemy_projectiles
    assert world.enemy_projectiles[0].body.vx < 0


def test_shooter_ignores_player_out_of_range() -> None:
    """Извън обхвата бодлоцветът не стреля."""
    world = world_from_rows("P" + "." * 20 + "S..X", "#" * 25)
    run(world, config.SHOOTER_INTERVAL * 2)
    assert not world.enemy_projectiles


def test_enemy_projectile_hurts_player() -> None:
    """Вражески снаряд наранява героя."""
    world = world_from_rows("P........X", "##########")
    settle(world)
    body = world.player.body
    world.add_projectile(EnemyProjectile(body.center_x + 40, body.center_y, -200, 0))
    run(world, 0.5)
    assert world.player.is_dead


def test_shooter_can_be_stomped() -> None:
    """Бодлоцветът също се побеждава със скок отгоре."""
    world = world_from_rows(*[row.replace("E", "S") for row in STOMP_ROWS])
    shooter = only(world, Shooter)
    drop_player_on(world, shooter)
    run(world, 0.5)
    assert not shooter.alive


# --- опасности -----------------------------------------------------------------
def test_spikes_hurt() -> None:
    """Шиповете нараняват (малката форма загива)."""
    world = world_from_rows("P...^....X", "##########")
    settle(world)
    run(world, 1.0, PlayerInput(right=True))
    assert world.player.is_dead and world.player.death_cause == "enemy"


def test_lava_kills_even_big_player() -> None:
    """Лавата убива моментално, дори голямата форма."""
    world = world_from_rows("P........X", "###~~~####", "##########")
    settle(world)
    world.player.set_form("big")
    run(world, 1.0, PlayerInput(right=True))
    assert world.player.is_dead and world.player.death_cause == "lava"


def test_pit_kills() -> None:
    """Падане в пропаст (под картата) е смърт."""
    world = world_from_rows("P........X", "###....###")
    run(world, 2.0, PlayerInput(right=True))
    assert world.player.is_dead and world.player.death_cause == "pit"


def test_time_up_kills() -> None:
    """Изтеклото време отнема живот."""
    level = level_from_rows("P........X", "##########")
    level.meta.time_limit = 1
    world = World(level)
    run(world, 1.1)
    assert world.player.is_dead and world.player.death_cause == "time"


# --- чекпойнти, изход, животи ---------------------------------------------------
CHECKPOINT_ROWS = ("....................", "P.......K..........X", "####################")


def test_checkpoint_changes_respawn_point() -> None:
    """Минаване покрай чекпойнта го запалва и сменя точката на възраждане."""
    world = world_from_rows(*CHECKPOINT_ROWS)
    settle(world)
    run(world, 1.5, PlayerInput(right=True))
    checkpoint = world.checkpoints[0]
    assert checkpoint.activated
    assert world.active_checkpoint == checkpoint.spawn
    assert world.session.checkpoint == ("test", 8, 1)
    respawned = World(world.level, world.session, respawn=world.active_checkpoint)
    assert respawned.player.body.center_x == (8 + 0.5) * T
    assert respawned.checkpoints[0].activated


def test_reaching_exit_completes_level() -> None:
    """Докосването на изхода завършва нивото."""
    world = world_from_rows("P...X", "#####")
    settle(world)
    run(world, 2.0, PlayerInput(right=True))
    assert world.status == COMPLETE


def test_session_lives_and_game_over() -> None:
    """3 загубени живота = край на играта."""
    session = Session()
    assert not session.lose_life()
    assert not session.lose_life()
    assert session.lose_life()


def test_hundred_coins_give_extra_life() -> None:
    """Всеки 100 монети дават допълнителен живот."""
    session = Session()
    extra = [session.add_coin() for _ in range(config.COINS_PER_EXTRA_LIFE)]
    assert extra.count(True) == 1
    assert session.lives == config.START_LIVES + 1
    assert session.coins == 0
