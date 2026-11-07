"""Validated default filter lock and seeded, platform-dependent custom fitting."""

import hashlib
import json
import math
from pathlib import Path
import random
import re

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


def palette_digest(palettes):
    return hashlib.sha256(json.dumps(palettes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def locked(palettes, path):
    """Validate canonical derived input; never fall back to a cache or fitter."""
    def require(condition, message):
        if not condition:
            raise ValueError(f'Filter lock: {message}')

    def keys(value, expected, label):
        require(isinstance(value, dict) and set(value) == set(expected), f'{label}: unexpected fields')

    def checksum(value, length, label):
        require(isinstance(value, str) and re.fullmatch(f'[0-9a-f]{{{length}}}', value) is not None,
                f'{label}: invalid digest')

    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f'duplicate JSON field: {key}')
            result[key] = value
        return result

    lock = json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)
    keys(lock, ('schemaVersion', 'fitterVersion', 'resolvedPalettesSha256', 'provenance', 'filters'), 'root')
    require(type(lock['schemaVersion']) is int and lock['schemaVersion'] == 1, 'unsupported schema version')
    require(type(lock['fitterVersion']) is int and lock['fitterVersion'] == VERSION, 'unsupported fitter version')
    checksum(lock['resolvedPalettesSha256'], 64, 'resolved palettes')
    require(lock['resolvedPalettesSha256'] == palette_digest(palettes), 'stale resolved palettes digest')
    provenance = lock['provenance']
    keys(provenance, ('sourceRevision', 'sourceArchiveSha256', 'nativeArtifacts', 'runtime', 'note'), 'provenance')
    checksum(provenance['sourceRevision'], 40, 'source revision')
    checksum(provenance['sourceArchiveSha256'], 64, 'source archive')
    keys(provenance['nativeArtifacts'], ('import.json', 'lib.less'), 'native artifacts')
    for value in provenance['nativeArtifacts'].values():
        checksum(value, 64, 'native artifact')
    for name in ('runtime', 'note'):
        require(isinstance(provenance[name], str) and bool(provenance[name].strip()), f'invalid {name}')
    colors = {color for palette in palettes.values() for color in palette.values()}
    keys(lock['filters'], colors, 'resolved color coverage')
    result = {}
    bounds = ((0, 100), (0, 100), (0, 8000), (0, 360), (0, 200), (0, 200))
    for color, record in lock['filters'].items():
        require(isinstance(color, str) and re.fullmatch('#[0-9a-f]{6}', color) is not None, 'invalid color')
        keys(record, ('parameters', 'maxChannelError'), color)
        parameters = record['parameters']
        require(isinstance(parameters, list) and len(parameters) == 6, f'{color}: expected six parameters')
        for value, (low, high) in zip(parameters, bounds):
            require(type(value) in (int, float) and low <= value <= high and math.isfinite(value)
                    and round(value, 4) == value, f'{color}: invalid rounded parameter')
        reported = record['maxChannelError']
        require(type(reported) in (int, float) and 0 <= reported <= MAX_ERROR and math.isfinite(reported),
                f'{color}: invalid reported error')
        inv, sep, sat, hue, bright, contrast = parameters
        emitted = [inv / 100, sep / 100, sat / 100, math.radians(hue), bright / 100, contrast / 100]
        target = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
        error = max(abs(a - b) for a, b in zip(apply(emitted), target))
        require(error <= MAX_ERROR, f'{color}: emitted filter exceeds channel tolerance')
        require(round(error, 4) == reported, f'{color}: reported error disagrees with emitted filter')
        css = (f'brightness(0) saturate(100%) invert({inv:.4f}%) sepia({sep:.4f}%) '
               f'saturate({sat:.4f}%) hue-rotate({hue:.4f}deg) '
               f'brightness({bright:.4f}%) contrast({contrast:.4f}%)')
        result[color] = {'css': css, 'max_channel_error': reported}
    return result


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
