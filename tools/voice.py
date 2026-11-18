"""The narration is the film's clock: lock the take, find when every word is spoken, then add breathing room."""
import base64, json, re, sys, urllib.error, urllib.request, wave
from difflib import SequenceMatcher
from pathlib import Path
import numpy as np
from common import ffmpeg, load, norm, probe_duration, run, save, die, TOOLS, HOME

SR = 48000
TTS_MODEL = 'gemini-2.5-flash-preview-tts'
ALLOWED_TTS_MODELS = [
    'gemini-2.5-flash-preview-tts',
    'gemini-2.0-flash',
    'gemini-1.5-flash',
    'gemini-2.5-pro',
]


def script_words(film):
    text = (film / 'script.md').read_text(encoding='utf-8') if (film / 'script.md').exists() else ''
    text = '\n'.join(l for l in text.splitlines() if not l.strip().startswith('#'))
    return re.findall(r"\S+", text)


def get_keys():
    import os, re
    candidates = []
    for env_var in ['GEMINI_API_KEYS', 'GEMINI_API_KEY']:
        raw = os.environ.get(env_var, '').strip()
        if raw:
            candidates.extend(re.split(r'[\r\n,;\s]+', raw))
    p = Path.home() / '.flow-mcp' / 'gemini-key'
    if p.exists():
        try:
            candidates.extend(re.split(r'[\r\n,;\s]+', p.read_text(encoding='utf-8')))
        except Exception:
            pass
    clean = []
    for k in candidates:
        k = k.strip()
        if len(k) >= 20 and not re.match(r'^(YOUR|PASTE|<|\$)', k, re.I) and not re.search(r'_KEY|KEY_HERE|EXAMPLE', k, re.I):
            if k not in clean:
                clean.append(k)
    return clean


def key():
    import os
    k = os.environ.get('GEMINI_API_KEY', '').strip()
    p = Path.home() / '.flow-mcp' / 'gemini-key'
    if not k and p.exists():
        k = p.read_text().strip()
    ks = get_keys()
    if not ks:
        die('No Google AI Studio key. See reference/voice.md: the user saves it in Flow Studio (Voice tab), never in the chat.')
    return ks[0]


