# Writing scene.js

`scene.js` is the animation. It has three parts: what is on the board and where, when the pen draws it, and how the camera moves. A complete film: `examples/chatbot-vs-agent/scene.js`.

The board is much bigger than the frame. **Board units are screen pixels at camera scale 1.** A 16:9 frame is 1920 x 1080, 9:16 is 1080 x 1920. Nothing appears on the board until the pen draws it.

## The word clock

```js
T('broke down')            // when these words start
T.end('broke down')        // when they end
T('what to do', {n: 2})    // the second time it is said
T('you', {after: T('helpful')})   // the first time after that moment
```

A phrase said more than once without `n` or `after` is an error, on purpose: guessing wrong puts a drawing on the wrong word. Longer phrases are the cleanest fix. `wb words <film>` prints the clock. `DUR` is the film's length.

## Placing things

```js
S.art('car', {cx: 600, cy: 650});                 // a traced drawing, by its centre
S.art('you', {from: 'person_stressed', cx: 1140, cy: 600});   // id differs from the file; lets you use a drawing twice
S.art('chat', {from: 'phone_bubble', x: 1400, y: 205});       // by its top-left corner
S.text('tells', {cx: 2800, cy: 600});             // a traced label from labels.json
```

Width defaults to the `w` it was traced at, which keeps every line the same weight. To change a size, change `w` in `drawings.json` and rerun `wb art`.

Labels live in `labels.json`, and `wb labels` traces them. The pen writes them glyph by glyph and they always end as the exact font:

```json
[ {"id": "tells", "text": "TELLS.", "size": 250, "weight": 900, "colour": "problem"} ]
```

Options: `family` (a different font), `tracking`, `style: "italic"`. Each word or short phrase is one label. `colour` is a palette role or hex.

Marks are drawn directly, with a little hand wobble:

```js
S.arrow('a1', [100, 100], [400, 300], {bend: 0.1, head: 32, color: 'problem', w: 10});
S.line('u1', [100, 400], [500, 400], {bend: -0.03, color: 'solution', w: 13});  // underline, connector
S.tick('t1', cx, cy, 54, {color: 'solution'});
S.cross('x1', cx, cy, 120, {color: 'problem'});     // two strokes
S.ring('r1', cx, cy, rx, ry, {color: 'problem'});   // a loop around something
S.drop('d1', cx, cy, 26, {color: 'highlight'});     // a teardrop
S.marks('m1', [[[x, y], [x, y]], [[x, y], [x, y]]], {color: 'ink', w: 9});      // your own strokes
```

An arrow that runs from one area to another while the camera travels with it takes `travel: true`, so the check knows it will not be whole in frame.

`S.overlapOK('a', 'b')` allows ink to touch on purpose, for example a ring around a word.

## The pen

There is **one pen**, so jobs must never overlap, which is exactly what makes it look real.

```js
S.draw('car', 0.6, T('so you') - 0.2);    // fit the outline and colour inside this window
S.draw('title', T('now'));                 // at the natural pen speed
S.then('label');                           // right after the last job
S.then('sweat', {gap: 0.1, until: T.end('all of it') + 0.7});
const j = S.draw('x', 3);  j.t1;           // returns {t0, t1}
```

- Start each drawing **on or just before its word**. Elements arrive on their own word, one at a time. That is the whole effect.
- A label comes after the drawing it names.
- Colour is scribbled in after the outline, automatically. It takes up to about a quarter of the window.
- The first job can start around 0.6 s. Frame 0 is always blank.
- The hand enters, travels between jobs and leaves by itself. Gaps over about 1.1 s send it out of frame so the viewer sees the drawing.

## The camera

```js
S.view(640, 650, 1.30);                    // where it starts: the board point at the frame centre, and the scale
S.cam(t, x, y, scale, duration, ease);     // ease: 'inOut' (default), 'linear', 'out', 'in'
S.cam(0, 640, 650, 1.34, 3.0, 'linear');   // a slow push while something draws
```

Rules that came from real mistakes:

- **Frame tightly.** Everything is watched on a phone, and a first draft is almost always too wide and too small. Scale = frame width / the width of what must be in shot, with a margin. In 16:9 that usually gives 1.1 to 1.35. In 9:16 the frame is only 1080 wide, so it usually gives 0.85 to 1.0.
- **The camera arrives before the pen starts.** `wb check` errors if the pen is off-frame.
- **One continuous move per idea**, not one per item. If the next drawing is already in shot, do not chase it.
- **Moves take 0.8 to 2.3 s**, with a slow linear push during holds so the frame is never dead.
- **Do not move away while the pen is still finishing** something at the edge of frame.
- **One wide pull-back to end on**, showing the whole board with the payoff words. Scale about 0.45 to 0.6. Keep 40 px or more of margin. The payoff word should still be at least 90 px on screen. The hand keeps its size, so it stays believable.

## Sizes on screen

`wb check` reads size x camera scale. Aim for:

| Thing | On screen |
|---|---|
| Payoff word | 90 px or more |
| Label | 50 px or more |
| Text inside a drawing | 40 px or more |
| A main drawing | At least 300 px on its short side |
| Marks | Line width 9 to 13, so they match the drawings' 8.5 |

## Layout patterns

- **Two rows, a contrast:** the problem side on top, the solution side below, payoff words at the end of each row.
- **Hub and jobs:** a central drawing with four around it, an arrow out to each, one per verb.
- **List in a bubble:** numbers first on "a list", then each item on its word.
- **Things landing on a person:** arrows from a list onto the character, then the character reacts (sweat drops), and a label.

## 9:16

A complete example: `examples/one-key/`.

- **Stack in a column.** The frame is 1080 wide and 1920 tall, so three things side by side already fill it. The story runs down the board, and the camera travels down with it. Recompose rather than shrink: fewer drawings per shot, bigger type.
- **The final wide shot** stacks both sides of the story. Portrait has spare height, so a stacked cluster leaves room beside it for the payoff words.
- **Stay out of the app's buttons.** Shorts, Reels and TikTok cover about the top 220 px, the bottom 380 px, and the right 140 px of the lower half with their own text and buttons. Keep words out of these zones. `wb check` warns about words there in the final frame. If the video is only for a normal player, ignore that warning.

## Long films

Make one board per minute or so, far apart on the canvas (for example 6000 units apart), each with its own final wide shot. The camera then travels to the next board. Render time grows with length, not with the number of boards.

## Colours and globals

`C.problem`, `C.solution` and the rest are the palette. In marks, `color: 'problem'` also works, as does any hex.
