#!/usr/bin/env python3
"""
Synthesize the crisp "glass tick" key sounds (sounds/*.wav, 44.1 kHz mono 16 bit).

A tap on glass is a very short broadband click followed by a few inharmonic partials that die
away within a few milliseconds. That is what makes it sound crisp instead of "clicky" or "boingy":

  - a ~1 ms noise burst, high-passed, for the contact transient,
  - 3 partials at ratios 1 : 2.32 : 4.03 (not harmonics, like a small glass plate), higher ones
    decaying faster,
  - 0.25 ms raised-cosine attack and a 4 ms fade-out so that there is never a pop,
  - total length 60 ms, so fast typing does not smear.

Usage:  python3 tools/make_sounds.py [out_dir]    (default: sounds/)
"""

import sys
import wave
from pathlib import Path

import numpy as np

SR = 44100
RNG = np.random.default_rng(20251030)


def t_axis(duration):
    return np.arange(int(SR * duration)) / SR


def tick(f0, partials, duration, click=0.5, thump=None, chirp=None, offset=0.0, gain=1.0, length=None):
    """One tap. partials: (ratio, amplitude, decay seconds). thump: (Hz, amplitude, decay) low body.
    chirp: (end Hz, over seconds) glide of the fundamental."""
    n = int(SR * (length if length is not None else duration))
    out = np.zeros(n)
    t = t_axis(duration)

    # contact transient: high-passed noise, a millisecond long
    nb = int(SR * 0.003)
    noise = RNG.standard_normal(nb + 2)
    noise = np.diff(np.diff(noise))  # 2nd difference = steep high-pass
    noise = noise[:nb] / np.max(np.abs(noise[:nb]))
    body = np.zeros_like(t)
    body[:nb] += click * noise * np.exp(-np.arange(nb) / SR / 0.0005)

    for ratio, amp, tau in partials:
        f = f0 * ratio
        if chirp and ratio == 1:
            f_end, over = chirp
            fi = f + (f_end - f) * np.clip(t / over, 0, 1)
            phase = 2 * np.pi * np.cumsum(fi) / SR
        else:
            phase = 2 * np.pi * f * t
        body += amp * np.sin(phase) * np.exp(-t / tau)
    if thump:
        fh, amp, tau = thump
        body += amp * np.sin(2 * np.pi * fh * t) * np.exp(-t / tau)

    attack = np.clip(t / 0.00025, 0, 1)
    body *= np.sin(attack * np.pi / 2) ** 2
    fade = int(SR * 0.004)
    body[-fade:] *= np.cos(np.linspace(0, np.pi / 2, fade)) ** 2

    start = int(SR * offset)
    out[start:start + len(body)] += gain * body[: n - start]
    return out


def finish(x, peak=0.85):
    x = x / np.max(np.abs(x)) * peak
    return np.round(x * 32767).astype(np.int16)


GLASS = ((1.0, 1.00, 9e-3), (2.32, 0.55, 6e-3), (4.03, 0.30, 3.5e-3))

SOUNDS = {
    "glass_key": lambda: tick(3300, GLASS, 0.060),
    # lower and a little longer, with a soft body underneath
    "glass_space": lambda: tick(2200, ((1.0, 1.0, 14e-3), (2.1, 0.5, 8e-3), (3.7, 0.25, 4e-3)), 0.090,
                                click=0.4, thump=(170, 0.6, 15e-3)),
    # a slightly falling tone, softer, reads as "removed"
    "glass_delete": lambda: tick(2900, ((1.0, 1.0, 8e-3), (2.32, 0.4, 5e-3), (4.03, 0.2, 3e-3)), 0.070,
                                 click=0.35, chirp=(2450, 0.03)),
    # two taps, the second one higher, reads as "done"
    "glass_return": lambda: tick(3300, GLASS, 0.060, length=0.110)
                            + tick(4400, GLASS, 0.060, offset=0.038, gain=0.8, length=0.110),
}


def analyse(name, pcm):
    x = pcm.astype(np.float64) / 32767
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / SR)
    centroid = (spec * freqs).sum() / spec.sum()
    energy = np.cumsum(x ** 2)
    t90 = np.searchsorted(energy, 0.9 * energy[-1]) / SR * 1000
    print(f"{name:13s} {len(x) / SR * 1000:5.0f} ms  peak {np.max(np.abs(x)):.2f}  "
          f"90% of energy within {t90:4.1f} ms  spectral centroid {centroid / 1000:4.1f} kHz  "
          f"first/last sample {pcm[0]}/{pcm[-1]}")


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "sounds"
    out.mkdir(parents=True, exist_ok=True)
    for name, make in SOUNDS.items():
        pcm = finish(make())
        analyse(name, pcm)
        with wave.open(str(out / f"{name}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    main()
