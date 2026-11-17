// "One key, every door". Top: one key opens all three doors, the thief walks in. Below: a safe, one key per door, the thief is stuck at the gym.
// Right-hand column: the payoff words, only seen in the final pull-back.

// ---- the problem
S.text('onepw', {cx: 600, cy: 95});
S.art('key', {cx: 600, cy: 300});
S.art('house', {cx: 195, cy: 785});
S.art('car', {cx: 600, cy: 873});
S.art('bank', {cx: 1005, cy: 812});
S.arrow('a_house', [385, 415], [195, 570], {bend: 0.1, head: 30, color: 'problem'});
S.arrow('a_car', [600, 345], [600, 745], {bend: 0.03, head: 30, color: 'problem'});
S.arrow('a_bank', [810, 420], [985, 630], {bend: -0.1, head: 30, color: 'problem'});
S.text('open1', {cx: 195, cy: 1050});
S.text('open2', {cx: 600, cy: 1050});
S.text('open3', {cx: 1005, cy: 1050});
S.art('key_copy', {cx: 330, cy: 1300});
S.art('gym', {cx: 275, cy: 1620});
S.art('thief', {cx: 860, cy: 1530});
S.arrow('takes', [505, 1305], [680, 1365], {bend: 0.05, head: 26, color: 'problem', w: 10});
const star = (cx, cy, r0, r1, n) => { const p = []; for (let i = 0; i <= 2 * n; i++) { const a = -Math.PI / 2 + i * Math.PI / n, r = i % 2 ? r0 : r1; p.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]); } return [p]; };
S.marks('bang', star(275, 1700, 58, 110, 8), {color: 'problem', w: 10});
S.arrow('t_house', [730, 1240], [215, 1115], {bend: 0.08, head: 30, color: 'problem'});
S.arrow('t_car', [775, 1225], [620, 1115], {bend: 0.05, head: 30, color: 'problem'});
S.arrow('t_bank', [840, 1225], [1000, 1115], {bend: -0.05, head: 30, color: 'problem'});

// ---- the password manager
S.arrow('down', [600, 1700], [600, 1915], {bend: 0.02, head: 34, color: 'solution', w: 11, travel: true});
S.text('pm', {cx: 600, cy: 1990});
S.art('safe', {cx: 390, cy: 2290});
S.art('house2', {cx: 180, cy: 2996});
S.art('car2', {cx: 600, cy: 3054});
S.art('bank2', {cx: 1020, cy: 3017});
S.art('key_round', {cx: 180, cy: 2710});
S.art('key_square', {cx: 600, cy: 2800});
S.art('key_star', {cx: 1020, cy: 2740});
S.arrow('in_round', [190, 2590], [195, 2500], {head: 22, color: 'solution', w: 9});
S.arrow('in_square', [555, 2680], [480, 2500], {bend: 0.06, head: 24, color: 'solution', w: 9});
S.arrow('in_star', [930, 2640], [625, 2450], {bend: 0.05, head: 26, color: 'solution', w: 9});
S.ring('dial', 386, 2277, 92, 92, {color: 'highlight', w: 11});
S.text('onecode', {cx: 895, cy: 2290});
S.arrow('code_ar', [650, 2225], [487, 2235], {bend: 0.05, head: 24, color: 'highlight', w: 10});
S.arrow('t_gym', [665, 1605], [440, 1685], {bend: 0.05, head: 28, color: 'problem'});
S.ring('r_gym', 275, 1705, 150, 140, {color: 'problem', w: 12});

// ---- the payoff
S.text('every', {x: 1170, cy: 880});
S.text('door1', {x: 1170, cy: 1050});
S.text('one', {x: 1170, cy: 2230});
S.text('door2', {x: 1170, cy: 2400});

