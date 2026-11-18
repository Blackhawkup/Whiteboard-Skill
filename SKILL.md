---
name: whiteboard-explainer
description: Make animated whiteboard explainer videos where a real-looking hand draws every picture and writes every word, timed word by word to the narration, and rendered to MP4 with no video editor. Use this whenever the user wants a whiteboard animation, whiteboard explainer, doodle or sketch video, hand-drawn explainer, RSA-style animation, or "a hand drawing it while someone talks", in any format (YouTube 16:9, Shorts or Reels 9:16), even if they only give a topic. It runs the whole job, from kickoff questions, script and storyboard to voice, images in Google Flow, animation and final video, and installs anything that is missing.
---

# Whiteboard Explainer

The user gives a topic. You write the script, plan the board, record the voice, generate the drawings in Google Flow, and build
a video in which a hand draws everything on the exact word it is spoken. Nothing on screen is AI video: the pictures are stills,
and code draws them stroke by stroke, so drawings stay consistent and the timing is exact.

This skill works in any coding agent (Claude Code, Codex, Antigravity, OpenCode and others). Below, "Flow tools" are the tools of
the Flow Studio MCP server (`flow_status`, `flow_agent_images` and so on; your agent may show them with a prefix).

## Ground rules

- **Stop at every ✋** and wait for the user. Between them, work without interrupting. All questions go in the one kickoff message.
- **Order matters: script, storyboard, voice, then images.** Each one is the input of the next, and changing an earlier one wastes
  the later work. Above all, the animation is timed to the voice, so the voice is locked before any image is generated.
- **Look before you show.** Open and look at every image you generate and every sheet you render, and fix what you see before the
  user does. If your agent cannot view images, say so and ask the user to check that sheet.
- **You cannot hear.** Say so when you deliver sound, and ask the user to listen.
- **Stills in Flow cost 0 credits, and this skill never generates Flow video.** If a Flow call would spend credits, stop and ask.
- **Never ask for an API key in the chat.** Keys go in Flow Studio (see `reference/voice.md`).
- **Check facts.** Any number, quote or claim in a script gets checked before the script goes to the user.

`wb` below means `bash <this skill's folder>/scripts/wb` (on Windows `<this skill's folder>\scripts\wb.cmd`). `wb help` lists every
command. Films live in `~/WhiteboardFilms/films/<slug>` (`$WHITEBOARD_HOME` moves it).

## Step 0: set up (first run only)

1. Run `wb setup`. If anything is missing, run `wb setup --install`: it installs every missing piece (ffmpeg, Node, Python packages,
   Chrome, Flow Studio) and connects Flow to every coding agent on this computer. Tell the user it is doing this, then do it. System
   installs may need their password, so if one fails, give them the exact command it prints.
2. If `wb setup` lists something the user has to do (sign in to Google for Flow, restart the agent), ask them to do it, then continue.
3. Call `flow_status` once, with `detailed: false` if your agent lets you (the output is long). It is the only real test of the Google sign-in. If the Flow tools do not exist in this session even after a
   restart, use manual mode (`reference/setup.md`): you write the prompts and the user brings the images.

Details and per-agent notes: `reference/setup.md`. To prove the install works, run `wb example`.

## Step 1: kickoff ✋

When the user asks for a video, even in one line, send the one kickoff message from `reference/kickoff.md`, leaving out anything they
already answered. They answer everything once. "You decide" means use the recommended defaults. Then
`wb new <slug> --format <16:9|9:16>` and record the answers in `film.json` (`reference/kickoff.md` shows where each one goes).

## Step 2: script ✋

Write the narration first, into `script.md`, to be spoken: rules and word budgets in `reference/writing.md`. Show it and wait.
The user may revise it as many times as they like. Nothing else starts until they approve it.

## Step 3: storyboard ✋

Plan what appears on the board during each line, in `storyboard.md`: rules, drawing budget and template in `reference/storyboard.md`.
This is what makes the video good. A drawing must help explain the line, not just decorate it. Show the table and the list of drawings.
If the user says a scene is too complicated, simplify it. Wait for approval; it fixes exactly what will be created.

## Step 4: voice, then lock it ✋

