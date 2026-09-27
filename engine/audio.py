"""Програмно генерирани звукови ефекти (без нито един аудио файл).

Звукът е поредица от числа (семпли) – моментното отклонение на мембраната на
говорителя. При честота на дискретизация 22050 Hz една секунда звук е 22050
числа. Генерираме ги с прости формули:

* **квадратна вълна** (square) – „8-битов“ звук: +1 или −1 според фазата;
* **синусоида** (sine) – мек, чист тон;
* **шум** (noise) – случайни стойности, за удари и чупене.

Честотата може да се плъзга от начална към крайна (sweep) – така скокът звучи
„нагоре“, а смъртта „надолу“. Обвивката (envelope) заглушава края плавно, за да
няма пукане.

Ако звуковата карта липсва, играта продължава без звук.
"""
from __future__ import annotations

import math
import random
from array import array
from dataclasses import dataclass

import pygame

import config

MAX_AMPLITUDE = 32767


@dataclass(frozen=True)
class Tone:
    """Един сегмент от звук.

    Attributes:
        start_hz: начална честота.
        end_hz: крайна честота (за плъзгане).
        duration: продължителност в секунди.
        wave: "square", "sine" или "noise".
        volume: сила 0..1.
    """

    start_hz: float
    end_hz: float
    duration: float
    wave: str = "square"
    volume: float = 1.0


def _sample(wave: str, phase: float, rng: random.Random) -> float:
    """Стойност на вълната при дадена фаза (0..1 = един период)."""
    if wave == "sine":
        return math.sin(2 * math.pi * phase)
    if wave == "noise":
        return rng.uniform(-1.0, 1.0)
    return 1.0 if phase % 1.0 < 0.5 else -1.0


def synthesize(tones: list[Tone], sample_rate: int = config.AUDIO_SAMPLE_RATE) -> array:
    """Превръща списък от тонове в 16-битови моно семпли."""
    samples = array("h")
    rng = random.Random(1)
    phase = 0.0
    for tone in tones:
        count = max(1, int(tone.duration * sample_rate))
        for index in range(count):
            progress = index / count
            frequency = tone.start_hz + (tone.end_hz - tone.start_hz) * progress
            phase += frequency / sample_rate
            envelope = (1.0 - progress) ** 1.5          # плавно заглъхване
            attack = min(1.0, index / (sample_rate * 0.003))   # без пукане в началото
            value = _sample(tone.wave, phase, rng) * envelope * attack * tone.volume
            samples.append(int(value * MAX_AMPLITUDE * 0.5))
    return samples


def _notes(frequencies: tuple[float, ...], duration: float, wave: str = "square") -> list[Tone]:
    """Мелодия от отделни ноти с еднаква дължина."""
    return [Tone(freq, freq, duration, wave) for freq in frequencies]


#: Рецептите на всички звуци.
SOUND_RECIPES: dict[str, list[Tone]] = {
    "jump": [Tone(320, 640, 0.14)],
    "coin": [Tone(988, 988, 0.07), Tone(1319, 1319, 0.22)],
    "stomp": [Tone(220, 70, 0.14)],
    "hurt": [Tone(640, 180, 0.3), Tone(200, 120, 0.1, "noise", 0.4)],
    "powerup": _notes((523, 659, 784, 1047, 1319), 0.07),
    "powerup_appear": [Tone(300, 700, 0.3, "sine")],
    "die": [Tone(784, 740, 0.12), Tone(700, 90, 0.8)],
    "bump": [Tone(140, 110, 0.07)],
    "break": [Tone(400, 100, 0.25, "noise")],
    "shoot": [Tone(900, 380, 0.1)],
    "enemy_shoot": [Tone(420, 240, 0.09, "sine")],
    "checkpoint": _notes((660, 880, 1175), 0.1, "sine"),
    "crystal": _notes((1047, 1319, 1568, 2093), 0.06, "sine"),
    "oneup": _notes((659, 784, 1319, 1047, 1175, 1568), 0.08),
    "star": _notes((523, 784, 1047, 784, 1047, 1568), 0.06),
    "boss_hit": [Tone(160, 60, 0.3), Tone(120, 60, 0.15, "noise", 0.6)],
    "boss_land": [Tone(90, 40, 0.35, "noise")],
    "boss_summon": [Tone(200, 400, 0.2, "sine")],
    "exit_open": _notes((392, 523, 659, 784), 0.12, "sine"),
    "level_complete": _notes((523, 659, 784, 1047, 784, 1047), 0.12, "sine"),
    "menu_move": [Tone(660, 660, 0.04)],
    "menu_select": [Tone(880, 1320, 0.09)],
    "pause": [Tone(440, 330, 0.12, "sine")],
}

#: Кое събитие от света кой звук пуска (ако името е различно).
EVENT_SOUNDS: dict[str, str] = {
    "enemy_stomp": "stomp", "enemy_fireball": "stomp", "enemy_star": "stomp",
    "fireball_pop": "bump",
}


class Audio:
    """Зарежда (генерира) звуците и ги пуска по име.

    Args:
        enabled: False изключва звука напълно (напр. в тестове).
    """

    def __init__(self, enabled: bool = config.AUDIO_ENABLED) -> None:
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.enabled = enabled and self._init_mixer()
        if self.enabled:
            self._build_sounds()

    @staticmethod
    def _init_mixer() -> bool:
        """Инициализира миксера; връща False, ако няма звуково устройство."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=config.AUDIO_SAMPLE_RATE, size=-16, channels=1)
        except pygame.error:
            return False
        return pygame.mixer.get_init() is not None

    def _build_sounds(self) -> None:
        """Генерира всички звуци според реалния формат на миксера (моно/стерео)."""
        frequency, _size, channels = pygame.mixer.get_init()
        for name, tones in SOUND_RECIPES.items():
            mono = synthesize(tones, frequency)
            if channels > 1:   # стерео: всяко семпле се повтаря за всеки канал
                data = array("h", (value for value in mono for _ in range(channels)))
            else:
                data = mono
            sound = pygame.mixer.Sound(buffer=data.tobytes())
            sound.set_volume(config.AUDIO_VOLUME)
            self.sounds[name] = sound

    def play(self, name: str) -> None:
        """Пуска звук по име (или по име на събитие); непознатите се пренебрегват."""
        if not self.enabled:
            return
        sound = self.sounds.get(EVENT_SOUNDS.get(name, name))
        if sound is not None:
            sound.play()
