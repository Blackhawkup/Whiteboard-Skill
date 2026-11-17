# Reviewing

Do this yourself before the user sees anything. Run `wb check <film>`, then `wb sheet <film>`, and look at every sheet in `out/sheets`. The check catches what can be measured. Your eyes catch the rest.

## Look for

- **Frame 0** is blank board. **The last frame** shows the whole payoff, fully drawn, the hand gone, nothing cut, and it holds at least 2.5 seconds.
- **Things cut by the edge.** A neighbour passing by during a camera move is fine. Something sitting half cut while the camera holds looks like a mistake. `wb check` warns about it, and also about words in a vertical video's button zones.
- **Lines crossing that should not.** An arrow crossing another arrow, or a ring cutting through a drawing's corners. The check only covers text, so this one is on your eyes.
- **Everything big enough for a phone.** If a shot looks sparse, with tiny drawings in a lot of empty board, push the camera in. This is the most common first-draft problem.
- **Each drawing on its word.** Compare the times on the sheet with `wb words <film>`.
- **Things in the right order.** A label after its illustration. An outline before its colour. A phone before its speech bubble (`"start"` in `drawings.json`).
- **Drawings that look right when they are tracing:** no stray marks, no missing parts. If one is wrong, look at the source picture first.
- **The marker tip on the line.** Check a full frame (`wb stills <film> --times 9.2`). If it is off, redo the hand's tip (`reference/prompts.md`).
- **The arm.** The sleeve must always run out of frame, with no pale ghost around the hand.
- **No marks that look like letters by accident.** A malformed drop once read as a letter "d" on the board. Zoom in on small marks.
- **Nothing covering the point for long.** The hand covers what it draws for a moment, which is natural. It should not sit over the key thing when it is done.

## Turning the user's notes into fixes

| The user says | What to change |
|---|---|
| "This scene moves too fast" or "slow down the drawing" | Give those drawings a longer window. If the voice leaves no room, add pauses in `film.json` `pacing` and `wb pace` |
| "Too slow" or "it drags" | Tighter windows, shorter pauses, or a faster voice (`--target`) |
| "Labels should come after the illustrations" | Reorder the jobs in `scene.js` |
| "A label appears too early" | Start it on its word: `S.draw('label', T('its word'))` |
| "It draws in the wrong order" | Reorder jobs. Inside one drawing, `start` in `drawings.json`, or split it into two images |
| "Too crowded" | Remove a drawing, spread things out, move the camera between them, or simplify the image's prompt and regenerate |
| "Too small" | Push the camera in, or raise `w` and rerun `wb art` |
| "The hand or marker does not line up" | `wb hand <image> --tip x,y` |
| "This drawing is wrong" | Regenerate through Flow with a better prompt, then `wb intake`, `wb art <film> <name>` |
| "Change this word" on the board | Edit `labels.json`, `wb labels` |
| "Change this word" in the voice | Warn that it means re-timing. Re-record, `wb voice`, then check every cue in `scene.js` still lands |
| "Different colours" | Edit `palette` or `colour`, then `wb art` and `wb labels`. No new images needed |
| "The voice sounds choppy" or "the pauses are weird" | Believe it, you cannot hear it. Remove or shorten pauses in `pacing`, `wb pace`, and let the drawings run on over the words instead |
| "No music", "louder music" | `"music": "none"`, or `music_db` in `film.json` (default -24), or `marker_db` (default -31). Then re-render |

Fix the whole class of a problem, not only the place they named. Then `wb check`, `wb sheet`, look, and send a new `wb preview`.

## Failures seen so far

| What went wrong | Prevention |
|---|---|
| Everything too small in the frame on the first draft | Frame at 1.1 to 1.35. The check warns about small things |
| The hand whipped around too fast to read | Pen speed check. Add voice pauses rather than accepting it |
| The camera left while the pen was finishing | Start the move after the last mark is down. The check catches the pen going off-frame |
| The pen started writing before the camera arrived on a pull-back | Finish the pull-back before the first payoff word |
| A cue landed on the wrong "you" or "it" | `T()` refuses ambiguous phrases. Use longer ones |
| The sleeve ended inside the frame | The hand tool extends it, and the hand keeps its size on a pull-back |
| Soft photo shadow left a ghost by the hand | The hand tool keeps only skin and dark pixels. Look at `hand_check.jpg` |
| A font silently fell back to a default | `wb labels` stops if the font did not load |
| Colour shades differed between images | Colours are applied when tracing, so Flow's shade does not matter |
| The voice sounded choppy: pauses landed inside words and between clauses | `wb pace` now cuts only in real silence, at sentence breaks, with room tone and crossfades, and reports what it refused |
| The first voice take came back in another voice, silently | Compare the voice in `flow_narrate`'s reply with the request. Use its `output` path |
| Drawings too detailed, so the film ran long | Count the parts in the prompt. `wb art` flags anything over budget |
| A finished row sat half cut during a long hold | `wb check` warns about it now |