Record the voice the user picked at kickoff (`reference/voice.md`): `flow_narrate` with `engine: "gemini"`, or direct TTS with `wb tts <film> --voice <voice> [--model <model>]` (which supports multiple allowed Gemini models and auto-rotating keys), or their own recording, or any other tool's file. **Flow can silently fall back to a different voice, so compare the voice in its reply with the one requested, and use the `output` path it returns.** Then `wb voice <film> <audio file> [--whisper-model <model>]`, which times every word. Tell them where the file is, ask them to listen, and take notes such as "pacing is too slow, target 30 seconds". Regenerate until they approve. From here on the words are locked, because changing them means re-timing. Tell the user that small speed changes and pauses may still be made once the drawings show how much time the pen needs.

## Step 5: images

1. Write `drawings.json` from the approved storyboard (you decide what is needed, the user has no work here), then `wb prompts <film>`.
2. Call `flow_new_project` with the film's title so its images stay together.
3. Generate in one or two batches with `flow_agent_images`, and collect with `flow_wait`. Exact calls, references for recurring
   characters, the hand and what to do when a batch fails: `reference/prompts.md`.
4. If `~/WhiteboardFilms/hand/hand.png` does not exist yet, generate the hand too, then `wb hand <file>` and look at `hand_check.jpg`.
   It is reused for every later film. (If you cannot get one, a built-in hand is used automatically.)
5. `wb intake <film> name=file ...`, then look at `out/intake.jpg` and show it to the user as a preview. Every picture must match its
   name (batch order is not guaranteed) and the style, with no writing in it. Regenerate any that fail: it is free.

## Step 6: build

1. `wb art <film>` traces each drawing into pen strokes, and prints its size on the board and its pen time: plan the layout from these. Write `labels.json` with any words the hand writes, then `wb labels <film>`.
2. Write `scene.js`: where everything sits, when the pen draws it (each on its own word), and how the camera moves. API, layout rules and
   patterns: `reference/scene-api.md`. Copy from a complete film: `examples/chatbot-vs-agent/` (16:9) or `examples/one-key/` (9:16).
3. Run `wb check <film>` until it has no errors. It catches overlapping pen jobs, a pen too fast to read, words too small for a phone,
   things cut by the frame edge, text colliding with a drawing, and more. It prints the fix. A pen that is too fast is fixed by giving it
   time, with a simpler drawing, a drawing that runs on over the next words, or a pause at a sentence end in `film.json` (`pacing`, then `wb pace`), never by accepting it. Never chop the voice to make room: `reference/voice.md` explains the limits.

## Step 7: review it yourself, then with the user ✋

1. `wb sheet <film>`, and look at every sheet in `out/sheets`. Checklist in `reference/review.md`. Fix, re-check.
2. `wb preview <film>` makes a quick half-size MP4 with sound, in about a minute. Give it to the user and ask them to watch and listen.
3. Take their notes, screenshots welcome. `reference/review.md` maps typical notes ("the second scene moves too fast", "too crowded",
   "the label comes too early", "the marker does not line up") to the exact fix. Generate any new image the note needs through Flow.
   Repeat until they approve.

## Step 8: deliver

`wb make <film>` runs the checks, mixes the sound at -14 LUFS and renders 1080p at 60 fps to `out/<slug>.mp4`. Look at the first frame
(it must be blank board) and the last frame (the whole payoff, nothing cut). Give the user the path, the length and the loudness, and
remind them you cannot hear the mix.

## Reference

| File | When to read it |
|---|---|
| `reference/setup.md` | Installing, each agent's notes, manual mode without Flow tools |
| `reference/kickoff.md` | The kickoff message and where the answers go |
| `reference/writing.md` | Writing narration for the ear, word budgets |
| `reference/storyboard.md` | Planning the board, drawing budget, template |
| `reference/voice.md` | AI Studio key, picking and recording a voice, pacing, long scripts |
| `reference/prompts.md` | Flow calls, the image recipe, the hand, consistency, fixing bad images |
| `reference/scene-api.md` | Writing `scene.js`: every call, sizes, camera, 9:16, long films |
| `reference/review.md` | Self-review checklist, turning user notes into fixes, failures seen so far |
| `examples/chatbot-vs-agent/` | A complete 37-second 16:9 film to copy from |
| `examples/one-key/` | A complete 35-second 9:16 film to copy from |
