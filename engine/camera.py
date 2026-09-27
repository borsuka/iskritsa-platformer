"""Камера, която следва героя плавно.

Три идеи работят заедно:
1. **Dead zone** – правоъгълник в средата на екрана. Докато героят е вътре,
   камерата не мърда. Така малките движения напред-назад не „клатят“ картината.
2. **Изглаждане (lerp)** – камерата не скача до желаната позиция, а изминава
   част от разстоянието всяка стъпка: x += (цел − x) · (1 − e^(−k·dt)).
   Формулата с експонента дава едно и също усещане при всяко dt.
3. **Look-ahead** – фокусът се измества малко напред по посоката на движение,
   за да се вижда повече от това, към което тичаме.

Накрая позицията се ограничава в границите на нивото. Логиката не зависи от
дисплей, затова се тества без прозорец.
"""
from __future__ import annotations

import math

import config
from physics.kinematics import approach


class Camera:
    """Изгледът върху света.

    Args:
        view_width: ширина на екрана.
        view_height: височина на екрана.
        world_width: ширина на нивото в пиксели.
        world_height: височина на нивото в пиксели.
    """

    def __init__(self, view_width: int, view_height: int, world_width: int,
                 world_height: int) -> None:
        self.view_width = view_width
        self.view_height = view_height
        self.world_width = world_width
        self.world_height = world_height
        self.x = 0.0
        self.y = 0.0
        self.look_ahead = 0.0
        self.shake_time = 0.0
        self.shake_duration = 0.0
        self.shake_strength = 0.0

    # --- следене -----------------------------------------------------------
    def snap_to(self, target_x: float, target_y: float) -> None:
        """Мигновено центрира камерата върху точка (при старт и възраждане)."""
        self.look_ahead = 0.0
        self.x = target_x - self.view_width / 2
        self.y = target_y - self.view_height / 2
        self._clamp()

    def update(self, target_x: float, target_y: float, target_vx: float, dt: float) -> None:
        """Една стъпка на следене.

        Args:
            target_x: центърът на героя по X.
            target_y: центърът на героя по Y.
            target_vx: хоризонталната скорост на героя (за look-ahead).
            dt: стъпка по време.
        """
        self._update_look_ahead(target_vx, dt)
        desired_x = self._follow_axis(self.x, target_x + self.look_ahead, self.view_width,
                                      config.CAMERA_DEAD_ZONE_WIDTH)
        desired_y = self._follow_axis(self.y, target_y, self.view_height,
                                      config.CAMERA_DEAD_ZONE_HEIGHT)
        blend = 1.0 - math.exp(-config.CAMERA_SMOOTHING * dt)
        self.x += (desired_x - self.x) * blend
        self.y += (desired_y - self.y) * blend
        self._clamp()
        self.shake_time = max(0.0, self.shake_time - dt)

    def _update_look_ahead(self, target_vx: float, dt: float) -> None:
        """Плавно премества фокуса напред по посоката на движение."""
        if abs(target_vx) > config.CAMERA_LOOK_AHEAD_MIN_SPEED:
            wanted = math.copysign(config.CAMERA_LOOK_AHEAD, target_vx)
        else:
            wanted = self.look_ahead
        step = config.CAMERA_LOOK_AHEAD * config.CAMERA_LOOK_AHEAD_SPEED * dt
        self.look_ahead = approach(self.look_ahead, wanted, step)

    @staticmethod
    def _follow_axis(camera: float, focus: float, view: float, dead_zone: float) -> float:
        """Къде трябва да е камерата по една ос, за да е фокусът в dead zone."""
        zone_start = camera + (view - dead_zone) / 2
        zone_end = zone_start + dead_zone
        if focus < zone_start:
            return camera - (zone_start - focus)
        if focus > zone_end:
            return camera + (focus - zone_end)
        return camera

    def _clamp(self) -> None:
        """Не позволява на камерата да покаже нещо извън нивото."""
        self.x = self._clamp_axis(self.x, self.view_width, self.world_width)
        self.y = self._clamp_axis(self.y, self.view_height, self.world_height)

    @staticmethod
    def _clamp_axis(value: float, view: float, world: float) -> float:
        """Ограничава една ос; ако нивото е по-малко от екрана – центрира го."""
        if world <= view:
            return (world - view) / 2
        return min(max(value, 0.0), world - view)

    # --- разклащане ----------------------------------------------------------
    def shake(self, duration: float = config.SCREEN_SHAKE_TIME,
              strength: float = config.SCREEN_SHAKE_STRENGTH) -> None:
        """Започва разклащане на екрана (напр. при приземяване на боса)."""
        self.shake_time = duration
        self.shake_duration = duration
        self.shake_strength = strength

    @property
    def offset(self) -> tuple[int, int]:
        """Отместването за рисуване (в цели пиксели, включително разклащането).

        Разклащането е детерминирано (синуси), за да остане логиката повторяема.
        """
        shake_x = shake_y = 0.0
        if self.shake_time > 0 and self.shake_duration > 0:
            fade = self.shake_time / self.shake_duration
            shake_x = math.sin(self.shake_time * 90.0) * self.shake_strength * fade
            shake_y = math.cos(self.shake_time * 70.0) * self.shake_strength * fade
        return round(self.x + shake_x), round(self.y + shake_y)
