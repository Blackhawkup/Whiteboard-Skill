# Generating the images

Stills in Flow cost 0 credits. If a call ever reports a cost, stop and ask.

## The recipe

Every drawing is **one object per image**, so that each can be drawn on its own word and placed anywhere. `wb prompts <film>` builds each prompt from `drawings.json` and the film's style:

> A small hatchback car seen from the side, facing right, broken down, with its front hood popped open and a big cloud of smoke puffing out of the engine. Hand-drawn whiteboard explainer illustration in bold black marker: thick, even, confident black outlines of uniform line weight, rounded line ends, simple friendly shapes, minimal interior detail, no shading, no hatching, no gradients, no texture, no text or letters anywhere. Flat solid bright red fill on the car body only; everything else unfilled white. Single subject centered on a pure flat white background with a wide empty margin, no ground shadow, no frame.

`drawings.json` is one entry per drawing:

```json
[
  {"name": "car", "w": 640, "colour": "problem", "fill_part": "the car body", "subject": "A small hatchback car seen from the side, facing right, ..."},
  {"name": "phone_bubble", "w": 800, "flip": true, "start": "right", "subject": "A smartphone ... with a large empty speech bubble ..."}
]
```

| Field | Meaning |
|---|---|
| `name` | Lower case with underscores. The file and the scene use it |
| `w` | Its width on the board, in board units. Line weight is set for this size, so choose it from your layout |
| `colour` | A palette role or hex for its accent, or leave it out for none. The exact colour is applied later, so Flow's shade does not matter |
| `fill_part` | The one part that gets the colour |
| `subject` | What it is: who, facing which way, doing what |
| `flip` | Mirror the image |
| `start` | Where the pen starts: `top` (default), `left` or `right`. For example, draw a phone before its speech bubble |
| `mode` | `painted` to keep this image's own colours (see below) |
| `from` | Use another entry's image again at a different size (for example `{"name": "key_small", "from": "key", "w": 340}`). Nothing new is generated. Line weight stays even, which plain scaling in `scene.js` would not |

**Why this recipe:** the pen follows dark outlines, so bold, even, simple lines give a clean drawing. Shading and hatching become hundreds of tiny strokes that take forever to draw. Text gets garbled by image models, so all words are written by the hand in a real font instead.

**Say which way things face.** A car driving right should face right in the picture. Plan it from your layout, or use `flip`.

**Count the parts.** "A bank" gets you ten columns, steps and a clock, which is four seconds of pen. "A bank with exactly two columns, no steps, no clock" takes half that. Image models add detail unless told how much. `wb art` prints the pen time of each drawing and flags anything over budget.

## Generating

Check `flow_status`, then `flow_new_project` with the film's title. Use one or two batches:

**Batch 1, if there are recurring characters:** generate each character's first picture, plus the hand if needed, and look at them. Regenerate until the look is right, because everything else follows it.

**Batch 2, everything else, all at once:**

```
flow_agent_images
  project: "<slug>"
  aspect_ratio: "1:1"
  download_quality: "upscaled"
  scenes: [ one prompt per drawing, from prompts.json ]
  references: [ {"image": "<absolute path or asset:<title>>", "name": "the man"} ]
  scene_references: [ [], ["the man"], [] ]     one list per scene
```

With no recurring character, one batch does it, and you can attach your best first drawing as a style reference for the rest. Then call `flow_wait` until `finished` is true. It returns about every 40 seconds, so call it again. If the batch is still running, tell the user images are on the way.

A later batch in the same `project` folder keeps counting up and never overwrites earlier files. Take the file paths from each result. Scenes come back matched by prompt, but check. Look at each image and bring them in by name:

```bash
wb intake <film> car=/path/scene-01.jpeg person=/path/scene-02.jpeg
```

Look at `out/intake.jpg` and show it to the user. It always shows every image the film has so far, so a replacement simply takes its place.

### When a batch fails

- The batch note says "still failed: scene ...": call `flow_retry` with its job id, and only those images are made again.
- Some scenes missing or wrong: ask for just those again with `flow_agent_images`.
- Agent mode unavailable or failing: use `flow_generate`, which goes one at a time (about 1.5 minutes each). Each scene: `type: "image"` (Flow picks its free image model by itself), `aspect_ratio: "1:1"`, `download_quality: "upscaled"`, `max_credits: 0`, and `reference_previous: true` or `reference_images` to keep a character the same.
- Your agent's `flow_agent_images` has no `references` field: Flow Studio is out of date. Update it (`git pull && npm install && npm run build` in `~/flow-mcp`) and restart the agent, or use `flow_generate` for the scenes that need a reference.

### Checking an image

Reject and regenerate, it is free, if: it shows the wrong thing or faces the wrong way; it has any writing; lines are thin, shaded or hatched; the background is not plain white; there is more than one subject; or the character does not match. After `wb art`, a note saying "too detailed" means simplify the prompt.

## The hand

Generated once and reused for every film. Add it to the first batch:

> Photorealistic overhead studio photograph of a right hand holding a black whiteboard marker in a relaxed, natural writing grip, the marker tip touching the surface. Shot from directly above. The hand and wrist enter from the bottom-right corner and the forearm continues out of frame at the bottom-right edge. The marker tip points toward the upper-left and sits near the centre of the image. Plain matte black marker, chisel tip, no logo, no text, cap off. Natural skin, short clean nails, no rings, no watch, a plain charcoal sleeve just visible at the wrist. Soft, even lighting, sharp focus on the whole hand and the tip, no motion blur. Solid seamless pure-white background, no paper texture, no shadows, no reflections.

Name a skin tone in it if the user asked for one. Then:

```bash
wb hand /path/to/image.jpeg
```

Look at `~/WhiteboardFilms/hand/hand_check.jpg`. The red ring must sit on the marker tip and the background must be clean. If the ring is off, pass the tip's pixel in the original picture: `wb hand image.jpeg --tip 790,780`. The user can also photograph their own hand this way: top-down on a white background, marker tip toward the upper left, arm leaving at the bottom right.

## Other looks

- **Other line styles:** change `style_words` in `film.json`. Keep the outlines dark: the ink colour is applied when tracing, so blue pen or chalk are still generated as dark lines on white and recoloured through `palette.ink`.
- **Full colour or shading:** set `"art_mode": "painted"` and describe the colours in `style_colour`. The drawing keeps its own colours. The pen draws the outlines, then a scribble reveals the colours. It still needs clear dark outlines and a white background, and it suits a light board (its dark lines disappear on a dark one). Start simple before trying complex styles.
- **A logo, product or screenshot:** bring it in with `wb intake` as a drawing with `"mode": "painted"`, on a white background. Real logos and products keep their own colours.
