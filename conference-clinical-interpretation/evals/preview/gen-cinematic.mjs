#!/usr/bin/env node
/**
 * 电影感支线（完全自由轨）：不用柱图，用粒子场 / 弧线流 / 径向汇聚讲同一批数据。
 *
 * 参考件：D:\Users\feishu_download\药物闭环.html（three.js WebGL，Points + LineSegments + OrbitControls）。
 * 本文件用 canvas 2D 复刻同一套语言（粒子、流光、径向），换来：单文件、无 CDN、<100 KB、可 grep 可改。
 *
 * 定位：探索 / 与开发 argue 的证据。不进 dist、不产 envelope。
 * 用法：node gen-cinematic.mjs --in <ndjson> --meeting "ASCO 2026" --out <file.html>
 */
import fs from 'node:fs';
import { unitsFromLines } from '../../skill/conference-clinical-interpretation/scripts/chart/lib/unit.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, c, i, arr) => {
    if (c.startsWith('--')) a.push([c.slice(2), arr[i + 1]]);
    return a;
}, []));
const INPUT = args.in ?? 'output/pharmcube-query-clinical-result-with-params/asco-2026-clinical-results.ndjson';
const MEETING = args.meeting ?? 'ASCO 2026';
const OUT = args.out ?? 'evals/preview/cinematic-demo.html';

const units = unitsFromLines(fs.readFileSync(INPUT, 'utf8').split('\n'));
const N = units.length;
const CN = new Set(['中国内地', '中国(港澳台)']);
const EVALS = ['积极', '不佳', '终止', '未评价'];
const evalOf = (u) => (EVALS.includes(u.evaluation) ? u.evaluation : '未评价');

const top = (list, key, n) => {
    const m = new Map();
    for (const u of list) for (const k of new Set(key(u))) m.set(k, (m.get(k) ?? 0) + 1);
    return [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, n);
};

// 粒子：一篇一粒子，带评价 / 是否中国资产 / 主癌种
const cancers = top(units, (u) => u.indications.map((i) => i.cn), 24).map(([x]) => x);
const cancerIdx = new Map(cancers.map((c, i) => [c, i]));
const particles = units.map((u) => ({
    e: EVALS.indexOf(evalOf(u)),
    ca: u.drugs.some((d) => (d.instituteAreas ?? []).some((a) => CN.has(a))) ? 1 : 0,
    cs: u.companies.some((c) => CN.has(c.country)) ? 1 : 0,
    c: cancerIdx.has(u.indications[0]?.cn) ? cancerIdx.get(u.indications[0].cn) : -1,
    lba: u.lba ? 1 : 0,
}));

// 流向：癌种 → 靶点（去单维度柱图的替代）
const targets = top(units, (u) => u.drugs.flatMap((d) => d.targets), 18).map(([x]) => x);
const targetSet = new Set(targets);
const flows = [];
{
    const m = new Map();
    for (const u of units) {
        const cs_ = [...new Set(u.indications.map((i) => i.cn))].filter((c) => cancerIdx.has(c)).slice(0, 3);
        const ts_ = [...new Set(u.drugs.flatMap((d) => d.targets))].filter((t) => targetSet.has(t));
        for (const c of cs_) for (const t of ts_) {
            const k = c + '|' + t;
            m.set(k, (m.get(k) ?? 0) + 1);
        }
    }
    const rows = [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, 120);
    for (const [k, v] of rows) {
        const [c, t] = k.split('|');
        flows.push({ c, t, v });
    }
}

const asset = particles.filter((p) => p.ca).length;
const sponsor = particles.filter((p) => p.cs).length;
const both = particles.filter((p) => p.ca && p.cs).length;
const PAYLOAD = {
    meeting: MEETING, n: N, particles, cancers, targets, flows,
    evals: EVALS.map((e, i) => ({ name: e, i, value: particles.filter((p) => p.e === i).length })),
    china: { asset, sponsor, both, onlyAsset: asset - both, onlySponsor: sponsor - both, neither: N - asset - (sponsor - both) },
};
const COLOR = ['#1f9d63', '#cf3f36', '#8b929e', '#c3cad6'];