// ---- the pen: one job at a time, each on its own word
S.draw('key', 0.5, T('opens'));
const H = T('your house', {n: 1}), C = T('your car', {n: 1}), B = T('your bank', {n: 1});
S.draw('a_house', H - 0.06, H + 0.08);
S.draw('house', H + 0.1, C - 0.1);
S.draw('a_car', C - 0.08, C + 0.06);
S.draw('car', C + 0.08, B - 0.1);
S.draw('a_bank', B - 0.08, B + 0.06);
S.draw('bank', B + 0.08, T('a copy') - 0.02);
S.draw('key_copy', T('a copy'), T('the gym') - 0.02);
S.draw('gym', T('the gym'), T('robbed') - 0.02);
S.draw('bang', T('robbed'), T('robbed') + 0.28);
S.draw('thief', T('a thief'), T('a thief') + 2.03);
S.then('takes', {gap: 0.02, until: T('a thief') + 2.2});
S.draw('t_house', T('your house', {n: 2}) - 0.1, T('your house', {n: 2}) + 0.1);
S.draw('open1', T('open', {n: 1}), T('open', {n: 1}) + 0.3);
S.draw('t_car', T('your car', {n: 2}) - 0.05, T('your car', {n: 2}) + 0.12);
S.draw('open2', T('open', {n: 2}), T('open', {n: 2}) + 0.3);
S.draw('t_bank', T('your bank', {n: 2}) - 0.05, T('your bank', {n: 2}) + 0.12);
S.draw('open3', T('open', {n: 3}), T('open', {n: 3}) + 0.3);
const OP = T('one password');
S.draw('onepw', OP, OP + 0.85);
S.draw('down', OP + 1.0, OP + 1.45);
const AS = T.end('a safe');                       // the long pause after "a safe" is when the pen catches up
S.draw('safe', OP + 1.48, AS - 0.1);
S.draw('pm', AS - 0.05, AS + 1.15);
S.draw('house2', AS + 1.2, AS + 2.02);                  // the doors run on over "it makes every door"
S.draw('car2', AS + 2.04, AS + 2.96);
S.draw('bank2', AS + 2.98, AS + 3.76);
S.draw('key_round', AS + 3.78, AS + 4.16);               // the keys land on "key" and just after
S.draw('key_square', AS + 4.18, AS + 4.56);
S.draw('key_star', AS + 4.58, AS + 4.92);
S.draw('in_round', AS + 4.94, AS + 5.1);
S.draw('in_square', AS + 5.12, AS + 5.32);
S.draw('in_star', AS + 5.34, AS + 5.58);
S.draw('dial', T('remember'), T('remember') + 0.24);
S.draw('onecode', T('one code'), T('one code') + 0.46);
S.then('code_ar', {gap: 0.02, until: T('one code') + 0.64});
S.draw('t_gym', T('the thief'), T('the thief') + 0.3);
S.draw('r_gym', T('one door'), T('one door') + 0.34);
const N = T('not every');
S.draw('one', N, N + 0.42);
S.draw('door2', N + 0.44, N + 1.04);
S.draw('every', N + 1.06, N + 1.74);
S.draw('door1', N + 1.76, N + 2.36);

// ---- the camera: board point at the frame centre, and scale
S.view(600, 300, 1.35);
S.cam(0, 600, 300, 1.38, 1.05, 'linear');                // slow push on the key
S.cam(1.05, 600, 650, 0.9, 0.8);                         // pull back: the key reaches the row
S.cam(1.9, 600, 650, 0.92, T('you leave') - 1.9, 'linear');
S.cam(T('you leave') + 0.0, 420, 1320, 1.15, 0.9);       // down to the gym
S.cam(T('a thief') - 0.4, 600, 1280, 0.93, 0.8);          // slide over to the thief
S.cam(T('he tries') - 0.1, 600, 930, 0.88, 0.85);        // the whole row and the thief
S.cam(OP - 0.6, 600, 640, 0.93, 0.8);                     // up to the key
S.cam(OP + 0.88, 600, 2860, 0.95, 1.0);                   // ride the arrow down to the safe; the keys and doors build into the space below
S.cam(OP + 1.9, 600, 2860, 0.96, T('now') - OP - 2.4, 'linear');
S.cam(T('now') - 0.5, 600, 2320, 0.72, 0.8);             // back up so the thief and gym are in shot
S.cam(N - 0.8, 998, 1420, 0.527, 0.8);                   // the whole board, there before the pen writes
S.cam(N, 998, 1420, 0.535, DUR - N, 'linear');           // breathe on the payoff