def tts(film, voice, style=None, text=None, out=None, model=None):
    """Direct call to Google AI Studio, supporting multi-key rotation and multiple allowed model fallbacks."""
    keys = get_keys()
    if not keys:
        die('No Google AI Studio key. See reference/voice.md: the user saves it in Flow Studio (Voice tab), never in the chat.')
    
    cfg = load(film / 'film.json', default={}) if isinstance(film, Path) and (film / 'film.json').exists() else {}
    target_model = model or cfg.get('tts_model') or os.environ.get('GEMINI_TTS_MODEL') or TTS_MODEL
    candidate_models = [target_model] + [m for m in ALLOWED_TTS_MODELS if m != target_model]

    src = text or (film / 'script.md').read_text(encoding='utf-8')
    paras = [p.strip() for p in src.split('\n\n') if p.strip() and not p.strip().startswith('#')]
    chunks, cur = [], ''
    for p in paras:                                                     # about 3 minutes per piece
        if len((cur + ' ' + p).split()) > 420 and cur:
            chunks.append(cur)
            cur = p
        else:
            cur = (cur + '\n\n' + p).strip()
    if cur:
        chunks.append(cur)
    vdir = film / 'voice'
    vdir.mkdir(exist_ok=True)
    files = []
    active_idx = 0
    active_model_idx = 0
    for i, c in enumerate(chunks):
        body = {'contents': [{'parts': [{'text': (f'Say {style}: {c}' if style else c)}]}],
                'generationConfig': {'responseModalities': ['AUDIO'], 'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': voice}}}}}
        
        r = None
        last_error = None
        for m_attempt in range(len(candidate_models)):
            cur_model = candidate_models[(active_model_idx + m_attempt) % len(candidate_models)]
            model_failed = False

            for attempt in range(len(keys)):
                cur_idx = (active_idx + attempt) % len(keys)
                cur_key = keys[cur_idx]
                req = urllib.request.Request(f'https://generativelanguage.googleapis.com/v1beta/models/{cur_model}:generateContent',
                                             data=json.dumps(body).encode(), headers={'content-type': 'application/json', 'x-goog-api-key': cur_key})
                try:
                    r = json.load(urllib.request.urlopen(req, timeout=300))
                    active_idx = cur_idx
                    active_model_idx = (active_model_idx + m_attempt) % len(candidate_models)
                    break
                except urllib.error.HTTPError as e:
                    last_error = e
                    if e.code in (429, 403) and len(keys) > 1:
                        print(f'AI Studio key ending in ...{cur_key[-4:]} hit quota limit ({e.code}) on model {cur_model}. Trying next key...', file=sys.stderr)
                        continue
                    if e.code in (404, 400) and len(candidate_models) > 1:
                        print(f'Model {cur_model} returned {e.code}. Falling back to alternate model in pool...', file=sys.stderr)
                        model_failed = True
                        break
                    if e.code == 429:
                        if len(candidate_models) > 1:
                            print(f'Quota reached on {cur_model}. Falling back to next allowed model...', file=sys.stderr)
                            model_failed = True
                            break
                        die('AI Studio says the free limit for voice takes is used up for now across all keys. It resets daily. Tell the user, and offer: try again later, a free local voice (flow_narrate with engine "kokoro"), or a recording.')
                    die(f'AI Studio refused this take ({e.code}): {e.read().decode()[:300]}')
                except Exception as e:
                    last_error = e
                    if len(keys) > 1:
                        print(f'AI Studio key ending in ...{cur_key[-4:]} error: {e}. Switching to next key...', file=sys.stderr)
                        continue
                    die(f'Error calling Google AI Studio: {e}')

            if r:
                break
            if not model_failed:
                break

        if not r:
            die(f'All {len(keys)} Google AI Studio keys and allowed models failed. Last error: {last_error}')

        part = next(p for p in r['candidates'][0]['content']['parts'] if 'inlineData' in p)
        rate = int((re.search(r'rate=(\d+)', part['inlineData'].get('mimeType', '')) or [0, 24000])[1])
        f = vdir / f'take-{i + 1:02d}.wav'
        with wave.open(str(f), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
            w.writeframes(base64.b64decode(part['inlineData']['data']))
        files.append(f)
        print(f'  piece {i + 1}/{len(chunks)} ({cur_model}): {probe_duration(f):.1f} s')
    return files


def lock(film, files, tempo=None, target=None, language=None, words_file=None, whisper_model=None):
    """Join the takes into voice/narration.wav, apply any speed change, and time every word."""
    vdir = film / 'voice'
    vdir.mkdir(exist_ok=True)
    tmp = vdir / '_joined.wav'
    if len(files) == 1:
        ffmpeg('-i', files[0], '-ar', SR, '-ac', 1, tmp)
    else:
        args = []
        for f in files:
            args += ['-i', f]
        chain = ''.join(f'[{i}:a]aresample={SR},aformat=channel_layouts=mono[a{i}];' for i in range(len(files)))
        joined = ''.join(f'[a{i}]' for i in range(len(files)))
        ffmpeg(*args, '-filter_complex', chain + f'{joined}concat=n={len(files)}:v=0:a=1[o]', '-map', '[o]', tmp)
    d0 = probe_duration(tmp)
    if target:
        tempo = d0 / float(target)
    out = vdir / 'narration.wav'
    if tempo and abs(tempo - 1) > 0.005:
        chain, t = [], float(tempo)
        while t > 2:
            chain.append('atempo=2'); t /= 2
        while t < 0.5:
            chain.append('atempo=0.5'); t /= 0.5
        chain.append(f'atempo={t:.4f}')
        ffmpeg('-i', tmp, '-filter:a', ','.join(chain), '-ar', SR, out)
        print(f'speed x{tempo:.3f}: {d0:.1f} s -> {probe_duration(out):.1f} s')
    else:
        ffmpeg('-i', tmp, '-c:a', 'pcm_s16le', out)
    tmp.unlink()
    print(f'narration {probe_duration(out):.2f} s -> {out}')
    clock(film, language, words_file, whisper_model=whisper_model)
    pace(film)


def transcribe(path, language, whisper_model=None):
    import os
    from faster_whisper import WhisperModel
    m = whisper_model or os.environ.get('WHISPER_MODEL', 'base')
    print(f'timing every word (using speech model: {m})...', flush=True)
    model = WhisperModel(m, device='cpu', compute_type='int8', download_root=str(TOOLS / 'models'))
    r = run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '1', '-ar', '16000', '-'], capture_output=True)
    audio = np.frombuffer(r.stdout, np.float32).copy()                  # decoded here so nothing depends on the av package
    segs, _ = model.transcribe(audio, word_timestamps=True, language=language, vad_filter=False)
    return [{'w': w.word.strip(), 's': round(w.start, 3), 'e': round(w.end, 3)} for s in segs for w in s.words if w.word.strip()]


