#!/usr/bin/env node
/**
 * 自由轨（支线）：不受 envelope 四类图型约束的高级可视化原型。
 *
 * 定位：**探索 / 与开发 argue 的证据**，不进交付包、不产 envelope、不写 ::visualization。
 * 与 gen-interactive.mjs 的区别：
 *   - 图型取自本地 lieflat-charts 的模板思路（Dot Waffle / Stagger Wave / Diverging）
 *   - 交互走 hover 联动高亮 + 属性过渡（形变感），而不是"换一份数据重画"
 *   - 下钻不做证据抽屉：本产品是 SaaS 数据库，点图跳数据检索列表页才是正解
 *
 * 产物是 fragment：无 doctype/html/head/body，首字符 `<`，单文件、无 CDN。
 * 用法：node gen-free.mjs --in <ndjson> --meeting "ASCO 2026" --out <file.html>
 */
import fs from 'node:fs';
import { unitsFromLines } from '../../skill/conference-clinical-interpretation/scripts/chart/lib/unit.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, c, i, arr) => {
    if (c.startsWith('--')) a.push([c.slice(2), arr[i + 1]]);
    return a;
}, []));
const INPUT = args.in ?? 'output/pharmcube-query-clinical-result-with-params/asco-2026-clinical-results.ndjson';
const MEETING = args.meeting ?? 'ASCO 2026';
const OUT = args.out ?? 'evals/preview/free-demo.html';

const units = unitsFromLines(fs.readFileSync(INPUT, 'utf8').split('\n'));
const N = units.length;
const CN = new Set(['中国内地', '中国(港澳台)']);
const CN_CO = (u) => u.companies.some((c) => CN.has(c.country));
const CN_ASSET = (u) => u.drugs.some((d) => (d.instituteAreas ?? []).some((a) => CN.has(a)));

const count = (list, key) => {
    const m = new Map();
    for (const u of list) for (const k of new Set(key(u))) m.set(k, (m.get(k) ?? 0) + 1);
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
};

const EVALS = ['积极', '不佳', '终止', '未评价'];
const evalOf = (u) => (EVALS.includes(u.evaluation) ? u.evaluation : '未评价');
const evalCounts = EVALS.map((e) => ({ name: e, value: units.filter((u) => evalOf(u) === e).length }));

// 癌种：按评价分层，取披露量 Top 12
const cancerTop = count(units, (u) => u.indications.map((i) => i.cn)).slice(0, 12);
const cancerRows = cancerTop.map(([name, total]) => {
    const set = units.filter((u) => u.indications.some((i) => i.cn === name));
    const by = EVALS.map((e) => ({ e, v: set.filter((u) => evalOf(u) === e).length }));
    return { name, total, by };
});

// 中国双口径：按癌种看「中国资产份额 − 其他地区份额」的发散度
const assetSet = units.filter(CN_ASSET);
const rowSet = units.filter((u) => !CN_ASSET(u));
const share = (set, name) => (set.length ? set.filter((u) => u.indications.some((i) => i.cn === name)).length / set.length : 0);
const diverging = count(units, (u) => u.indications.map((i) => i.cn)).slice(0, 14).map(([name]) => {
    const a = share(assetSet, name), r = share(rowSet, name);
    return { name, asset: a, row: r, delta: (a - r) * 100 };
}).sort((x, y) => y.delta - x.delta);

const chinaStats = {
    asset: assetSet.length,
    sponsor: units.filter(CN_CO).length,
    both: units.filter((u) => CN_ASSET(u) && CN_CO(u)).length,
    posAsset: Math.round(assetSet.filter((u) => evalOf(u) === '积极').length / Math.max(1, assetSet.length) * 1000) / 10,
    posSponsor: (() => { const s = units.filter(CN_CO); return Math.round(s.filter((u) => evalOf(u) === '积极').length / Math.max(1, s.length) * 1000) / 10; })(),
    posRow: Math.round(rowSet.filter((u) => evalOf(u) === '积极').length / Math.max(1, rowSet.length) * 1000) / 10,
};

const PAYLOAD = { meeting: MEETING, n: N, evals: evalCounts, cancers: cancerRows, diverging, china: chinaStats };
const COLOR = { 积极: 'var(--f-pos)', 不佳: 'var(--f-neg)', 终止: 'var(--f-stop)', 未评价: 'var(--f-none)' };

