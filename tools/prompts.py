"""Build the Flow prompts: one recipe, the film's style, one subject per image."""
from common import load, save

RECIPE = ("Hand-drawn whiteboard explainer illustration{style}: thick, even, confident black outlines of uniform line weight, rounded line ends, simple friendly shapes, "
          "minimal interior detail, no shading, no hatching, no gradients, no texture, no text or letters anywhere. {fill} Single subject centered on a pure flat white background "
          "with a wide empty margin, no ground shadow, no frame.")


def colour_word(h):
    import colorsys
    h = h.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hue, l, s = colorsys.rgb_to_hls(r, g, b)
    hue *= 360
    if s < 0.15:
        return 'grey'
    for lim, name in ((15, 'red'), (40, 'orange'), (65, 'yellow'), (160, 'green'), (200, 'cyan'), (250, 'blue'), (290, 'violet'), (340, 'pink'), (361, 'red')):
        if hue < lim:
            return 'bright ' + name


def write(film):
    cfg = load(film / 'film.json')
    pal = cfg.get('palette', {})
    style = cfg.get('style_words', 'in bold black marker')
    style = (' ' + style) if style else ''
    painted = cfg.get('art_mode') == 'painted'
    out = []
    for d in load(film / 'drawings.json'):
        if d.get('from'):                                               # the same image at another size: nothing to generate
            continue
        c = d.get('colour')
        if painted:
            fill = cfg.get('style_colour', 'Use a few flat colours.')
        elif c and c != 'none':
            fill = f"Flat solid {colour_word(pal.get(c, c))} fill on {d.get('fill_part', 'the main part')} only; everything else unfilled white."
        else:
            fill = 'No colour fill at all, black outlines on white only.'
        out.append({'name': d['name'], 'prompt': d['subject'].rstrip('.') + '. ' + RECIPE.format(style=style, fill=fill)})
    save(film / 'prompts.json', out)
    print(f'{len(out)} prompts -> {film / "prompts.json"} (same order as drawings.json)')
    for p in out:
        print(f"- {p['name']}: {p['prompt'][:90]}...")