def clock(film, language=None, words_file=None, whisper_model=None):
    vdir = film / 'voice'
    if words_file:                                                      # e.g. saved from the Flow transcribe tool
        raw = load(words_file)
        raw = raw.get('words', raw) if isinstance(raw, dict) else raw
        W = [{'w': str(x.get('w', x.get('word', x.get('text')))).strip(), 's': float(x.get('s', x.get('start'))), 'e': float(x.get('e', x.get('end')))} for x in raw]
    else:
        wmodel = whisper_model or load(film / 'film.json', default={}).get('whisper_model')
        W = transcribe(vdir / 'narration.wav', language or load(film / 'film.json').get('language'), whisper_model=wmodel)
    # the script knows the spelling: fix mishearings so scene.js can use the real words
    sw = script_words(film)
    if sw:
        a, b = [norm(x['w']) for x in W], [norm(x) for x in sw]
        fixed = 0
        for tag, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
            if tag == 'replace' and i2 - i1 == j2 - j1:
                for k in range(i2 - i1):
                    W[i1 + k]['w'] = sw[j1 + k]
                    fixed += 1
        ratio = SequenceMatcher(None, a, b, autojunk=False).ratio()
        print(f'clock: {len(W)} words, {ratio * 100:.0f}% match the script' + (f', {fixed} mishearings corrected' if fixed else ''))
        if ratio < 0.9:
            print('NOTE: the take differs from script.md. Read voice/words.json: scene.js must use the words really spoken.')
    save(vdir / 'words.json', W)


def _phrase(W, phrase, n=None):
    tk = [norm(t) for t in phrase.split() if norm(t)]
    a = [norm(x['w']) for x in W]
    hits = [i for i in range(len(a) - len(tk) + 1) if a[i:i + len(tk)] == tk]
    if not hits:
        die(f'pacing: "{phrase}" is not in the narration')
    if n:
        return hits[n - 1] + len(tk) - 1
    if len(hits) > 1:
        die(f'pacing: "{phrase}" is said {len(hits)} times. Add "n": k, or use a longer phrase.')
    return hits[0] + len(tk) - 1


XF = int(0.008 * SR)                                                    # 8 ms crossfade at every join
MAX_PAUSE = {'end': 1.6, 'comma': 0.45}


def _levels(x, hop=int(0.002 * SR), win=int(0.006 * SR)):
    """Loudness over time, every 2 ms."""
    if len(x) < win:
        return np.array([0.0])
    c = np.cumsum(np.concatenate([[0.0], x.astype(np.float64) ** 2]))
    idx = np.arange(0, len(x) - win, hop)
    return np.sqrt(np.maximum(c[idx + win] - c[idx], 0) / win)


def _find_silence(x, t_end, t_next, quiet):
    """Where the voice is really silent around this word boundary, judged from the audio, not from the estimated word times.
    Returns the sample in the middle of the longest silence, or None if the words run together."""
    a = max(0, int((t_end - 0.12) * SR))
    b = min(len(x), int((t_next + 0.12) * SR))
    lv = _levels(x[a:b]) < quiet
    best, run, start, best_start = 0, 0, 0, 0
    for i, q in enumerate(lv):
        if q:
            if not run:
                start = i
            run += 1
            if run > best:
                best, best_start = run, start
        else:
            run = 0
    if best * 0.002 < 0.03:                                             # under 30 ms is not a gap
        return None
    return a + int((best_start + best / 2) * 0.002 * SR)


