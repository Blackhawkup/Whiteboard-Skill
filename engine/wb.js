/* Whiteboard engine: deterministic and seek-driven, so any frame can be rendered in any order.
   Board units = px at camera scale 1. #cam holds #board; the hand lives in screen space above it.
   scene.js uses the global S (scene), T (word clock) and C (palette). Full API: reference/scene-api.md */
(function () {
  const F = window.FILM, ART = window.ART || {}, W = F.W, H = F.H;
  const HOP_MIN = 0.006, HOP_V = 9000, SPEED = F.pen_speed || 2600;     // pen-up hop: s + board px / (px/s); natural pen speed
  const lerp = (a, b, u) => a + (b - a) * u, clamp = (u) => Math.max(0, Math.min(1, u));
  const sio = (u) => 0.5 - 0.5 * Math.cos(Math.PI * clamp(u));
  const EASE = { inOut: sio, linear: clamp, none: clamp, out: (u) => 1 - Math.pow(1 - clamp(u), 3), in: (u) => Math.pow(clamp(u), 3) };

  // ---------------------------------------------------------------- word clock
  const norm = (w) => w.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '');
  const WORDS = (window.WORDS || []).map((x) => Object.assign({ k: norm(x.w) }, x));
  function matches(phrase) {
    const tk = phrase.split(/\s+/).map(norm).filter(Boolean), out = [];
    if (!tk.length) return out;
    for (let i = 0; i + tk.length <= WORDS.length; i++) if (tk.every((t, j) => WORDS[i + j].k === t)) out.push([i, i + tk.length - 1]);
    return out;
  }
  function pick(phrase, o) {
    o = o || {};
    let m = matches(phrase);
    const where = () => m.map(([a]) => WORDS[a].s.toFixed(2) + 's').join(', ');
    if (!m.length) throw new Error('T: "' + phrase + '" is not in the narration');
    if (o.after != null) { const all = where(); m = m.filter(([a]) => WORDS[a].s >= o.after - 1e-3); if (!m.length) throw new Error('T: "' + phrase + '" is not said after ' + o.after.toFixed(2) + 's (it is at ' + all + ')'); return m[0]; }
    if (o.n) { if (!m[o.n - 1]) throw new Error('T: "' + phrase + '" is only said ' + m.length + ' time(s)'); return m[o.n - 1]; }
    if (m.length > 1) throw new Error('T: "' + phrase + '" is said ' + m.length + ' times (' + where() + '). Use a longer phrase, {n: k} or {after: t}.');
    return m[0];
  }
  const T = window.T = (p, o) => WORDS[pick(p, o)[0]].s;
  T.end = (p, o) => WORDS[pick(p, o)[1]].e;
  T.words = WORDS;

  // ---------------------------------------------------------------- items
  const S = window.S = { W, H, items: {}, jobs: [], penEnd: 0, allowed: [] };
  window.C = F.palette;
  const color = (c, dflt) => (c == null ? dflt : (F.palette[c] || c));

  function prep(strokes) {
    let total = 0;
    for (const s of strokes) {
      s.cum = [0];
      for (let i = 1; i < s.pts.length; i++) s.cum.push(s.cum[i - 1] + Math.hypot(s.pts[i][0] - s.pts[i - 1][0], s.pts[i][1] - s.pts[i - 1][1]));
      s.len = s.cum[s.cum.length - 1]; total += s.len;
    }
    return total;
  }
  function pointAt(s, l) {
    const P = s.pts, C_ = s.cum;
    if (l <= 0) return P[0];
    if (l >= s.len) return P[P.length - 1];
    let i = 1; while (C_[i] < l) i++;
    const u = (l - C_[i - 1]) / (C_[i] - C_[i - 1] || 1);
    return [lerp(P[i - 1][0], P[i][0], u), lerp(P[i - 1][1], P[i][1], u)];
  }
  function canvas(parent, w, h, cssW, cssH, z) {
    const c = document.createElement('canvas'); c.width = Math.ceil(w); c.height = Math.ceil(h);
    Object.assign(c.style, { position: 'absolute', left: 0, top: 0, width: cssW + 'px', height: cssH + 'px', zIndex: z });
    parent.appendChild(c); return c;
  }
  function holder(id, x, y, w, h) {
    if (S.items[id]) throw new Error('S: item "' + id + '" is already on the board');
    const d = document.createElement('div'); d.className = 'item'; d.id = 'it_' + id;
    Object.assign(d.style, { left: x + 'px', top: y + 'px', width: w + 'px', height: h + 'px' });
    document.getElementById('board').appendChild(d); return d;
  }

  function place(id, name, o) {
    const m = ART[name]; if (!m) throw new Error('S: no traced image "' + name + '". Is it in drawings.json / labels.json, and did wb art run?');
    const w = o.w || m.board_w, k = w / m.w, h = m.h * k;
    const x = o.cx != null ? o.cx - w / 2 : o.x, y = o.cy != null ? o.cy - h / 2 : o.y;
    const el = holder(id, x, y, w, h);
    const it = { id, name, kind: m.kind, el, x, y, w, h, k, pad: m.pad * k, fontSize: m.font_size ? m.font_size * w / m.board_w : null, layers: {}, traceW: m.board_w };
    const ink = new Image(); ink.src = '../art/' + name + '_ink.png';
    const st = JSON.parse(JSON.stringify(m.strokes));
    it.layers.ink = { strokes: st, total: prep(st), img: ink, cv: canvas(el, m.w, m.h, w, h, 2), last: -1 };
    if (m.fill) {
      const f = new Image(); f.src = '../art/' + name + '_fill.png';
      const fs = [{ pts: m.fill.pts, w: m.fill.w }];
      it.layers.fill = { strokes: fs, total: prep(fs), img: f, cv: canvas(el, m.w, m.h, w, h, 1), last: -1 };
    }
    if (o.rot) { el.style.transform = 'rotate(' + o.rot + 'deg)'; it.rot = o.rot; }
    S.items[id] = it; return it;
  }
  S.art = (id, o) => place(id, (o && o.from) || id, o || {});       // S.art('car', {cx, cy, w})
  S.text = (id, o) => place(id, (o && o.from) || id, o || {});      // S.text('title', {cx, cy})

  S.marks = function (id, strokes, o) {                             // strokes in board coordinates
    o = Object.assign({ color: F.ink, w: 9, pad: 30 }, o || {});
    let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    for (const s of strokes) for (const p of s) { x0 = Math.min(x0, p[0]); y0 = Math.min(y0, p[1]); x1 = Math.max(x1, p[0]); y1 = Math.max(y1, p[1]); }
    x0 -= o.pad; y0 -= o.pad; x1 += o.pad; y1 += o.pad;
    const R = 1.5, el = holder(id, x0, y0, x1 - x0, y1 - y0);
    const St = strokes.map((s) => ({ pts: s.map((p) => [(p[0] - x0) * R, (p[1] - y0) * R]), w: o.w * R }));
    const it = { id, kind: 'mark', el, x: x0, y: y0, w: x1 - x0, h: y1 - y0, k: 1 / R, pad: o.pad, color: color(o.color), layers: {}, src: strokes, lw: o.w, travel: !!o.travel };
    it.layers.ink = { strokes: St, total: prep(St), cv: canvas(el, (x1 - x0) * R, (y1 - y0) * R, x1 - x0, y1 - y0, 2), last: -1 };
    S.items[id] = it; return it;
  };

  // ---- hand-drawn marks ---------------------------------------------------------------------------------
  const wob = (pts, a, seed) => pts.map((p, i) => [p[0] + a * Math.sin(i * 1.7 + seed), p[1] + a * Math.cos(i * 1.3 + seed * 2)]);
  function curve(p0, p1, bend, n) {
    const mx = (p0[0] + p1[0]) / 2, my = (p0[1] + p1[1]) / 2, dx = p1[0] - p0[0], dy = p1[1] - p0[1];
    const c = [mx - dy * bend, my + dx * bend], out = [];
    for (let i = 0; i <= n; i++) { const u = i / n; out.push([(1 - u) * (1 - u) * p0[0] + 2 * u * (1 - u) * c[0] + u * u * p1[0], (1 - u) * (1 - u) * p0[1] + 2 * u * (1 - u) * c[1] + u * u * p1[1]]); }
    return out;
  }
  const seedOf = (id) => { let h = 7; for (const c of id) h = (h * 31 + c.charCodeAt(0)) % 97; return 1 + h / 10; };
  S.line = (id, p0, p1, o) => { o = o || {}; return S.marks(id, [wob(curve(p0, p1, o.bend || 0, 30), 1.3, seedOf(id))], o); };
  S.arrow = function (id, p0, p1, o) {                              // shaft, then one stroke for the head
    o = o || {};
    const s = wob(curve(p0, p1, o.bend || 0, 28), 1.2, seedOf(id)), a = s[s.length - 1], b = s[s.length - 4];
    const ang = Math.atan2(a[1] - b[1], a[0] - b[0]), h = o.head || 32, sp = 0.5;
    return S.marks(id, [s, [[a[0] - h * Math.cos(ang - sp), a[1] - h * Math.sin(ang - sp)], a, [a[0] - h * Math.cos(ang + sp), a[1] - h * Math.sin(ang + sp)]]], Object.assign({ w: 10 }, o));
  };
  S.tick = (id, cx, cy, s, o) => S.marks(id, [[[cx - s * .5, cy - s * .02], [cx - s * .12, cy + s * .36], [cx + s * .55, cy - s * .5]]], Object.assign({ w: 10 }, o));
  S.cross = (id, cx, cy, s, o) => S.marks(id, [[[cx - s / 2, cy - s / 2], [cx + s / 2, cy + s / 2]], [[cx + s / 2, cy - s / 2], [cx - s / 2, cy + s / 2]]], Object.assign({ w: 12 }, o));
  S.ring = function (id, cx, cy, rx, ry, o) {                       // a hand-drawn loop that overshoots its start
    const p = []; for (let i = 0; i <= 44; i++) { const a = -2.2 + (2 * Math.PI + 0.45) * i / 44, g = 1 + 0.035 * (i / 44); p.push([cx + rx * g * Math.cos(a), cy + ry * g * Math.sin(a)]); }
    return S.marks(id, [p], Object.assign({ w: 9 }, o));
  };
  S.drop = function (id, cx, cy, s, o) {                            // a teardrop: apex on top, tangent lines into a round belly
    const r = 0.46 * s, B = Math.acos(r / s), p = [[cx, cy - s]];
    for (let i = 0; i <= 22; i++) { const th = 1.5 * Math.PI - B - (2 * Math.PI - 2 * B) * i / 22; p.push([cx + r * Math.cos(th), cy + r * Math.sin(th)]); }
    p.push([cx, cy - s]); return S.marks(id, [p], Object.assign({ w: 7 }, o));
  };
  S.overlapOK = (a, b) => S.allowed.push([a, b]);                   // ink of a and b may touch on purpose

  // ---------------------------------------------------------------- pen jobs
  function hopsOf(it, L) {
    const St = L.strokes, hops = []; let total = 0;
    for (let i = 1; i < St.length; i++) {
      const a = St[i - 1].pts[St[i - 1].pts.length - 1], b = St[i].pts[0];
      const d = Math.hypot(b[0] - a[0], b[1] - a[1]) * it.k, h = d < 12 ? 0 : HOP_MIN + d / HOP_V;
      hops.push(h); total += h;
    }
    return { hops, total };
  }
  function addJob(it, layer, t0, t1) {
    const L = it.layers[layer], St = L.strokes, job = { it, L, layer, t0, t1, segs: [] };
    let { hops, total } = hopsOf(it, L);
    const span = t1 - t0;
    if (span <= 0) throw new Error('S.draw: "' + it.id + '" has no time (' + t0.toFixed(2) + ' to ' + t1.toFixed(2) + ')');
    if (total > 0.25 * span) { const f = 0.25 * span / total; hops = hops.map((h) => h * f); total = 0.25 * span; }
    const v = L.total / (span - total);
    let t = t0, l0 = 0;
    St.forEach((s, i) => {
      if (i > 0 && hops[i - 1] > 0) {
        job.segs.push({ type: 'hop', t0: t, t1: t + hops[i - 1], l0, a: St[i - 1].pts[St[i - 1].pts.length - 1], b: s.pts[0] });
        t += hops[i - 1];
      }
      const dt = s.len / v;
      job.segs.push({ type: 'draw', t0: t, t1: t + dt, l0, s });
      t += dt; l0 += s.len;
    });
    job.v = v * it.k;                                               // board px per second
    S.jobs.push(job); S.jobs.sort((a, b) => a.t0 - b.t0);
    S.penEnd = Math.max(S.penEnd, t1);
    return job;
  }
  /* S.draw(id, t0)      draw at the natural pen speed, colour afterwards
     S.draw(id, t0, t1)  fit ink + colour inside this window        returns {t0, t1} */
  S.draw = function (id, t0, t1, o) {
    o = o || {};
    const it = S.items[id]; if (!it) throw new Error('S.draw: nothing called "' + id + '" on the board');
    const ink = it.layers.ink, fill = o.fill === false ? null : it.layers.fill;
    const inkT = ink.total * it.k / SPEED + hopsOf(it, ink).total;
    let fillT = fill ? Math.max(0.14, Math.min(0.45, fill.total * it.k / (SPEED * 3.2))) : 0;
    if (t1 == null) t1 = t0 + inkT + fillT; else fillT = Math.min(fillT, 0.25 * (t1 - t0));
    addJob(it, 'ink', t0, t1 - fillT);
    if (fill) addJob(it, 'fill', t1 - fillT, t1);
    return { t0, t1 };
  };
  S.then = (id, o) => S.draw(id, S.penEnd + ((o && o.gap) != null ? o.gap : 0.06), o && o.until, o);   // draw right after the last job

  function jobState(job, t) {
    if (t >= job.t1) { const s = job.L.strokes[job.L.strokes.length - 1]; return { len: job.L.total, pos: s.pts[s.pts.length - 1], lift: 0 }; }
    for (const g of job.segs) {
      if (t < g.t1 || g === job.segs[job.segs.length - 1]) {
        const u = clamp((t - g.t0) / (g.t1 - g.t0 || 1));
        if (g.type === 'draw') return { len: g.l0 + g.s.len * u, pos: pointAt(g.s, g.s.len * u), lift: 0 };
        const e = sio(u);
        return { len: g.l0, pos: [lerp(g.a[0], g.b[0], e), lerp(g.a[1], g.b[1], e)], lift: Math.sin(Math.PI * u) };
      }
    }
  }
  function paint(it, L, len) {
    const key = Math.round(len * 4);
    if (key === L.last) return; L.last = key;
    const c = L.cv.getContext('2d'); c.clearRect(0, 0, L.cv.width, L.cv.height);
    if (len <= 0) return;
    if (len >= L.total - 0.01 && L.img) { c.drawImage(L.img, 0, 0); return; }     // finished: the exact image
    c.lineCap = 'round'; c.lineJoin = 'round'; c.strokeStyle = it.color || '#000';
    let rem = len;
    for (const s of L.strokes) {
      c.lineWidth = s.w; c.beginPath(); c.moveTo(s.pts[0][0], s.pts[0][1]);
      for (let i = 1; i < s.pts.length; i++) {
        const d = s.cum[i] - s.cum[i - 1];
        if (rem >= d) { c.lineTo(s.pts[i][0], s.pts[i][1]); rem -= d; }
        else { const u = rem / (d || 1); c.lineTo(lerp(s.pts[i - 1][0], s.pts[i][0], u), lerp(s.pts[i - 1][1], s.pts[i][1], u)); rem = 0; break; }
      }
      c.stroke(); if (rem <= 0) break;
    }
    if (L.img) { c.globalCompositeOperation = 'source-in'; c.drawImage(L.img, 0, 0); c.globalCompositeOperation = 'source-over'; }
  }

  // ---------------------------------------------------------------- camera
  const camKeys = []; let cam0 = { x: W / 2, y: H / 2, s: 1 }, camReady = false;
  S.view = (x, y, s) => { cam0 = { x, y, s: s || 1 }; };             // where the camera starts
  S.cam = (t, x, y, s, dur, ease) => { camKeys.push({ t, x, y, s, dur: Math.max(dur || 0.001, 0.001), ease: EASE[ease || 'inOut'] || sio }); camReady = false; };
  function camSetup() {
    camKeys.sort((a, b) => a.t - b.t);
    let st = cam0;
    camKeys.forEach((k, i) => {
      k.from = st;
      const nx = camKeys[i + 1], at = nx ? nx.t : k.t + k.dur, e = k.ease((at - k.t) / k.dur);
      st = { x: lerp(k.from.x, k.x, e), y: lerp(k.from.y, k.y, e), s: lerp(k.from.s, k.s, e) };
    });
    camReady = true;
  }
  function camAt(t) {
    if (!camReady) camSetup();
    let k = null;
    for (const c of camKeys) { if (c.t <= t) k = c; else break; }
    if (!k) return cam0;
    const e = k.ease((t - k.t) / k.dur);
    return { x: lerp(k.from.x, k.x, e), y: lerp(k.from.y, k.y, e), s: lerp(k.from.s, k.s, e) };
  }
  const toScreen = (p, c) => [W / 2 + c.s * (p[0] - c.x), H / 2 + c.s * (p[1] - c.y)];
  const boardPt = (job, p) => [job.it.x + p[0] * job.it.k, job.it.y + p[1] * job.it.k];

  // ---------------------------------------------------------------- hand
  const HAND = Object.assign({ ax: 0, ay: 0, k: 0.74 }, window.HAND_META || {}), OFF = [W + 430, H + 620];
  function handAt(t, c) {
    const J = S.jobs;
    for (const j of J) if (t >= j.t0 && t < j.t1) { const s = jobState(j, t); return { xy: toScreen(boardPt(j, s.pos), c), lift: s.lift, on: 1 }; }
    let prev = null, next = null;
    for (const j of J) { if (j.t1 <= t) prev = j; else if (j.t0 > t && !next) next = j; }
    const endOf = (j) => toScreen(boardPt(j, jobState(j, j.t1).pos), c);
    const startOf = (j) => toScreen(boardPt(j, j.L.strokes[0].pts[0]), c);
    const OUT = 0.42, IN = next ? Math.min(0.48, Math.max(0.05, next.t0)) : 0.48;   // frame 0 stays blank even if the first job starts early
    if (prev && next && next.t0 - prev.t1 < 1.15) {                 // travel lifted to the next job
      const g = next.t0 - prev.t1, u = clamp((t - prev.t1) / Math.min(g, 0.5)), a = endOf(prev), b = startOf(next), e = sio(u);
      return { xy: [lerp(a[0], b[0], e), lerp(a[1], b[1], e)], lift: 1, on: 1 };
    }
    if (prev && t - prev.t1 < OUT) {                                // leave the frame
      const a = endOf(prev), e = sio((t - prev.t1) / OUT);
      return { xy: [lerp(a[0], OFF[0], e), lerp(a[1], OFF[1], e)], lift: 1, on: 1 };
    }
    if (next && next.t0 - t < IN) {                                 // come back in
      const b = startOf(next), e = sio(1 - (next.t0 - t) / IN);
      return { xy: [lerp(OFF[0], b[0], e), lerp(OFF[1], b[1], e)], lift: 1, on: 1 };
    }
    return { xy: OFF, lift: 1, on: 0 };
  }

  // ---------------------------------------------------------------- one frame
  S.render = function (t) {
    const c = camAt(t);
    document.getElementById('cam').style.transform = 'translate(' + W / 2 + 'px,' + H / 2 + 'px) scale(' + c.s + ') translate(' + (-c.x) + 'px,' + (-c.y) + 'px)';
    const gr = document.getElementById('grain');
    if (gr) gr.style.backgroundPosition = (-(c.x * c.s) % 512) + 'px ' + (-(c.y * c.s) % 512) + 'px';
    for (const id in S.items) {
      const it = S.items[id];
      const off = (it.x + it.w - c.x) * c.s < -W / 2 - 20 || (it.x - c.x) * c.s > W / 2 + 20 || (it.y + it.h - c.y) * c.s < -H / 2 - 20 || (it.y - c.y) * c.s > H / 2 + 20;
      it.el.style.visibility = off ? 'hidden' : 'visible';
      for (const ln in it.layers) {
        const L = it.layers[ln]; let len = 0;
        for (const j of S.jobs) if (j.L === L) { if (t >= j.t1) len = L.total; else if (t >= j.t0) len = jobState(j, t).len; }
        paint(it, L, len);
      }
    }
    // the hand is over the board, not on it: it never shrinks with a pull-back, so the arm always leaves the frame
    const h = handAt(t, c), img = document.getElementById('hand');
    const sc = HAND.k * Math.max(1.0, Math.min(c.s, 1.3)) * (1 + 0.035 * h.lift);
    const rot = -3 + 5 * ((h.xy[0] - W / 2) / (W / 2));
    img.style.transformOrigin = HAND.ax + 'px ' + HAND.ay + 'px';
    img.style.transform = 'translate(' + (h.xy[0] + 10 * h.lift - HAND.ax) + 'px,' + (h.xy[1] - 16 * h.lift - HAND.ay) + 'px) rotate(' + rot + 'deg) scale(' + sc + ')';
    img.style.opacity = h.on ? 1 : 0;
    const sd = 14 + 22 * h.lift;
    img.style.filter = 'drop-shadow(' + sd * 0.8 + 'px ' + sd + 'px ' + (12 + 14 * h.lift) + 'px rgba(17,17,17,' + (0.2 - 0.05 * h.lift) + '))';
  };

  // ---------------------------------------------------------------- reports for wb check / wb mix
  S.info = function () {
    return {
      W, H, dur: window.DUR,
      items: Object.values(S.items).map((it) => ({ id: it.id, name: it.name, kind: it.kind, x: it.x, y: it.y, w: it.w, h: it.h, pad: it.pad, fontSize: it.fontSize, traceW: it.traceW, layers: Object.keys(it.layers), src: it.src, lw: it.lw, travel: it.travel })),
      jobs: S.jobs.map((j) => ({ id: j.it.id, layer: j.layer, t0: j.t0, t1: j.t1, v: j.v, len: j.L.total * j.it.k, scale: camAt((j.t0 + j.t1) / 2).s })),
      allowed: S.allowed,
    };
  };
  S.camAt = camAt;
  S.penAt = (t) => handAt(t, camAt(t)).xy;
  S.penLog = function () {
    const out = [];
    for (const j of S.jobs) for (const g of j.segs) if (g.type === 'draw') out.push({ t0: g.t0, t1: g.t1, v: j.v, layer: j.layer });
    return out;
  };
  S.start = function () {
    window.CLOCK = { dur: window.DUR };
    window.__seek = (t) => S.render(t);
    const imgs = [...document.images];
    for (const id in S.items) for (const ln in S.items[id].layers) { const im = S.items[id].layers[ln].img; if (im) imgs.push(im); }
    Promise.all(imgs.map((im) => (im.complete ? Promise.resolve() : new Promise((r) => { im.onload = r; im.onerror = () => { console.error('image failed: ' + im.src); r(); }; }))))
      .then(() => { S.render(0); window.__READY = true; });
  };
})();
