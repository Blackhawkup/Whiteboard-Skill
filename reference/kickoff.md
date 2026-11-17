# The kickoff message

Send this once, right after the first request, in a single message. Leave out anything already answered, and use the user's words where you can. Then wait. They answer everything in one reply, and you do not interrupt them with questions after this.

---

Before I write anything, a few quick questions. Answer them all in one message, or say "you decide" for any of them.

1. **Who is it for, and what should they understand or do after watching?** A video for beginners looks and sounds different from one for a technical audience.
2. **How long?** Any length works, but I suggest starting with 30 seconds to 2 minutes.
3. **What format?** 16:9 for regular YouTube, or 9:16 for Shorts, Reels and TikTok.
4. **Where will it be used?** A standalone video, or a short section inside a longer one? This decides whether it needs its own intro and ending, or just explains one idea.
5. **What should it look like?** This goes into every drawing, so we decide it now.
   - **Style.** My suggestion: black marker with an even line, a warm off-white board, and a few accent colours. Coral for the problem, violet for the solution, cyan for important or supporting points. Tell me your brand colours if you have some, or describe another look.
   - **Font** for the words the hand writes. I suggest Geist. Any Google font works, or give me a font file.
   - **Anything real to show?** A logo, a screenshot, a product or a name that should appear on the board.
6. **Which voice?** Google AI Studio's voices are free. Try Charon (informative), Sulafat (warm), Puck (upbeat), Kore (firm), Achird (friendly), Sadaltager (knowledgeable), Aoede (breezy) or Gacrux (mature). To hear them first, open [AI Studio](https://aistudio.google.com), click the model name at the top right, filter by Audio, choose a TTS model, start a new dialogue, and pick a voice on the right. You can also use your own recording or a voice from another tool such as ElevenLabs.
7. **How should it end?** A call to action (tell me which), or just the payoff?

---

If the voice list can be checked, call `flow_voices` first and only offer names it returns.

## Where the answers go

| Answer | Goes to |
|---|---|
| Audience and goal | The top of `storyboard.md`, and they steer the script |
| Length | The word budget in `reference/writing.md` |
| Format | `wb new <slug> --format 16:9` or `9:16` (`format` in `film.json`) |
| Where it plays | A section needs no intro or ending, and usually `"music": "none"` because the edit will have its own |
| Colours | `palette` in `film.json`. Keep the role names `problem`, `solution`, `highlight`, and `ink` for the marker. Add any role you need |
| Board | `board` in `film.json`, a hex colour. A dark board with light ink makes a chalkboard look: `"board": "#20262B"`, `"ink": "#F4F1EA"` |
| Style words | `style_words` in `film.json`, for example `"in thin blue ballpoint pen"`. They go in every image prompt |
| A fully coloured or shaded look | `"art_mode": "painted"` in `film.json` (see `reference/prompts.md`) |
| Font | `font` in `film.json`: `{"family": "Geist"}`, any Google Fonts family name, or `{"family": "Mine", "file": "/path/to/font.otf"}`. Bundled: Geist, Inter, Archivo Black, Instrument Serif, Caveat |
| Real things to show | Ask for the files if they did not attach them. They become drawings or images in `drawings.json` |
| Voice | `voice` in `film.json` |
| Ending | The last lines of the script and the final wide shot |

Music defaults to a soft synthesized bed. If the user says no music, set `"music": "none"`. Their own track: `"music": "/path/to/track.mp3"`.
