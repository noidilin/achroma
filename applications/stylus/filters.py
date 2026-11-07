"""Deterministic CSS filter fitting. No network or third-party dependencies."""

import math
import random

VERSION = 1
MAX_ERROR = 8.0  # maximum absolute error per sRGB channel (0..255)


def apply(values):
    """Apply invert/sepia/saturate/hue-rotate/brightness/contrast to black."""
    invert, sepia, saturation, hue, brightness, contrast = values
    rgb = [invert] * 3
    matrix = (
        (.393, .769, .189),
        (.349, .686, .168),
        (.272, .534, .131),
    )
    rgb = [min(1, max(0, (1 - sepia) * rgb[i] + sepia * sum(
        row[j] * rgb[j] for j in range(3)))) for i, row in enumerate(matrix)]
    lum = sum(a * b for a, b in zip(rgb, (.213, .715, .072)))
    rgb = [min(1, max(0, lum + saturation * (x - lum))) for x in rgb]
    cos, sin = math.cos(hue), math.sin(hue)
    matrix = (
        (.213 + cos * .787 - sin * .213, .715 - cos * .715 - sin * .715, .072 - cos * .072 + sin * .928),
        (.213 - cos * .213 + sin * .143, .715 + cos * .285 + sin * .140, .072 - cos * .072 - sin * .283),
        (.213 - cos * .213 - sin * .787, .715 - cos * .715 + sin * .715, .072 + cos * .928 + sin * .072),
    )
    rgb = [min(1, max(0, sum(a * b for a, b in zip(row, rgb)))) for row in matrix]
    rgb = [min(1, max(0, x * brightness)) for x in rgb]
    return [255 * min(1, max(0, (x - .5) * contrast + .5)) for x in rgb]


def fit(color):
    target = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    rng = random.Random(int(color[1:], 16))
    bounds = ((0, 1), (0, 1), (0, 80), (0, 2 * math.pi), (0, 2), (0, 2))

    def loss(values):
        return sum((a - b) ** 2 for a, b in zip(apply(values), target))

    best, best_loss = None, float('inf')
    # Coordinate search with seeded restarts. Grays have an exact invert solution.
    if max(target) == min(target):
        best = [target[0] / 255, 0, 1, 0, 1, 1]
    else:
        for restart in range(32):
            values = [sum(target) / 765, rng.random(), rng.uniform(0, 8),
                      rng.uniform(0, 2 * math.pi), 1, 1]
            score = loss(values)
            for scale in (.2, .08, .03, .01, .003, .001, .0003):
                for _ in range(60):
                    changed = False
                    for axis, (low, high) in enumerate(bounds):
                        step = (high - low) * scale
                        for sign in (-1, 1):
                            trial = values.copy()
                            trial[axis] = min(high, max(low, trial[axis] + sign * step))
                            trial_score = loss(trial)
                            if trial_score < score:
                                values, score, changed = trial, trial_score, True
                    if not changed:
                        break
            if score < best_loss:
                best, best_loss = values, score
            if max(abs(a - b) for a, b in zip(apply(best), target)) < .5:
                break
    # Quantize before evaluating so the report measures the emitted filter.
    inv, sep, sat, hue, bright, contrast = best
    emitted = [round(inv * 100, 4) / 100, round(sep * 100, 4) / 100,
               round(sat * 100, 4) / 100, math.radians(round(math.degrees(hue), 4)),
               round(bright * 100, 4) / 100, round(contrast * 100, 4) / 100]
    error = max(abs(a - b) for a, b in zip(apply(emitted), target))
    if error > MAX_ERROR:
        raise ValueError(f'Cannot fit filter for {color}: channel error {error:.2f} > {MAX_ERROR}')
    css = (f'brightness(0) saturate(100%) invert({emitted[0] * 100:.4f}%) '
           f'sepia({emitted[1] * 100:.4f}%) saturate({emitted[2] * 100:.4f}%) '
           f'hue-rotate({math.degrees(emitted[3]):.4f}deg) '
           f'brightness({emitted[4] * 100:.4f}%) contrast({emitted[5] * 100:.4f}%)')
    return {'css': css, 'max_channel_error': round(error, 4)}