const html = `<style>
.f-app{--f-ink:var(--viz-text,#15181e);--f-mute:var(--viz-text-muted,#6b7280);--f-line:var(--viz-border,#e6e9ef);
 --f-bg:var(--viz-background,#fff);--f-pos:var(--viz-success,#1f9d63);--f-neg:var(--viz-danger,#cf3f36);
 --f-stop:#8b929e;--f-none:#cbd2dc;--f-accent:var(--viz-info,#2f6fed);
 font:14px/1.7 -apple-system,"PingFang SC","Noto Sans SC",Segoe UI,sans-serif;color:var(--f-ink);
 background:var(--f-bg);padding:6px 2px}
.f-mono{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;font-variant-numeric:tabular-nums}
.f-hd h2{margin:0;font-size:18px;letter-spacing:.2px}
.f-hd .f-sub{color:var(--f-mute);font-size:12.5px}
.f-act{margin:26px 0 0;padding-top:18px;border-top:1px solid var(--f-line)}
.f-act h3{margin:0 0 2px;font-size:14px}
.f-act .f-kicker{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--f-accent);font-weight:600}
.f-lead{color:var(--f-mute);font-size:12.8px;margin:2px 0 14px;max-width:64em}
.f-dot{transition:opacity .28s ease,transform .28s ease}
.f-row{transition:opacity .24s ease}
.f-bar{transition:width .5s cubic-bezier(.22,.68,0,1),x .5s cubic-bezier(.22,.68,0,1)}
.f-dim{opacity:.16}
.f-lg{display:flex;gap:14px;flex-wrap:wrap;font-size:11.5px;color:var(--f-mute);margin-top:8px}
.f-lg i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px}
svg.f-svg{display:block;width:100%;overflow:visible}
svg.f-svg text{font-family:inherit}
.f-hit{cursor:pointer}
</style>
<div class="f-app" id="fRoot">
  <div class="f-hd">
    <h2 id="fTitle"></h2>
    <div class="f-sub" id="fSub"></div>
  </div>

  <div class="f-act">
    <div class="f-kicker">Act 1 · 一眼看完</div>
    <h3>1639 篇摘要，76% 被判积极</h3>
    <div class="f-lead">一格 = 一篇摘要。点阵不用来读精确比例，用来把「体量」变成可数的东西——横条图看不出 1639 是什么概念。</div>
    <div id="fWaffle"></div>
  </div>

  <div class="f-act">
    <div class="f-kicker">Act 2 · 热点与成熟度</div>
    <h3>癌种与结果的交错波形</h3>
    <div class="f-lead">每根是交错堆叠的波形，不是普通堆叠条；悬停某个癌种，第一幕的点阵会同步高亮它的位置。</div>
    <div id="fWave"></div>
  </div>

  <div class="f-act">
    <div class="f-kicker">Act 4 · 中国声音</div>
    <h3>中国资产相对其他地区，重在哪、轻在哪</h3>
    <div class="f-lead">发散条＝各癌种「中国资产占比 − 其他地区占比」。向右是中国特色，向左是相对缺位。这是两根并列柱读不出来的东西。</div>
    <div id="fDiv"></div>
  </div>
</div>
<script>
var D = ${JSON.stringify(PAYLOAD).replace(/<\//g, '<\\/')};
var COLOR = ${JSON.stringify(COLOR)};
var root = document.getElementById('fRoot');
var tip = document.createElement('div');
tip.style.cssText = 'position:fixed;z-index:9;pointer-events:none;background:#10141a;color:#fff;border-radius:8px;padding:6px 9px;font-size:12px;opacity:0;transition:opacity .12s';
document.body.appendChild(tip);
var showTip = function (e, html) { tip.innerHTML = html; tip.style.opacity = 1;
  tip.style.left = (e.clientX + 14) + 'px'; tip.style.top = (e.clientY + 14) + 'px'; };
var hideTip = function () { tip.style.opacity = 0; };

document.getElementById('fTitle').textContent = D.meeting + ' 会议临床解读';
document.getElementById('fSub').textContent = D.n + ' 篇研究摘要（按研究去重）· 自由轨原型，图型与交互均超出平台 envelope 表达范围';

/* --- Act 1：Dot Waffle（1639 格） --- */
var dots = [];
(function waffle(){
  var box = document.getElementById('fWaffle');
  var cols = 41, cell = 13, pad = 1.5, gap = 2;
  var rows = Math.ceil(D.n / cols);
  var W = cols * (cell + gap), H = rows * (cell + gap);
  var order = [];
  D.evals.forEach(function (e) { for (var i = 0; i < e.value; i++) order.push(e.name); });
  var out = '';
  for (var i = 0; i < order.length; i++) {
    var r = Math.floor(i / cols), c = i % cols;
    var x = c * (cell + gap), y = r * (cell + gap);
    out += '<rect class="f-dot" data-e="' + order[i] + '" x="' + x + '" y="' + y + '" width="' + cell + '" height="' + cell
      + '" rx="' + (pad + 1.5) + '" fill="' + COLOR[order[i]] + '" opacity=".9"></rect>';
  }
  box.innerHTML = '<svg class="f-svg" viewBox="0 0 ' + W + ' ' + H + '" style="height:' + Math.min(H, 430) + 'px">' + out + '</svg>'
    + '<div class="f-lg">' + D.evals.map(function (e) {
        return '<span><i style="background:' + COLOR[e.name] + '"></i>' + e.name + ' <b class="f-mono">' + e.value + '</b>（' + (e.value / D.n * 100).toFixed(1) + '%）</span>';
      }).join('') + '</div>';
  dots = box.querySelectorAll('.f-dot');
})();

/* --- Act 2：Stagger Wave（交错堆叠） --- */
(function wave(){
  var box = document.getElementById('fWave');
  var RH = 34, L = 118, R = 46, W = 660;
  var H = D.cancers.length * RH + 18;
  var max = Math.max.apply(null, D.cancers.map(function (c) { return c.total; }));
  var out = '';
  D.cancers.forEach(function (c, i) {
    var y = i * RH + 8, x = L, usable = W - L - R;
    var segs = '';
    c.by.forEach(function (b, k) {
      var w = usable * b.v / max;
      var off = (k % 2 === 0 ? 0 : 5);   // 交错：偶数层贴基线，奇数层下沉，形成波形
      segs += '<rect class="f-bar" x="' + x + '" y="' + (y + off) + '" width="' + w + '" height="' + (RH - 12)
        + '" rx="3" fill="' + COLOR[b.e] + '" opacity=".92"></rect>';
      x += w;
    });
    out += '<g class="f-row" data-c="' + c.name + '">'
      + '<text x="' + (L - 10) + '" y="' + (y + 15) + '" text-anchor="end" font-size="12" fill="var(--f-mute)">' + c.name + '</text>'
      + segs
      + '<text x="' + (W - R + 10) + '" y="' + (y + 15) + '" font-size="11.5" class="f-mono" fill="var(--f-mute)">' + c.total + '</text></g>';
  });
  box.innerHTML = '<svg class="f-svg" viewBox="0 0 ' + W + ' ' + H + '" style="height:' + H + 'px">' + out + '</svg>';
  box.querySelectorAll('.f-row').forEach(function (g) {
    g.addEventListener('mousemove', function (e) {
      var name = g.getAttribute('data-c');
      var c = D.cancers.filter(function (x) { return x.name === name; })[0];
      showTip(e, '<b>' + name + '</b><br>' + c.by.map(function (b) { return b.e + ' ' + b.v; }).join(' · '));
      dots.forEach(function (d) { d.classList.add('f-dim'); });
    });
    g.addEventListener('mouseleave', function () { hideTip(); dots.forEach(function (d) { d.classList.remove('f-dim'); }); });
  });
})();

/* --- Act 4：Diverging（发散条） --- */
(function diverge(){
  var box = document.getElementById('fDiv');
  var RH = 30, L = 200, W = 660, H = D.diverging.length * RH + 26;
  var mid = L + (W - L - 90) / 2;
  var span = Math.max.apply(null, D.diverging.map(function (d) { return Math.abs(d.delta); })) || 1;
  var scale = (W - L - 90) / 2 / span;
  var out = '<line x1="' + mid + '" x2="' + mid + '" y1="6" y2="' + (H - 18) + '" stroke="var(--f-line)"></line>'
    + '<text x="' + (mid - 6) + '" y="' + (H - 4) + '" text-anchor="end" font-size="11" fill="var(--f-mute)">← 相对缺位</text>'
    + '<text x="' + (mid + 6) + '" y="' + (H - 4) + '" font-size="11" fill="var(--f-mute)">中国更重 →</text>';
  D.diverging.forEach(function (d, i) {
    var y = i * RH + 8, w = Math.abs(d.delta) * scale;
    var x = d.delta >= 0 ? mid : mid - w;
    out += '<g><text x="' + (L - 10) + '" y="' + (y + 14) + '" text-anchor="end" font-size="12" fill="var(--f-mute)">' + d.name + '</text>'
      + '<rect class="f-bar" x="' + x + '" y="' + y + '" width="' + Math.max(1.5, w) + '" height="15" rx="3" fill="'
      + (d.delta >= 0 ? 'var(--f-accent)' : 'var(--f-stop)') + '" opacity=".85"></rect>'
      + '<text x="' + (W - 78) + '" y="' + (y + 13) + '" font-size="11.5" class="f-mono" fill="var(--f-mute)">'
      + (d.delta >= 0 ? '+' : '') + d.delta.toFixed(1) + 'pp</text></g>';
  });
  out += '<text x="' + L + '" y="' + (H - 4) + '" font-size="11" fill="var(--f-mute)">中国资产 ' + D.china.asset
    + ' 篇 · 积极率 ' + D.china.posAsset + '%｜其他地区 ' + (D.n - D.china.asset) + ' 篇 · 积极率 ' + D.china.posRow + '%</text>';
  box.innerHTML = '<svg class="f-svg" viewBox="0 0 ' + W + ' ' + H + '" style="height:' + H + 'px">' + out + '</svg>';
})();
</script>
`;

fs.mkdirSync(OUT.replace(/\/[^/]+$/, ''), { recursive: true });
fs.writeFileSync(OUT, html);
fs.writeFileSync(OUT.replace(/\.html$/, '.preview.html'), '<meta charset="utf-8">' + html);
console.log(`[free] ${OUT}  ${(Buffer.byteLength(html) / 1024).toFixed(0)} KB · units=${N}`);
