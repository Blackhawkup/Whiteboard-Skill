# Planning the board

The storyboard decides what appears on the whiteboard during each line. It is the most important creative step. A drawing has to help the viewer understand the line, not just illustrate a word in it.

## Rules

1. **Show what the line means.** "You still have to do all of it" is not a list on screen: it is the tasks physically flying back onto the person. For each line ask what single picture would explain it with the sound off.
2. **Draw the noun the voice says.** If the line says garage, draw a garage, not a generic icon. Keep the drawing literal and let the arrangement carry the idea.
3. **Same characters and objects throughout.** The person who was stressed in scene 1 is the one relaxing at the end. Recurring things are the same drawing or a referenced version of it.
4. **One big board, not slides.** Everything sits in one world and the camera travels. The last shot pulls back to show the whole story, which is the moment viewers remember. Plan the layout so that shot makes sense, for example one row per side of a contrast.
5. **Connect things.** Arrows and lines between drawings do the explaining: who gives what to whom, what leads to what.
6. **Few words, and big.** Labels are one to four words that add meaning. Never write the narration on the board. A label comes after the illustration it names, and sits above it, because the bottom of the frame is easily lost on a phone.
7. **Colour means something.** The problem in one colour, the solution in another, supporting things in a third. A drawing gets one accent colour on one part, and the same colour never touches itself in neighbouring drawings.
8. **Payoff in one or two huge words**, beside the proof. TELLS. and DOES. beat a sentence.
9. **Fewer, bigger.** These are watched on phones. If a shot needs more than about four drawings on screen, split it.

## Budget

The pen needs time. A drawing has to fit inside the words it belongs to, or the voice needs a pause there.

| Thing | Pen time |
|---|---|
| Simple object (house, phone, taxi) | 1 to 1.5 s |
| Detailed object or person (car with smoke, armchair) | 1.5 to 2.5 s |
| Label of 1 to 3 words | 0.5 to 1.5 s |
| Big payoff word | 1 s |
| Arrow, tick, line | 0.2 to 0.3 s |

Too much for the line? Cut a drawing, simplify it, or plan a pause in the voice. Do not plan on the pen going faster.

## Template

Write this in `storyboard.md` and show it to the user. Keep it short enough to read in a minute.

```markdown
# Storyboard: <title>
For: <audience>. They should come away with: <goal>.

## The board
<Where each area sits, how the camera travels, the final wide shot, in two or three lines.>

| # | Narration | What gets drawn, in order | Why it explains the line | Camera |
|---|---|---|---|---|
| 1 | Your car just broke down. | Car with hood up and smoke, then its red colour | Everyone instantly knows this problem | Close on the car, slow push |

## Drawings to generate
car: a small hatchback, hood up, smoke (red body)
...
```

A complete one: `examples/chatbot-vs-agent/storyboard.md`.

For a long film, split the story into boards of about a minute, each with its own wide shot, and let the camera travel to the next board. Tell the user how many boards you planned.
