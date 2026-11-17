// "Chatbot vs AI agent". Row 1: car, you, the chatbot's list. Row 2: the agent and its four jobs, then home.
// Right-hand column: the payoff words. Every element is drawn by the one pen on its own word.

// ---- row 1: the problem, and what a chatbot gives you
S.art('car', {cx: 470, cy: 650});
S.art('you', {from: 'person_stressed', cx: 1140, cy: 600});
const BX = 1400, BY = 205;                       // the phone + bubble drawing; the list sits inside the bubble
S.art('chat', {from: 'phone_bubble', x: BX, y: BY});
S.text('chatbot', {cx: BX + 680, cy: BY + 135});
const LX = BX + 46, LY = [BY + 270, BY + 395, BY + 520];
['n1', 'n2', 'n3'].forEach((n, i) => S.text(n, {x: LX, cy: LY[i]}));
['l1', 'l2', 'l3'].forEach((n, i) => S.text(n, {x: LX + 60, cy: LY[i]}));
S.arrow('ar1', [LX - 4, LY[0]], [1296, 545], {bend: -0.16, head: 30, color: 'problem'});
S.arrow('ar2', [LX - 4, LY[1]], [1296, 625], {head: 30, color: 'problem'});
S.arrow('ar3', [LX - 4, LY[2]], [1296, 705], {bend: 0.16, head: 30, color: 'problem'});
S.text('allonyou', {cx: 1140, cy: 228});
S.marks('sweat', [...dropPts(1290, 365, 26), ...dropPts(1320, 438, 20)], {color: 'highlight', w: 7});
function dropPts(cx, cy, s) {
  const r = 0.46 * s, B = Math.acos(r / s), p = [[cx, cy - s]];
  for (let i = 0; i <= 22; i++) { const th = 1.5 * Math.PI - B - (2 * Math.PI - 2 * B) * i / 22; p.push([cx + r * Math.cos(th), cy + r * Math.sin(th)]); }
  p.push([cx, cy - s]); return [p];
}

// ---- row 2: what an agent does
S.arrow('ask', [1140, 935], [1140, 1590], {bend: 0.04, head: 36, color: 'solution', w: 11, travel: true});
S.text('agent', {cx: 1140, cy: 1640});
S.art('hub', {from: 'phone_agent', cx: 1140, cy: 1900});
const JOBS = {garage: [600, 1660], clipboard: [1690, 1660], taxi: [600, 2150], calendar: [1690, 2150]};
const LINES = {garage: [[985, 1790], [790, 1705]], clipboard: [[1295, 1790], [1520, 1705]], taxi: [[985, 2010], [810, 2090]], calendar: [[1295, 2010], [1525, 2095]]};
const TICKS = {garage: [810, 1530], clipboard: [1880, 1530], taxi: [830, 2010], calendar: [1875, 2010]};
for (const k in JOBS) {
  S.art(k, {cx: JOBS[k][0], cy: JOBS[k][1]});
  S.arrow('ln_' + k, LINES[k][0], LINES[k][1], {bend: 0.06, head: 26, color: 'solution', w: 9});
  S.tick('tk_' + k, TICKS[k][0], TICKS[k][1], 54, {color: 'solution'});
}
S.art('house', {cx: 2200, cy: 1880});
S.art('relaxed', {from: 'person_relaxed', cx: 2640, cy: 1925});

// ---- the payoff
S.text('tells', {cx: 2800, cy: 600});
S.text('does', {cx: 3330, cy: 1900});
S.line('under', [2960, 2048], [3700, 2048], {bend: -0.035, color: 'solution', w: 13});

// ---- the pen: one job at a time, each on its own word
const SO = T('so you');
S.draw('car', 0.6, SO - 0.2);
S.draw('you', SO - 0.12, T('what to do', {n: 1}) + 0.42);
S.draw('chat', T('what to do', {n: 1}) + 0.48, T('a list') - 0.3);
const L = T('a list');
S.draw('n1', L - 0.25, L + 0.05); S.draw('n2', L + 0.1, L + 0.38); S.draw('n3', L + 0.43, L + 0.72);
S.draw('l1', T('call'), T.end('call a garage') + 0.1);
S.draw('l2', T('book'), T.end('book a repair') + 0.1);
S.draw('l3', T('find'), T.end('ride home') + 0.1);
S.draw('chatbot', T('helpful') - 0.05, T('but you') - 0.12);
const BUT = T('but you');
S.draw('ar1', BUT + 0.02, BUT + 0.32); S.draw('ar2', BUT + 0.38, BUT + 0.68); S.draw('ar3', BUT + 0.71, BUT + 1.14);
S.draw('allonyou', T('all of it'), T.end('all of it') + 0.4);
S.then('sweat', {until: T.end('all of it') + 0.75});
S.draw('ask', T('now') - 0.1, T('now') + 1.05);            // the pen and the camera travel down together
S.draw('hub', T('now') + 1.1, T('agent', {n: 1}) + 0.95);
S.then('agent', {gap: 0.05, until: T('it calls') - 0.3});
let t = T('calls') - 0.22;
[['garage', T('books')], ['clipboard', T('orders') + 0.22], ['taxi', T('adds') + 0.12], ['calendar', T.end('your calendar') + 1.15]].forEach(([k, next]) => {
  const end = next - 0.2;
  S.draw('ln_' + k, t, t + 0.18);
  S.draw(k, t + 0.2, end);
  t = end + 0.02;
});
const TK = T.end('your calendar') + 1.0;
['garage', 'clipboard', 'taxi', 'calendar'].forEach((k, i) => S.draw('tk_' + k, TK + i * 0.11, TK + i * 0.11 + 0.095));
const YOU = T('you just');
S.draw('house', YOU - 0.02, T('go home') + 1.05);
S.draw('relaxed', T('go home') + 1.1, T('tells') - 0.17);
S.draw('tells', T('tells'), T.end('what to do', {n: 2}) + 0.1);
S.draw('does', T('does'), T.end('for you') + 0.45);
S.then('under', {gap: 0.05, until: T.end('for you') + 0.8});

// ---- the camera: board point at the frame centre, and scale
const A = T('a chatbot tells');
S.view(560, 650, 1.30);
S.cam(0, 560, 650, 1.34, SO - 0.3, 'linear');            // slow push while the car breaks down
S.cam(SO - 0.3, 1600, 585, 1.28, 2.3);                   // one pan: you, then the chatbot
S.cam(SO + 2.0, 1600, 585, 1.31, 6.0, 'linear');         // read the list
S.cam(BUT - 0.3, 1530, 585, 1.30, 0.8);                  // make room for ALL ON YOU
S.cam(T('now') - 0.05, 1145, 1900, 1.14, 1.15);          // ride the arrow down to the agent
S.cam(T('now') + 1.1, 1145, 1900, 1.17, 6.2, 'linear');
S.cam(TK + 0.46, 2440, 1890, 1.3, 0.8);                  // home, once the last tick is down
S.cam(A - 0.55, 2000, 1245, 0.45, 1.1);                  // the whole board, there before the pen writes
S.cam(A + 0.6, 2000, 1245, 0.462, DUR - A - 0.6, 'linear');   // breathe on the payoff
