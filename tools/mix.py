"""Voice + a marker sound on every pen stroke + a soft composed bed (all synthesized, nothing to license) -> voice/mix.wav at -14 LUFS."""
import json, re, subprocess
from pathlib import Path
import numpy as np
from scipy import signal
from common import load, run
from voice import ffmpeg_decode

SR = 48000
MIDI = lambda m: 440.0 * 2 ** ((m - 69) / 12.0)
rng = np.random.default_rng(3)


def _pluck(f, dur, vel, bright=0.8):
    n = int(dur * SR); t = np.arange(n) / SR
    ratios, amps, taus = [1, 2, 3, 4.2], [1.0, .42 * bright, .2 * bright, .1 * bright], [.55, .32, .2, .12]
    x = sum(a * np.sin(2 * np.pi * f * r * t + .3 * i) * np.exp(-t / (tau * dur / 1.2)) for i, (r, a, tau) in enumerate(zip(ratios, amps, taus)))
    return x * np.minimum(1, t / .003) * vel * .5


def _pad(freqs, dur, vel):
    n = int(dur * SR); t = np.arange(n) / SR; x = np.zeros(n)
    for f in freqs:
        for det in (-6, 0, 6):
            ff = f * 2 ** (det / 1200.0)
            x += sum(np.sin(2 * np.pi * ff * k * t + k) / k ** 1.8 for k in (1, 2, 3)) / 3
    e = np.ones(n); na = min(n, int(.9 * SR)); nr = min(n, int(1.2 * SR))
    e[:na] = np.sin(np.linspace(0, np.pi / 2, na)) ** 2; e[-nr:] *= np.cos(np.linspace(0, np.pi / 2, nr)) ** 2
    return x * e * vel / len(freqs) ** .7


def composed_bed(N, key=50, bpm=84):
    """I V vi IV, slow arpeggio and pad. Warm and out of the way."""
    out = np.zeros((N + SR * 3, 2))
    beat, bar = 60 / bpm, 240 / bpm
    triads = [(0, 4, 7), (7, 11, 14), (9, 12, 16), (5, 9, 12)]

    def put(sig, t, pan=0.0):
        i = int(t * SR)
        if i >= out.shape[0]:
            return
        s = sig[:out.shape[0] - i]
        out[i:i + len(s), 0] += s * (1 - max(0, pan))
        out[i:i + len(s), 1] += s * (1 + min(0, pan))

    t, k = 0.0, 0
    while t < N / SR:
        tri = [key + x for x in triads[k % 4]]
        put(_pad([MIDI(n) for n in tri], bar + .6, .22), t)
        up = [n + 12 for n in tri] + [tri[0] + 24]
        for i, idx in enumerate([0, 1, 2, 1, 0, 1, 2, 3]):
            put(_pluck(MIDI(up[idx]), 1.1, .2 * (1.0 if i % 4 == 0 else .7)), t + i * beat / 2, -.15 if i % 2 else .15)
        t += bar; k += 1
    x = out[:N]
    # a little room
    ir = rng.standard_normal(int(1.3 * SR)) * np.exp(-6.9 * np.arange(int(1.3 * SR)) / (1.2 * SR))
    for c in range(2):
        wet = signal.fftconvolve(x[:, c], ir, 'full')[:N]
        x[:, c] = x[:, c] * .88 + wet / (np.abs(ir).max() * 40)
    return x


def lufs(path):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-af', 'ebur128=framelog=quiet', '-f', 'null', '-'], capture_output=True, text=True)
    return float(re.findall(r'I:\s+(-?[\d.]+) LUFS', r.stderr)[-1])


