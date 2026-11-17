# The voice

The voice is locked before images are generated, because every drawing is timed to it. If the words change later, the timing changes and the animation has to be adjusted, which wastes the user's agent usage. What is really frozen is the words: speed (`--tempo`) and pauses (`pacing`) can still change in seconds, and every cue in `scene.js` moves with them, because cues are written as words, not times.

## Google AI Studio key (once)

The free narration voices need a free key. Walk the user through it. They must never paste the key into this chat, because it would stay in the conversation history.

1. Go to [AI Studio](https://aistudio.google.com) and click the key icon at the lower left (Get API key).
2. Click **Create API key**, name it, select **New project**, then **Create key**, and copy it.
3. Open Flow Studio in the browser (it runs locally; `flow_status` gives its address, usually http://127.0.0.1:8787). Go to the **Voice** tab, paste the key in the Google AI Studio key field, and save.

Check it with `flow_voices`, which reports whether a key is set up. `wb setup` also reports it.

No key and no wish to get one? Flow Studio also has a free local voice (`flow_narrate` with `engine: "kokoro"`, if your version lists it) and system voices (`engine: "mac"`), or use a recording.

## Recording

```
flow_narrate  project: "<slug>", engine: "gemini", voice: "<their pick>", style: "<delivery note>", text: "<the whole script>"
```

The style note steers delivery: "warm, confident, conversational explainer, medium pace, short pauses between sentences".

**Check the reply before using the file.** Flow may fall back to another engine and voice when AI Studio refuses a take, for example because of a short-lived limit. It still returns a file, in the wrong voice. If the reply's `engine` or `voice` differs from what you asked for, or it contains `fell_back_from`: retry once. If it falls back again, tell the user instead of using it. You cannot catch this by ear.

**The free tier has a daily limit on takes**, and it is not large, so do not spend it on tests. Regenerate only when the user asks. When it runs out, Flow falls back as described above and `wb tts` says so. Tell the user: it resets daily, or they can use a free local voice or a recording.

**Use the `output` path from the reply.** Each take in a project gets a new number, so never assume a file name. Then:

```bash
wb voice <film> <output path>
```

This converts it, times every word (the first run downloads a speech model of about 150 MB), and corrects any mishearing against `script.md`. Tell the user where the file is and ask them to listen. You cannot hear it.

**No Flow tools in this agent?** `wb tts <film> --voice Charon --style "warm, conversational"` calls AI Studio directly using the saved key.

**Their own recording, or ElevenLabs and the like?** Just `wb voice <film> /path/to/file`. If the words differ from `script.md`, it warns you. Then use the words really spoken in `scene.js` (`wb words <film>` prints them).

## Pacing notes

Users will say things like "pacing is too slow, keep everything constant but have it speak quicker, target 30 seconds".

1. First regenerate with a style note ("speak at a brisk pace"). It sounds the most natural.
2. To hit an exact length without regenerating: `wb voice <film> <file> --target 30` (or `--tempo 1.1`). This changes the speed and keeps the pitch. Keep it small: see "Speed changes" below.

## Long scripts

Very long takes can fail. In testing, narration worked up to about three minutes. Flow Studio may already split long text itself. If a long take errors, or for a video over three minutes, split the script at paragraph breaks into pieces of at most 400 words, record each one, then join them:

```bash
wb voice <film> part1.m4a part2.m4a part3.m4a
```

`wb tts` splits by itself.

## Pauses: giving the pen time

`pacing` in `film.json` adds silence without touching a word:

```json
"pacing": { "lead": 1.0, "tail": 4.0, "pauses": [ {"after": "broke down", "sec": 0.8}, {"after": "what to do", "n": 1, "sec": 0.5} ] }
```

- `lead`: silence before the first word, so the first drawing can start early
- `tail`: silence after the last word. The last frame rests for this minus whatever the pen is still drawing, so if the payoff is written on the final words, a `tail` of about 4 gives a 2.5 s rest. `wb check` tells you the real figure
- `after`: the words the pause follows. If the phrase is said more than once, `n` says which time

After editing, run `wb pace <film>`.

**Pauses are the easiest way to ruin a voice, so the tool is strict.** Users notice choppiness at once. `wb pace` finds the real silence in the audio, fills the pause with the take's own room tone, and crossfades the joins. It refuses anything that would sound chopped, and says so in its output and in `wb check`:
- After a sentence end: up to 1.6 s. Above about 1 s, use it rarely, because several long pauses make the voice feel slow.
- After a comma: up to 0.45 s.
- Anywhere else: refused. A pause in the middle of a clause always sounds like a mistake.
- Words that run together with no silence: refused, because any pause there would cut into speech.

When the pen needs more time than the sentence breaks can give, do not fight the voice. Let the drawing run on over the next few words, start it earlier during the previous pause, or simplify the drawing. A drawing does not have to finish before the next word starts.

**Speed changes:** prefer regenerating with a style note. `--tempo` is fine for small changes, about 0.92 to 1.12. Beyond that, the voice starts to sound processed.

For a recording that must stay in sync with camera footage, leave `pauses` empty.

**You cannot hear any of this.** Always ask the user to listen, and if they say it sounds choppy, believe them: compare `voice/paced.wav` with the original take.