const html = `<style>
.c-app{--c-ink:var(--viz-text,#e9edf4);--c-mute:#8d97a8;--c-line:#242b36;--c-bg:#0a0d13;
 font:14px/1.7 -apple-system,"PingFang SC","Noto Sans SC",Segoe UI,sans-serif;color:var(--c-ink);
 background:radial-gradient(120% 80% at 50% 0%,#121a27 0%,var(--c-bg) 60%);padding:18px 16px 26px;border-radius:14px}
.c-mono{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;font-variant-numeric:tabular-nums}
.c-hd h2{margin:0;font-size:19px;letter-spacing:.3px}
.c-hd .c-sub{color:var(--c-mute);font-size:12.5px}
.c-stage{position:relative;margin:22px 0 0;border:1px solid var(--c-line);border-radius:14px;
 background:linear-gradient(180deg,rgba(255,255,255,.035),rgba(255,255,255,.008));overflow:hidden}
.c-stage canvas{display:block;width:100%;height:340px}
.c-cap{position:absolute;left:16px;top:12px;right:16px;pointer-events:none}
.c-cap b{display:block;font-size:13.5px;letter-spacing:.2px}
.c-cap span{color:var(--c-mute);font-size:11.5px}
.c-pill{position:absolute;right:14px;bottom:12px;display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
.c-pill button{font:inherit;font-size:11.5px;padding:3px 10px;border-radius:999px;cursor:pointer;
 border:1px solid var(--c-line);background:rgba(255,255,255,.04);color:var(--c-ink);transition:.18s}
.c-pill button[aria-pressed="true"]{background:rgba(47,111,237,.22);border-color:#3b6fd4;color:#cfe0ff}
.c-kpi{display:flex;gap:22px;flex-wrap:wrap;margin:6px 0 0;font-size:12px;color:var(--c-mute)}
.c-kpi b{color:var(--c-ink);font-size:15px;letter-spacing:.2px}
.c-lg{display:flex;gap:14px;flex-wrap:wrap;font-size:11.5px;color:var(--c-mute);margin:10px 0 0}
.c-lg i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}
</style>
<div class="c-app" id="cRoot">
  <div class="c-hd">
    <h2 id="cTitle"></h2>
    <div class="c-sub" id="cSub"></div>
  </div>

  <div class="c-stage"><canvas id="cv1"></canvas>
    <div class="c-cap"><b>1639 粒研究摘要，成团还是散开</b><span>每粒 = 一篇；位置由癌种与评价决定，越靠外越晚披露。悬停右下角筛选，看整片星图重排。</span></div>
    <div class="c-pill" id="cPill1"></div>
  </div>
  <div class="c-lg" id="cLg"></div>

  <div class="c-stage"><canvas id="cv2"></canvas>
    <div class="c-cap"><b>癌种 → 靶点，谁在喂谁</b><span>弧线粗细 = 该癌种下研究该靶点的摘要数；流光方向表示证据流向。悬停左岸癌种可单独追踪。</span></div>
  </div>

  <div class="c-stage"><canvas id="cv3"></canvas>
    <div class="c-cap"><b>两条中国口径的月食</b><span>外环 = 研发机构地区含中国，内环 = 申办方登记地在中国；两环重叠的扇区才是「既在中国人账上、也由中国人做」。</span></div>
    <div class="c-kpi" id="cKpi"></div>
  </div>
</div>
<script>
var D = ${JSON.stringify(PAYLOAD).replace(/<\//g, '<\\/')};
var C = ${JSON.stringify(COLOR)};
var MUTE = '#8d97a8';
document.getElementById('cTitle').textContent = D.meeting + ' 会议临床解读';
document.getElementById('cSub').textContent = D.n + ' 篇研究摘要（按研究去重）· 粒子 / 弧流 / 径向视图 · 自由轨原型';

var fit = function (cv, h) {
  var dpr = Math.min(2, window.devicePixelRatio || 1);
  var w = cv.clientWidth || 660;
  cv.width = w * dpr; cv.height = h * dpr;
  var g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { g: g, w: w, h: h };
};

/* ---------- 星图：一篇一粒子 ---------- */
(function star(){
  var cv = document.getElementById('cv1'), H = 340, S = fit(cv, H), g = S.g, W = S.w;
  var cx = W / 2, cy = H / 2 + 6, R = Math.min(W, H) * 0.42;
  var filter = { e: -1, cn: 0 };
  var pts = D.particles.map(function (p, i) {
    var ang = (i / D.particles.length) * Math.PI * 2 * 7.3;
    var ring = 0.32 + 0.68 * ((p.c >= 0 ? p.c : 11) / 24);
    var rr = R * ring * (0.82 + 0.18 * Math.sin(i * 1.7));
    return { p: p, a: ang, r: rr, x: cx + Math.cos(ang) * rr, y: cy + Math.sin(ang) * rr * 0.86,
      tx: cx + Math.cos(ang) * rr, ty: cy + Math.sin(ang) * rr * 0.86, ph: i * 0.37, lba: p.lba };
  });
  var mouse = { x: cx, y: cy };
  cv.addEventListener('mousemove', function (e) {
    var b = cv.getBoundingClientRect(); mouse.x = e.clientX - b.left; mouse.y = e.clientY - b.top;
  });
  var pills = D.evals.map(function (e) {
    return '<button data-e="' + e.i + '" aria-pressed="false">' + e.name + ' ' + e.value + '</button>';
  }).join('') + '<button data-cn="1" aria-pressed="false">只看中国资产</button>';
  document.getElementById('cPill1').innerHTML = pills;
  document.getElementById('cPill1').addEventListener('click', function (ev) {
    var b = ev.target.closest('button'); if (!b) return;
    if (b.dataset.cn) { filter.cn = filter.cn ? 0 : 1; b.setAttribute('aria-pressed', filter.cn ? 'true' : 'false'); }
    else { var e = +b.dataset.e; filter.e = filter.e === e ? -1 : e;
      [].forEach.call(this.querySelectorAll('button[data-e]'), function (x) {
        x.setAttribute('aria-pressed', +x.dataset.e === filter.e ? 'true' : 'false'); }); }
    layout();
  });
  function layout(){
    pts.forEach(function (o, i) {
      var on = (filter.e < 0 || o.p.e === filter.e) && (!filter.cn || o.p.ca);
      var k = on ? 1 : 0;
      // 命中项向外推、未命中项向内收，形成重排感
      var rr = o.r * (k ? 1 : 0.52);
      o.tx = cx + Math.cos(o.a) * rr; o.ty = cy + Math.sin(o.a) * rr * 0.86;
    });
  }
  document.getElementById('cLg').innerHTML = D.evals.map(function (e) {
    return '<span><i style="background:' + C[e.i] + '"></i>' + e.name + ' <b class="c-mono">' + e.value + '</b></span>';
  }).join('') + '<span><i style="background:#fff"></i>白点带外圈 = LBA</span>';

  var t0 = performance.now();
  (function loop(now){
    var dt = (now - t0) / 1000; t0 = now;
    g.clearRect(0, 0, W, H);
    var pg = g.createRadialGradient(cx, cy, 0, cx, cy, R * 1.18);
    pg.addColorStop(0, 'rgba(47,111,237,.10)'); pg.addColorStop(1, 'rgba(47,111,237,0)');
    g.fillStyle = pg; g.beginPath(); g.arc(cx, cy, R * 1.18, 0, 6.2832); g.fill();
    for (var i = 0; i < pts.length; i++) {
      var o = pts[i];
      o.x += (o.tx - o.x) * Math.min(1, dt * 3.2);
      o.y += (o.ty - o.y) * Math.min(1, dt * 3.2);
      var wob = Math.sin(dt * 0.7 + o.ph) * 1.6;
      var dx = o.x - mouse.x, dy = o.y - mouse.y, d2 = dx * dx + dy * dy;
      var hot = d2 < 5000;
      var on = (filter.e < 0 || o.p.e === filter.e) && (!filter.cn || o.p.ca);
      g.globalAlpha = on ? (hot ? 1 : 0.86) : 0.12;
      g.fillStyle = C[o.p.e];
      g.beginPath(); g.arc(o.x + wob * 0.3, o.y + wob, hot ? 2.6 : 1.7, 0, 6.2832); g.fill();
      if (o.p.lba) { g.strokeStyle = 'rgba(255,255,255,.55)'; g.lineWidth = 0.8;
        g.beginPath(); g.arc(o.x, o.y, 3.6, 0, 6.2832); g.stroke(); }
    }
    g.globalAlpha = 1;
    requestAnimationFrame(loop);
  })(t0);
})();

/* ---------- 弧流：癌种 → 靶点 ---------- */
(function arc(){
  var cv = document.getElementById('cv2'), H = 340, S = fit(cv, H), g = S.g, W = S.w;
  var L = Math.min(230, W * 0.3), R = W - 96;
  var leftSet = [];
  D.flows.forEach(function (f) { if (leftSet.indexOf(f.c) < 0) leftSet.push(f.c); });
  var pos = {};
  leftSet.forEach(function (c, i) { pos['L:' + c] = { x: L, y: 44 + i * ((H - 80) / Math.max(1, leftSet.length - 1)), label: c, side: 'l' }; });
  D.targets.forEach(function (t, i) { pos['R:' + t] = { x: R, y: 40 + i * ((H - 76) / Math.max(1, D.targets.length - 1)), label: t, side: 'r' }; });
  var maxV = Math.max.apply(null, D.flows.map(function (f) { return f.v; }));
  var hover = null;
  cv.addEventListener('mousemove', function (e) {
    var b = cv.getBoundingClientRect(), mx = e.clientX - b.left, my = e.clientY - b.top;
    hover = null;
    Object.keys(pos).forEach(function (k) {
      var p = pos[k]; if (Math.abs(p.x - mx) < 78 && Math.abs(p.y - my) < 9) hover = p.label;
    });
  });
  cv.addEventListener('mouseleave', function () { hover = null; });
  var t0 = performance.now();
  (function loop(now){
    var dt = (now - t0) / 1000;
    g.clearRect(0, 0, W, H);
    D.flows.forEach(function (f, i) {
      var a = pos['L:' + f.c], b = pos['R:' + f.t]; if (!a || !b) return;
      var on = !hover || f.c === hover || f.t === hover;
      var w = 0.5 + 3.4 * Math.pow(f.v / maxV, 0.7);
      g.strokeStyle = on ? 'rgba(96,165,250,.42)' : 'rgba(120,132,150,.10)';
      g.lineWidth = on ? w : 0.6;
      g.beginPath(); g.moveTo(a.x, a.y);
      g.bezierCurveTo(a.x + (b.x - a.x) * 0.55, a.y, a.x + (b.x - a.x) * 0.45, b.y, b.x, b.y);
      g.stroke();
      if (on && f.v > maxV * 0.22) {
        var t = ((now / 1400) + i * 0.13) % 1;
        var mx = a.x + (b.x - a.x) * t, my = a.y + (b.y - a.y) * t;
        g.fillStyle = 'rgba(191,219,254,.95)';
        g.beginPath(); g.arc(mx, my, 1.9, 0, 6.2832); g.fill();
      }
    });
    Object.keys(pos).forEach(function (k) {
      var p = pos[k];
      var isHot = hover === p.label;
      g.fillStyle = isHot ? '#dbeafe' : (hover ? '#5b6472' : '#aab4c4');
      g.font = (isHot ? '600 ' : '') + '12px -apple-system,"PingFang SC",sans-serif';
      g.textAlign = p.side === 'l' ? 'right' : 'left';
      g.fillText(p.label, p.side === 'l' ? p.x - 10 : p.x + 10, p.y + 4);
    });
    requestAnimationFrame(loop);
  })(t0);
})();

/* ---------- 径向：两条中国口径 ---------- */
(function radial(){
  var cv = document.getElementById('cv3'), H = 340, S = fit(cv, H), g = S.g, W = S.w;
  var cx = W / 2, cy = H / 2 + 4, Rox = Math.min(W, H) * 0.34, Rox2 = Rox - 26, Rin = Rox - 58, Rin2 = Rin - 22;
  var seg = function (cx, cy, r1, r2, a0, a1, color, alpha) {
    g.beginPath();
    g.arc(cx, cy, r2, a0, a1); g.arc(cx, cy, r1, a1, a0, true); g.closePath();
    g.fillStyle = color; g.globalAlpha = alpha; g.fill(); g.globalAlpha = 1;
  };
  var f = function (v) { return v / D.n * 6.2832; };
  var B = D.china;
  var t0 = performance.now();
  (function loop(now){
    var dt = (now - t0) / 1000;
    g.clearRect(0, 0, W, H);
    var grow = Math.min(1, dt);
    var a0 = -Math.PI / 2;
    // 外环：中国资产
    seg(cx, cy, Rox2, Rox, a0, a0 + f(B.asset) * grow, '#2f6fed', .55);
    seg(cx, cy, Rox2, Rox, a0 + f(B.asset), a0 + 6.2832, '#1b2432', .9);
    // 内环：中国申办方
    seg(cx, cy, Rin2, Rin, a0 + f(B.onlyAsset), a0 + f(B.onlyAsset) + f(B.sponsor) * grow, '#12b981', .5);
    seg(cx, cy, Rin2, Rin, a0, a0 + f(B.onlyAsset), '#1b2432', .9);
    seg(cx, cy, Rin2, Rin, a0 + f(B.onlyAsset) + f(B.sponsor), a0 + 6.2832, '#1b2432', .9);
    // 重叠扇区高亮 + 呼吸
    var pulse = 0.5 + 0.25 * Math.sin(now / 620);
    seg(cx, cy, Rin2, Rox, a0 + f(B.onlyAsset), a0 + f(B.onlyAsset) + f(B.both), '#f0abfc', pulse * 0.55);
    g.fillStyle = '#e9edf4'; g.textAlign = 'center';
    g.font = '600 26px "IBM Plex Mono",ui-monospace,monospace';
    g.fillText(B.asset, cx, cy + 2);
    g.font = '11.5px -apple-system,"PingFang SC",sans-serif'; g.fillStyle = MUTE;
    g.fillText('研发机构含中国', cx, cy + 22);
    requestAnimationFrame(loop);
  })(t0);
  document.getElementById('cKpi').innerHTML = [
    ['中国资产', B.asset], ['中国申办方', B.sponsor], ['两者都是', B.both],
    ['仅资产侧', B.onlyAsset], ['仅申办方', B.onlySponsor], ['两者都不占', B.neither],
  ].map(function (x) { return '<span>' + x[0] + ' <b class="c-mono">' + x[1] + '</b></span>'; }).join('');
})();
</script>
`;

fs.mkdirSync(OUT.replace(/\/[^/]+$/, ''), { recursive: true });
fs.writeFileSync(OUT, html);
fs.writeFileSync(OUT.replace(/\.html$/, '.preview.html'), '<meta charset="utf-8">' + html);
console.log(`[cinematic] ${OUT}  ${(Buffer.byteLength(html) / 1024).toFixed(0)} KB · units=${N} flows=${flows.length}`);