def _squeaky_marker(pen, N, vo, cfg):
    """Tonal stick-slip dry-erase squeaks + ultra-soft high-frequency felt glide (zero low-mid static/grain)."""
    squeak = np.zeros(N, np.float32)
    glide_env = np.zeros(N, np.float32)

    for idx, g in enumerate(pen):
        i0, i1 = int(g['t0'] * SR), min(N, int(g['t1'] * SR))
        n = i1 - i0
        if n < 64:
            continue
        dur = n / SR
        spd = float(np.clip(g['v'] / 2600.0, 0.5, 1.35))
        is_fill = g.get('layer') == 'fill'

        # Very gentle felt glide envelope (high-passed later, purely airy)
        e = np.ones(n, np.float32)
        at, rel = min(n // 3, int(.012 * SR)), min(n // 3, int(.035 * SR))
        e[:at] = np.linspace(0, 1, at)
        e[n - rel:] = np.linspace(1, 0, rel)
        glide_env[i0:i1] = np.maximum(glide_env[i0:i1], e * (0.65 if is_fill else 0.45) * spd)

        # Place clean tonal stick-slip squeak chirps along the stroke
        chirps = []
        if is_fill:
            step = rng.uniform(0.085, 0.125)
            t = 0.015
            up = True
            while t + 0.04 < dur:
                cd = float(min(rng.uniform(0.042, 0.072), dur - t))
                f0 = float(rng.uniform(2350, 2950))
                df = float(rng.uniform(260, 520)) * (1 if up else -0.85)
                chirps.append((t, cd, f0, df, 0.85))
                t += step
                up = not up
        elif dur <= 0.24:
            if dur > 0.055 and (idx % 2 == 0 or rng.random() < 0.55):
                cd = float(min(dur * 0.72, rng.uniform(0.045, 0.085)))
                t = float(rng.uniform(0.0, max(0.005, dur - cd)))
                f0 = float(rng.uniform(2550, 3450))
                df = float(rng.uniform(-320, 460))
                chirps.append((t, cd, f0, df, 0.75 * spd))
        else:
            t = float(rng.uniform(0.02, 0.14))
            while t + 0.05 < dur:
                cd = float(min(rng.uniform(0.055, 0.125), dur - t))
                f0 = float(rng.uniform(2250, 3400))
                df = float(rng.uniform(-380, 580))
                chirps.append((t, cd, f0, df, float(rng.uniform(0.55, 1.0)) * spd))
                t += float(rng.uniform(0.18, 0.34))

        for t_rel, cd, f0, df, amp in chirps:
            c0 = i0 + int(t_rel * SR)
            cn = min(N - c0, int(cd * SR))
            if cn < 48:
                continue
            u = np.linspace(0.0, 1.0, cn, dtype=np.float64)
            # Smooth curved frequency glide + tiny organic vibrato
            freq = f0 + df * np.sin(np.pi * u / 2.0) + 28.0 * np.sin(2 * np.pi * 16.0 * u * cd)
            phase = 2.0 * np.pi * np.cumsum(freq) / SR
            tone = np.sin(phase) + 0.24 * np.sin(2.0 * phase + 0.4) + 0.06 * np.sin(3.0 * phase + 0.9)
            win = (np.sin(np.pi * u) ** 1.6).astype(np.float32)
            squeak[c0:c0 + cn] += (tone.astype(np.float32) * win * amp)

    # Whisper-soft high-frequency felt silk (strictly >3.6 kHz, zero low/mid grit)
    b, a = signal.butter(2, [3600 / (SR / 2), 6800 / (SR / 2)], 'band')
    silk = signal.lfilter(b, a, rng.standard_normal(N)).astype(np.float32)
    silk = silk / (np.sqrt(np.mean(silk ** 2)) + 1e-9) * 0.045 * glide_env
    if (np.abs(squeak) > 1e-4).any():
        squeak = squeak / (np.sqrt(np.mean(squeak[np.abs(squeak) > 1e-4] ** 2)) + 1e-9)
    return squeak + silk


def mix(film, pen, target=-14.0):
    cfg = load(film / 'film.json')
    vo = ffmpeg_decode(film / 'voice/paced.wav'); N = len(vo)
    active_vo = np.abs(vo) > 0.015
    vo_rms = float(np.sqrt(np.mean(vo[active_vo] ** 2))) if active_vo.any() else 0.12

    win_fast = int(.07 * SR)
    venv_fast = signal.fftconvolve(np.abs(vo), np.ones(win_fast) / win_fast, 'same')
    venv_fast = venv_fast / (np.percentile(venv_fast[active_vo], 85) + 1e-9) if active_vo.any() else venv_fast
    win_gate = int(.05 * SR)
    speech_gate = signal.fftconvolve(np.clip(venv_fast * 3.0, 0, 1), np.ones(win_gate) / win_gate, 'same')

    if cfg.get('marker_style', 'squeaky') == 'felt':
        b, a = signal.butter(2, [1800 / (SR / 2), 7000 / (SR / 2)], 'band')
        felt = signal.lfilter(b, a, rng.standard_normal(N))
        b2, a2 = signal.butter(2, [600 / (SR / 2), 2400 / (SR / 2)], 'band')
        body = signal.lfilter(b2, a2, rng.standard_normal(N))
        env = np.zeros(N, np.float32)
        for g in pen:
            i0, i1 = int(g['t0'] * SR), min(N, int(g['t1'] * SR))
            n = i1 - i0
            if n < 64:
                continue
            e = np.ones(n, np.float32)
            at, rel = min(n // 3, int(.008 * SR)), min(n // 3, int(.03 * SR))
            e[:at] = np.linspace(0, 1, at); e[n - rel:] = np.linspace(1, 0, rel)
            lvl = np.clip(g['v'] / 2600, .45, 1.0) * (1.25 if g['layer'] == 'fill' else 1.0)
            tt = np.arange(n) / SR
            flutter = .75 + .25 * np.sin(2 * np.pi * (11 if g['layer'] == 'fill' else 5.5) * tt + rng.uniform(0, 6))
            env[i0:i1] = np.maximum(env[i0:i1], e * lvl * flutter)
        marker = (.75 * felt + .35 * body) * env
        if (env > 0).any():
            marker *= 10 ** (cfg.get('marker_db', -31) / 20) / (np.sqrt(np.mean(marker[env > 0] ** 2)) + 1e-9)
    else:
        marker = _squeaky_marker(pen, N, vo, cfg)
        active_m = np.abs(marker) > 1e-4
        if active_m.any():
            # Target marker level relative to actual voice RMS so voice always dominates
            rel_db = float(cfg.get('marker_rel_db', -20.0))
            marker_duck = (1.0 - 0.65 * speech_gate).astype(np.float32)  # -9 dB deeper under active speech
            marker = marker * (vo_rms * 10 ** (rel_db / 20.0) / (np.sqrt(np.mean(marker[active_m] ** 2)) + 1e-9)) * marker_duck

    out = np.zeros((N, 2), np.float32)
    out += vo[:, None] + marker[:, None] * np.array([.92, 1.0], np.float32)
    music = cfg.get('music', 'composed')
    margin = None
    marker_margin = None
    win = int(.25 * SR)
    active = np.abs(signal.fftconvolve(np.abs(vo), np.ones(win) / win, 'same')) > .02
    if active.any() and (np.abs(marker[active]) > 1e-6).any():
        marker_margin = 20 * np.log10(np.sqrt(np.mean(vo[active] ** 2)) / (np.sqrt(np.mean(marker[active] ** 2)) + 1e-9))
    if music and music != 'none':
        if music == 'composed':
            bed = composed_bed(N)
        else:
            raw = ffmpeg_decode(Path(music).expanduser(), 2).reshape(-1, 2)
            bed = np.vstack([raw] * (N // len(raw) + 1))[:N]
        fade = np.ones(N, np.float32); fi, fo = min(N, int(.6 * SR)), min(N, int(2.5 * SR))
        fade[:fi] = np.linspace(0, 1, fi); fade[N - fo:] = np.linspace(1, 0, fo)
        venv = signal.fftconvolve(np.abs(vo), np.ones(win) / win, 'same'); venv = venv / (venv.max() + 1e-9)
        duck = 1 - .52 * np.clip(venv * 6, 0, 1)
        win_duck = int(.12 * SR)
        duck = signal.fftconvolve(duck, np.ones(win_duck) / win_duck, 'same')
        # Keep music comfortably below voice RMS regardless of raw take gain
        bed_rel_db = float(cfg.get('music_rel_db', -18.0))
        bed = bed * (fade * duck)[:, None] * (vo_rms * 10 ** (bed_rel_db / 20.0)) / (np.sqrt(np.mean(bed ** 2)) + 1e-9)
        out = out + bed.astype(np.float32)
        if active.any():
            margin = 20 * np.log10(np.sqrt(np.mean(vo[active] ** 2)) / (np.sqrt(np.mean(bed[active] ** 2)) + 1e-9))
    out /= max(1.0, np.abs(out).max() / .95)
    tmp = film / 'voice/_mix.wav'
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-i', '-', '-c:a', 'pcm_s24le', tmp], input=out.tobytes())
    g = target - lufs(tmp)
    run(['ffmpeg', '-y', '-v', 'error', '-i', tmp, '-af', f'volume={g:.2f}dB,alimiter=limit=0.84:level=false:attack=3:release=40', '-ar', str(SR), '-c:a', 'pcm_s24le', film / 'voice/mix.wav'])
    tmp.unlink()
    final = lufs(film / 'voice/mix.wav')
    msg = f'mix: {final:.1f} LUFS'
    if margin is not None:
        msg += f', voice sits {margin:.0f} dB above music'
    else:
        msg += ', no music'
    if marker_margin is not None:
        msg += f', {marker_margin:.0f} dB above marker'
    print(msg + '. You cannot hear this: ask the user to listen.')
    if margin is not None and margin < 9:
        print('NOTE: the music is close to the voice. Lower music_rel_db in film.json (9 dB or more of margin is safest).')
    return final