def _room_tone(x, n):
    """Silence that sounds like the take: its own quietest stretch, repeated. Digital silence between words sounds like a dropout."""
    win = int(0.15 * SR)
    if len(x) <= win:
        return np.zeros(n, np.float32)
    c = np.cumsum(np.concatenate([[0.0], x.astype(np.float64) ** 2]))
    k = int(np.argmin(c[win:] - c[:-win]))
    piece = x[k:k + win]
    loop = np.concatenate([piece, piece[::-1]])                         # mirrored, so the repeats have no clicks
    return np.tile(loop, n // len(loop) + 1)[:n].astype(np.float32)


def _join(a, b):
    """Crossfade b onto the end of a. The result is XF samples shorter than the two together."""
    n = min(XF, len(a), len(b))
    if n == 0:
        return np.concatenate([a, b])
    fade = np.linspace(0, 1, n, dtype=np.float32)
    return np.concatenate([a[:-n], a[-n:] * (1 - fade) + b[:n] * fade, b[n:]])


def pace(film):
    """Add breathing room without touching a word: room tone at the start, at the end, and in real silences between sentences.
    Pauses only go where the audio is silent and the sentence allows one. Everything else is refused and reported."""
    cfg = load(film / 'film.json').get('pacing', {})
    lead, tail = float(cfg.get('lead', 0.8)), float(cfg.get('tail', 3.0))
    W = load(film / 'voice/words.json')
    raw = ffmpeg_decode(film / 'voice/narration.wav')
    speech = np.sqrt(np.mean(raw[np.abs(raw) > 0.01] ** 2)) if (np.abs(raw) > 0.01).any() else 1.0
    quiet = speech * 10 ** (-38 / 20)
    cuts, problems = [], []
    for p in cfg.get('pauses', []):
        i = _phrase(W, p['after'], p.get('n'))
        if i + 1 >= len(W):
            continue
        word, sec = W[i]['w'].rstrip(), float(p['sec'])
        kind = 'end' if word[-1:] in '.!?' else 'comma' if word[-1:] in ',;:' else None
        if not kind:
            problems.append(f'"{p["after"]}": no pause added, it is the middle of a sentence and would sound chopped.')
            continue
        if sec > MAX_PAUSE[kind]:
            problems.append(f'"{p["after"]}": pause cut to {MAX_PAUSE[kind]} s, the most this break can take and still sound natural (asked for {sec} s).')
            sec = MAX_PAUSE[kind]
        k = _find_silence(raw, W[i]['e'], W[i + 1]['s'], quiet)
        if k is None:
            problems.append(f'"{p["after"]}": no pause added, the voice runs straight into the next word here, so a pause would cut into speech.')
            continue
        cuts.append((k, sec, i))
    cuts.sort()
    tone = lambda seconds, extra=0: _room_tone(raw, int(seconds * SR) + extra)
    y, pos = tone(lead, XF), 0
    for k, sec, _ in cuts:
        y = _join(y, raw[pos:k])
        y = _join(y, tone(sec, 2 * XF))
        pos = k
    y = _join(y, raw[pos:])
    # word clock: each word moves by the lead plus the pauses before it
    P = []
    for n, w in enumerate(W):
        shift = lead + sum(sec for _, sec, i in cuts if i < n)
        P.append({'w': w['w'], 's': round(w['s'] + shift, 3), 'e': round(w['e'] + shift, 3)})
    dur = round(max(P[-1]['e'] + tail, len(y) / SR), 3)
    y = _join(y, tone(max(0.1, dur - len(y) / SR), XF))[:int(dur * SR)]
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-i', '-', '-c:a', 'pcm_s24le', film / 'voice/paced.wav'], input=y.astype(np.float32).tobytes())
    (film / 'build').mkdir(exist_ok=True)
    (film / 'build/clocks.js').write_text('window.WORDS=' + json.dumps(P, ensure_ascii=False) + ';window.DUR=%.3f;\n' % dur, encoding='utf-8')
    save(film / 'voice/pacing-problems.json', problems)
    print(f'timeline {dur:.2f} s (voice ends at {P[-1]["e"]:.2f} s, {len(cuts)} pauses added)')
    for m in problems:
        print('NOTE ' + m)


def ffmpeg_decode(path, ch=1):
    r = run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', str(ch), '-ar', str(SR), '-'], capture_output=True)
    return np.frombuffer(r.stdout, np.float32).copy()
