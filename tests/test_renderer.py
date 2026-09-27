"""Тестове за рисуването (headless): debug режимът показва хитбоксове."""
from __future__ import annotations

import pygame

import config
from engine.game import Game
from engine.states import Playing, new_session


def hitbox_corner_color(debug: bool) -> tuple[int, int, int]:
    """Рисува кадър и връща цвета на пиксела в горния ляв ъгъл на хитбокса на героя."""
    game = Game(debug=debug)
    playing = Playing(game, new_session())
    game.start(playing)
    game.step_frame(config.FIXED_DT)
    offset_x, offset_y = playing.camera.offset
    rect = playing.world.player.body.rect().move(-offset_x, -offset_y)
    color = game.screen.get_at(rect.topleft)
    return color.r, color.g, color.b


def test_debug_mode_draws_hitboxes() -> None:
    """С включен debug ъгълът на хитбокса е оцветен в DEBUG_HITBOX."""
    assert hitbox_corner_color(debug=True) == config.DEBUG_HITBOX


def test_normal_mode_has_no_hitboxes() -> None:
    """Без debug хитбоксовете не се рисуват."""
    assert hitbox_corner_color(debug=False) != config.DEBUG_HITBOX


def test_f1_toggles_debug() -> None:
    """Действието `debug` (F1) превключва режима."""
    game = Game()
    game.start(Playing(game, new_session()))
    game.input.handle_key(pygame.K_F1, True)
    game.step_frame(config.FIXED_DT)
    assert game.debug
