// The animation, timed to the narration. API: reference/scene-api.md
// S = scene, T = word clock ("T('broke down')" is when those words start), C = palette colours.

// ---- layout (board units = screen px at camera scale 1)
// S.art('car', {cx: 600, cy: 650});
// S.text('title', {cx: 960, cy: 200});
// S.arrow('a1', [100, 100], [400, 300], {bend: .1, color: 'problem'});

// ---- camera
// S.view(640, 650, 1.3);
// S.cam(T('so you') - .3, 1600, 585, 1.28, 2.3);

// ---- pen: one job at a time, each on its own word
// S.draw('car', .6, T('so you') - .2);
// S.then('title');
