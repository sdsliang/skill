#!/usr/bin/env node
/**
 * 支线原型：把一场会议的临床结果集渲染成单文件交互解读页（HTML fragment）。
 *
 * 和 envelope JSON 的分工：
 *   - JSON  envelope = 口径严格 + 可下钻到证据列表页（平台唯一支持下钻的通道）
 *   - HTML fragment = 质感 / 动画 / 页内联动；点击只做页内筛选，不做跨页跳转
 *
 * 产物是 fragment：不含 doctype / html / head / body 包裹，首字符必须是 `<`。
 * 数据全部内联，不依赖 CDN，可离线打开。
 *
 * 用法：node gen-interactive.mjs --in <ndjson> --meeting "ASCO 2026" --out <file.html>
 */
import fs from 'node:fs';
import path from 'node:path';
import { unitsFromLines } from '../../skill/conference-clinical-interpretation/scripts/chart/lib/unit.mjs';

const args = Object.fromEntries(
    process.argv.slice(2).reduce((acc, cur, i, a) => {
        if (cur.startsWith('--')) acc.push([cur.slice(2), a[i + 1]]);
        return acc;
    }, []),
);

const INPUT = args.in ?? 'output/pharmcube-query-clinical-result-with-params/asco-2026-clinical-results.ndjson';
const MEETING = args.meeting ?? 'ASCO 2026';
const OUT = args.out ?? 'evals/preview/interactive-demo.html';

const units = unitsFromLines(fs.readFileSync(INPUT, 'utf8').split('\n'));

/* ---------- 维度字典 ---------- */
const topBy = (getKeys, n) => {
    const m = new Map();
    for (const u of units) for (const k of getKeys(u)) m.set(k, (m.get(k) ?? 0) + 1);
    return [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, n).map(([k]) => k);
};

const NON_TARGET = new Set(['not available', 'n/a', 'na', 'none', 'unknown', 'unclear', 'tbd', '其他', 'other']);
const realTargets = (u) => u.drugs.flatMap((d) => d.targets).filter((t) => !NON_TARGET.has(String(t).toLowerCase()));

const cancers = topBy((u) => u.indications.map((i) => i.cn), 20);
const targets = topBy((u) => realTargets(u), 20);
const drugs = topBy((u) => u.drugs.map((d) => d.cn), 40);
const stages = ['早期', '局部晚期', '晚期', 'III期', 'II期', 'IV期', 'I期', '广泛期'];
const evals = ['积极', '不佳', '终止', '-'];

const dayList = [...new Set(units.map((u) => u.day).filter(Boolean))].sort();

const idx = (arr, v) => {
    const i = arr.indexOf(v);
    return i;
};

const rows = units.map((u) => {
    const targetsOf = realTargets(u);
    return {
        t: u.title || '(无标题)',
        c: [...new Set(u.indications.map((i) => idx(cancers, i.cn)).filter((i) => i >= 0))],
        g: [...new Set(targetsOf.map((t) => idx(targets, t)).filter((i) => i >= 0))],
        d: [...new Set(u.drugs.map((d) => idx(drugs, d.cn)).filter((i) => i >= 0))],
        s: idx(stages, u.stages[0]?.cn ?? ''),
        e: idx(evals, u.evaluation || '-'),
        b: u.lba ? 1 : 0,
        k: !!u.keyEvidence && !/^(-|—|–|n\/a|na|none|否|无|no|null)$/i.test(String(u.keyEvidence).trim()),
        y: dayList.indexOf(u.day),
        l: u.link || '',
        co: u.companies[0]?.cn || '',
    };
});

const payload = { meeting: MEETING, cancers, targets, drugs, stages, evals, days: dayList, rows };

/* ---------- 页面 ---------- */
const html = `<style>
.wv-app{--wv-ink:var(--viz-text,#161b22);--wv-mute:var(--viz-text-muted,#6b7280);--wv-line:var(--viz-border,#e4e8ee);
  --wv-bg:var(--viz-background,#ffffff);--wv-surface:var(--viz-surface,#ffffff);
  --wv-pos:var(--viz-success,#1f9d63);--wv-neg:var(--viz-danger,#cf3f36);--wv-stop:#8b929e;--wv-none:#c8ced8;
  --wv-accent:var(--viz-info,#2f6fed);
  font:14px/1.65 -apple-system,"PingFang SC","Noto Sans SC","Noto Sans CJK SC",Segoe UI,sans-serif;
  color:var(--wv-ink);background:var(--wv-bg);padding:4px;position:relative}
.wv-app *{box-sizing:border-box}
.wv-mono{font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;font-variant-numeric:tabular-nums}
.wv-hd{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin:0 0 2px}
.wv-hd h2{font-size:17px;margin:0;letter-spacing:.2px}
.wv-hd .wv-sub{color:var(--wv-mute);font-size:12.5px}
.wv-kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(104px,1fr));gap:8px;margin:12px 0 16px}
.wv-kpi div{background:linear-gradient(180deg,color-mix(in srgb,var(--wv-accent) 6%,transparent),transparent);
  border:1px solid var(--wv-line);border-radius:10px;padding:9px 11px}
.wv-kpi b{display:block;font-size:19px;line-height:1.25;font-weight:600}
.wv-kpi span{font-size:11.5px;color:var(--wv-mute)}
.wv-bar{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin:0 0 14px;padding:8px 10px;
  border:1px solid var(--wv-line);border-radius:10px;background:color-mix(in srgb,var(--wv-ink) 2%,transparent)}
.wv-bar .wv-lab{font-size:11.5px;color:var(--wv-mute);margin-right:2px}
.wv-chip{font-size:12px;padding:3px 9px;border-radius:999px;border:1px solid var(--wv-line);
  background:var(--wv-surface);cursor:pointer;transition:.16s;white-space:nowrap}
.wv-chip:hover{border-color:var(--wv-accent);color:var(--wv-accent)}
.wv-chip[aria-pressed="true"]{background:var(--wv-accent);border-color:var(--wv-accent);color:#fff}
.wv-bar input{border:1px solid var(--wv-line);border-radius:8px;padding:4px 9px;font-size:12px;
  background:var(--wv-surface);color:inherit;outline:none;min-width:150px}
.wv-bar input:focus{border-color:var(--wv-accent)}
.wv-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:860px){.wv-grid{grid-template-columns:1fr}}
.wv-card{border:1px solid var(--wv-line);border-radius:12px;padding:12px 14px 10px;background:var(--wv-surface);
  box-shadow:0 1px 2px rgba(16,24,40,.04)}
.wv-card.wv-wide{grid-column:1/-1}
.wv-card h3{margin:0;font-size:13.5px;font-weight:600}
.wv-card .wv-cap{color:var(--wv-mute);font-size:11.5px;margin:1px 0 8px}
.wv-tip{position:fixed;z-index:9;pointer-events:none;background:#11151c;color:#fff;border-radius:8px;
  padding:7px 9px;font-size:12px;line-height:1.5;opacity:0;transition:opacity .12s;max-width:280px;
  box-shadow:0 8px 24px rgba(0,0,0,.25)}
.wv-tip b{font-weight:600}
.wv-sig{display:flex;gap:10px;align-items:flex-start;padding:9px 4px;border-top:1px solid var(--wv-line)}
.wv-sig:first-of-type{border-top:0}
.wv-sig .wv-rk{flex:0 0 22px;font-size:11px;color:var(--wv-mute);padding-top:2px}
.wv-sig .wv-ttl{font-size:12.8px;line-height:1.5}
.wv-sig .wv-ttl a{color:inherit;text-decoration:none;border-bottom:1px solid color-mix(in srgb,var(--wv-accent) 35%,transparent)}
.wv-sig .wv-ttl a:hover{color:var(--wv-accent)}
.wv-bdg{display:inline-block;font-size:10.5px;padding:1px 6px;border-radius:5px;margin-right:4px;
  border:1px solid currentColor;line-height:1.5;vertical-align:1px}
.wv-pos{color:var(--wv-pos)}.wv-neg{color:var(--wv-neg)}.wv-stop{color:var(--wv-stop)}.wv-none{color:#98a0ad}
.wv-lba{color:#8a5cf6;border-color:currentColor}
.wv-list{max-height:340px;overflow:auto;margin-top:6px}
.wv-row{display:flex;gap:8px;padding:6px 2px;border-top:1px dashed var(--wv-line);font-size:12.2px;align-items:baseline}
.wv-row:first-child{border-top:0}
.wv-row .wv-m{color:var(--wv-mute);font-size:11px;white-space:nowrap}
.wv-foot{color:var(--wv-mute);font-size:11.5px;margin-top:12px;border-top:1px solid var(--wv-line);padding-top:8px}
.wv-lg{display:flex;gap:12px;flex-wrap:wrap;font-size:11.5px;color:var(--wv-mute);margin:2px 0 0}
.wv-lg i{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:4px;vertical-align:0}
svg.wv-svg{display:block;width:100%;overflow:visible}
svg.wv-svg text{font-family:inherit}
.wv-hit{cursor:pointer}
</style>
<div class="wv-app" id="wvRoot">
  <div class="wv-hd">
    <h2>${MEETING} 临床披露解读</h2>
    <span class="wv-sub">${units.length} 篇研究摘要 · 页内可联动筛选 · 数字与正式报告同口径（按研究去重）</span>
  </div>
  <div class="wv-kpi" id="wvKpi"></div>
  <div class="wv-bar" id="wvBar">
    <span class="wv-lab">癌种</span><span id="wvCancerChips"></span>
    <span class="wv-lab" style="margin-left:8px">阶段</span><span id="wvStageChips"></span>
    <span class="wv-lab" style="margin-left:8px">评价</span><span id="wvEvalChips"></span>
    <input id="wvQ" placeholder="搜药物 / 靶点 / 标题…">
    <button class="wv-chip" id="wvReset">清空</button>
  </div>

  <div class="wv-grid">
    <div class="wv-card wv-wide">
      <h3>披露节奏</h3>
      <div class="wv-cap">每天披露的研究摘要数；紫点为 LBA（late-breaking）。点一天只看那天。</div>
      <div id="wvTime"></div>
    </div>

    <div class="wv-card">
      <h3>癌种热度环</h3>
      <div class="wv-cap">弧长 = 摘要数，内圈颜色 = 积极占比。点一个癌种只看它。</div>
      <div id="wvRing"></div>
      <div class="wv-lg"><span><i style="background:var(--wv-pos)"></i>积极</span>
        <span><i style="background:color-mix(in srgb,var(--wv-pos) 55%,var(--wv-none))"></i>积极占比中等</span>
        <span><i style="background:var(--wv-none)"></i>未评价为主</span></div>
    </div>

    <div class="wv-card">
      <h3>药物星座</h3>
      <div class="wv-cap">横轴 = 平均阶段（越右越晚），纵轴 = 摘要数，气泡大小 = 摘要数，颜色 = 积极占比。</div>
      <div id="wvScatter"></div>
    </div>

    <div class="wv-card wv-wide">
      <h3>靶点 × 癌种 覆盖矩阵</h3>
      <div class="wv-cap">谁在哪个靶点上、针对哪些癌种堆了最多数据；深色 = 该组合的摘要数多。</div>
      <div id="wvMatrix"></div>
    </div>

    <div class="wv-card">
      <h3>可行动信号</h3>
      <div class="wv-cap">按「关键证据 + LBA + 晚期 + 积极」排序，只列当前筛选下最该读的。</div>
      <div id="wvSignals"></div>
    </div>

    <div class="wv-card">
      <h3>当前筛选下的摘要<span class="wv-mono" id="wvCount" style="color:var(--wv-mute);font-size:12px"></span></h3>
      <div class="wv-cap">点标题开原文；列表与上面所有图共用同一份筛选状态。</div>
      <div class="wv-list" id="wvList"></div>
    </div>
  </div>

  <div class="wv-foot">口径：一条 = 一个 <code>clinical_result_extra_esid</code>；多值维度同一摘要内先去重，故各维度占比之和可 &gt; 100%。数据源：平台临床结果结构化表（${MEETING}，按 meeting_tags 匹配）。</div>
  <div class="wv-tip" id="wvTip"></div>
</div>
<script>
(function(){
const D = ${JSON.stringify(payload).replace(/<\//g, '<\\/')};
const EV = ['积极','不佳','终止','-'];
const EVCOL = ['var(--wv-pos)','var(--wv-neg)','var(--wv-stop)','var(--wv-none)'];
const state = { cancer: null, stage: null, eval: null, day: null, q: '' };

const root = document.getElementById('wvRoot');
const tip = document.getElementById('wvTip');
const showTip = (e, html) => { tip.innerHTML = html; tip.style.opacity = 1;
  const x = Math.min(e.clientX + 14, innerWidth - 290), y = e.clientY + 16;
  tip.style.left = x + 'px'; tip.style.top = y + 'px'; };
const hideTip = () => { tip.style.opacity = 0; };

const match = (r) => {
  if (state.cancer !== null && !r.c.includes(state.cancer)) return false;
  if (state.stage !== null && r.s !== state.stage) return false;
  if (state.eval !== null && r.e !== state.eval) return false;
  if (state.day !== null && r.y !== state.day) return false;
  if (state.q) {
    const q = state.q.toLowerCase();
    const hay = (r.t + ' ' + r.c.map(i=>D.cancers[i]).join(' ') + ' ' + r.g.map(i=>D.targets[i]).join(' ') + ' ' + r.d.map(i=>D.drugs[i]).join(' ')).toLowerCase();
    if (!hay.includes(q)) return false;
  }
  return true;
};
const M = () => D.rows.filter(match);

/* ---------- KPI ---------- */
function kpi(rows){
  const pos = rows.filter(r=>r.e===0).length, neg = rows.filter(r=>r.e===1).length;
  const stop = rows.filter(r=>r.e===2).length, lba = rows.filter(r=>r.b).length;
  const key = rows.filter(r=>r.k).length;
  const items = [[rows.length,'研究摘要（当前筛选）'],[key,'含关键证据'],[pos,'积极'],[neg,'不佳'],[stop,'终止'],[lba,'LBA']];
  document.getElementById('wvKpi').innerHTML = items.map(([v,l])=>
    '<div><b class="wv-mono">'+v+'</b><span>'+l+'</span></div>').join('');
}

/* ---------- 芯片 ---------- */
function chips(){
  const mk = (label, i, dim, count) => '<button class="wv-chip" data-dim="'+dim+'" data-i="'+i+'" aria-pressed="'+(state[dim]===i)+'">'+label+
    (count!=null?' <span class="wv-mono" style="opacity:.6">'+count+'</span>':'')+'</button>';
  const cnt = (get) => { const m={}; for(const r of D.rows) for(const k of get(r)) m[k]=(m[k]||0)+1; return m; };
  const cc = cnt(r=>r.c);
  document.getElementById('wvCancerChips').innerHTML =
    (state.cancer!==null?mk('× '+D.cancers[state.cancer], state.cancer,'cancer',null):'<span class="wv-lab">全部</span>') +
    [0,1,2,3,4].map(i=>mk(D.cancers[i], i, 'cancer', cc[i]||0)).join('');
  const sc = {}; D.rows.forEach(r=>{ if(r.s>=0) sc[r.s]=(sc[r.s]||0)+1; });
  document.getElementById('wvStageChips').innerHTML =
    (state.stage!==null?mk('× '+D.stages[state.stage], state.stage,'stage',null):'<span class="wv-lab">全部</span>') +
    D.stages.map((s,i)=>count2(s,i,sc[i])).join('');
  const ec = {}; D.rows.forEach(r=>{ if(r.e>=0) ec[r.e]=(ec[r.e]||0)+1; });
  document.getElementById('wvEvalChips').innerHTML =
    EV.map((s,i)=>mk(i===3?'未评价':s, i, 'eval', ec[i]||0)).join('');
  function count2(s,i,n){ return n?mk(s,i,'stage',n):''; }
}
root.addEventListener('click', (e)=>{
  const chip = e.target.closest('.wv-chip');
  if (!chip) return;
  if (chip.id === 'wvReset') { state.cancer=state.stage=state.eval=state.day=null; state.q=''; document.getElementById('wvQ').value=''; render(); return; }
  const dim = chip.dataset.dim, i = +chip.dataset.i;
  if (!dim) return;
  state[dim] = state[dim] === i ? null : i;
  render();
});
document.getElementById('wvQ').addEventListener('input', (e)=>{ state.q = e.target.value.trim(); render(false); });

/* ---------- 披露节奏 ---------- */
function timeline(rows){
  const box = document.getElementById('wvTime');
  if (!D.days.length) { box.innerHTML = '<div class="wv-cap">数据里没有披露日期字段。</div>'; return; }
  const W = 900, H = 120, P = {t:14,r:10,b:22,l:10};
  const n = D.days.length;
  const per = new Array(n).fill(0), lba = new Array(n).fill(0);
  rows.forEach(r=>{ if(r.y>=0){ per[r.y]++; if(r.b) lba[r.y]++; } });
  const max = Math.max(1, ...per);
  const x = i => P.l + (i / Math.max(1,n-1)) * (W-P.l-P.r);
  const y = v => H - P.b - (v/max) * (H-P.t-P.b);
  const pts = per.map((v,i)=>[x(i), y(v)]);
  const line = pts.map((p,i)=>(i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1)).join(' ');
  const area = line + ' L' + x(n-1).toFixed(1) + ' ' + (H-P.b) + ' L' + x(0).toFixed(1) + ' ' + (H-P.b) + ' Z';
  let dots = '';
  for (let i=0;i<n;i++) if (lba[i]) dots += '<circle class="wv-hit" data-day="'+i+'" cx="'+x(i)+'" cy="'+y(per[i])+'" r="'+(3+lba[i])+'" fill="#8a5cf6" opacity=".85"/>';
  const labels = D.days.map((d,i)=> i%Math.ceil(n/9)===0 ? '<text x="'+x(i)+'" y="'+(H-6)+'" font-size="10" fill="var(--wv-mute)" text-anchor="middle">'+d.slice(5)+'</text>' : '').join('');
  box.innerHTML = '<svg class="wv-svg" viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none" style="height:'+H+'px">'+
    '<defs><linearGradient id="wvGrad" x1="0" y1="0" x2="0" y2="1">'+
    '<stop offset="0%" stop-color="var(--wv-accent)" stop-opacity=".28"/><stop offset="100%" stop-color="var(--wv-accent)" stop-opacity="0"/>'+
    '</linearGradient></defs>'+
    '<path d="'+area+'" fill="url(#wvGrad)"/>'+
    '<path d="'+line+'" fill="none" stroke="var(--wv-accent)" stroke-width="1.6"/>'+dots+
    '<line id="wvCursor" x1="0" x2="0" y1="'+P.t+'" y2="'+(H-P.b)+'" stroke="var(--wv-ink)" stroke-opacity=".25" stroke-dasharray="3 3" style="display:none"/>'+
    labels+'</svg>'+
    '<div class="wv-cap" style="margin-top:2px">峰值 '+max+' 篇/天 · '+D.days[0]+' → '+D.days[n-1]+' · LBA '+rows.filter(r=>r.b).length+' 篇</div>';
  const svg = box.querySelector('svg');
  svg.addEventListener('mousemove', (e)=>{
    const rect = svg.getBoundingClientRect();
    const rel = (e.clientX - rect.left) / rect.width * W;
    let best = 0, bd = 1e9;
    for (let i=0;i<n;i++){ const d = Math.abs(x(i)-rel); if (d<bd){bd=d;best=i;} }
    const cur = svg.querySelector('#wvCursor');
    cur.style.display=''; cur.setAttribute('x1', x(best)); cur.setAttribute('x2', x(best));
    showTip(e, '<b>'+D.days[best]+'</b><br>摘要 '+per[best]+' 篇'+(lba[best]?' · LBA '+lba[best]+' 篇':'')+'<br><span style="opacity:.6">点击只看这天</span>');
    svg.dataset.day = best;
  });
  svg.addEventListener('mouseleave', ()=>{ hideTip(); svg.querySelector('#wvCursor').style.display='none'; });
  svg.addEventListener('click', ()=>{ const d = +svg.dataset.day; state.day = state.day===d?null:d; render(); });
}

/* ---------- 癌种热度环 ---------- */
function ring(rows){
  const box = document.getElementById('wvRing');
  const cnt = new Map(), pos = new Map();
  rows.forEach(r=>r.c.forEach(c=>{ cnt.set(c,(cnt.get(c)||0)+1); if(r.e===0) pos.set(c,(pos.get(c)||0)+1); }));
  const items = [...cnt.entries()].sort((a,b)=>b[1]-a[1]).slice(0,14);
  if (!items.length){ box.innerHTML='<div class="wv-cap">当前筛选下没有可展示的癌种。</div>'; return; }
  const S = 340, R = 122, r0 = 84, cx = S/2, cy = S/2;
  const total = items.reduce((s,[,v])=>s+v,0);
  let a0 = -Math.PI/2, out = '';
  const arc = (a,b,ri,ro) => {
    const p = (rad,ang)=>[cx+Math.cos(ang)*rad, cy+Math.sin(ang)*rad];
    const [x1,y1]=p(ro,a), [x2,y2]=p(ro,b), [x3,y3]=p(ri,b), [x4,y4]=p(ri,a);
    const big = (b-a) > Math.PI ? 1 : 0;
    return 'M'+x1+' '+y1+' A'+ro+' '+ro+' 0 '+big+' 1 '+x2+' '+y2+' L'+x3+' '+y3+' A'+ri+' '+ri+' 0 '+big+' 0 '+x4+' '+y4+' Z';
  };
  items.forEach(([c,v],k)=>{
    const share = v/total, a1 = a0 + share*Math.PI*2 - 0.012;
    const pr = (pos.get(c)||0)/v;
    const col = pr>.5 ? 'var(--wv-pos)' : pr>.25 ? 'color-mix(in srgb,var(--wv-pos) 62%,var(--wv-none))' : 'var(--wv-none)';
    const on = state.cancer===c;
    out += '<path class="wv-hit" data-c="'+c+'" d="'+arc(a0,a1,r0,R)+'" fill="'+col+'" opacity="'+(state.cancer===null||on?1:.28)+
      '" stroke="var(--wv-bg)" stroke-width="1" style="transition:.18s;'+(on?'filter:drop-shadow(0 0 8px var(--wv-pos))':'')+'"/>';
    if (share > 0.045){
      const mid = (a0+a1)/2, [lx,ly] = [cx+Math.cos(mid)*(R+15), cy+Math.sin(mid)*(R+15)];
      out += '<text x="'+lx+'" y="'+ly+'" font-size="10.5" fill="var(--wv-mute)" text-anchor="'+(Math.cos(mid)>0.15?'start':Math.cos(mid)<-0.15?'end':'middle')+'" dominant-baseline="middle" pointer-events="none">'+D.cancers[c]+'</text>';
    }
    a0 = a1 + 0.012;
  });
  out += '<text x="'+cx+'" y="'+(cy-4)+'" text-anchor="middle" font-size="24" font-weight="600" class="wv-mono" fill="var(--wv-ink)">'+total+'</text>';
  out += '<text x="'+cx+'" y="'+(cy+16)+'" text-anchor="middle" font-size="11" fill="var(--wv-mute)">癌种标注次数</text>';
  box.innerHTML = '<svg class="wv-svg" viewBox="0 0 '+S+' '+S+'" style="height:300px">'+out+'</svg>';
  box.querySelectorAll('path[data-c]').forEach(p=>{
    p.addEventListener('mousemove',(e)=>{ const c=+p.dataset.c; const v=cnt.get(c), pr=((pos.get(c)||0)/v*100).toFixed(0);
      showTip(e,'<b>'+D.cancers[c]+'</b><br>摘要 '+v+' 篇 · 积极 '+pr+'%'); });
    p.addEventListener('mouseleave',hideTip);
    p.addEventListener('click',()=>{ const c=+p.dataset.c; state.cancer = state.cancer===c?null:c; render(); });
  });
}

/* ---------- 药物星座 ---------- */
function scatter(rows){
  const box = document.getElementById('wvScatter');
  const agg = new Map();
  const stageWeight = (s) => ({'早期':0.6,'I期':1,'II期':2,'III期':3,'IV期':4,'晚期':4,'局部晚期':3,'广泛期':4})[s] ?? null;
  rows.forEach(r=>{
    r.d.forEach(d=>{
      const a = agg.get(d) || {n:0,pos:0,st:[],co:''};
      a.n++; if (r.e===0) a.pos++;
      if (r.s>=0) { const w = stageWeight(D.stages[r.s]); if (w) a.st.push(w); }
      if (!a.co && r.co) a.co = r.co;
      agg.set(d,a);
    });
  });
  const items = [...agg.entries()].map(([d,a])=>({d, n:a.n, pr:a.pos/a.n, st:a.st.length? a.st.reduce((x,y)=>x+y,0)/a.st.length : 0, co:a.co}))
    .sort((a,b)=>b.n-a.n).slice(0,26);
  // 同一阶段上的点做垂直/水平微抖动，避免完全重叠
  items.forEach((it,i)=>{ it.jx = ((i*37)%11-5)*1.6; it.jy = ((i*53)%9-4)*1.2; });
  if (!items.length){ box.innerHTML='<div class="wv-cap">当前筛选下没有可展示的药物。</div>'; return; }
  const W=560,H=300,P={t:14,r:16,b:34,l:38};
  const maxN=Math.max(...items.map(i=>i.n)), maxS=Math.max(4,...items.map(i=>i.st));
  const x=v=>P.l+(v/maxS)*(W-P.l-P.r), y=v=>H-P.b-(Math.log10(v+1)/Math.log10(maxN+1))*(H-P.t-P.b);
  const r=v=>6+Math.sqrt(v/maxN)*20;
  let out='';
  // 网格
  for (let g=0; g<=4; g++){ const gy=y(Math.pow(maxN+1, g/4)-1); out+='<line x1="'+P.l+'" x2="'+(W-P.r)+'" y1="'+gy+'" y2="'+gy+'" stroke="var(--wv-line)" stroke-dasharray="2 4"/>'; }
  [1,2,3,4].forEach(s=>{ out+='<text x="'+x(s)+'" y="'+(H-P.b+16)+'" font-size="10" fill="var(--wv-mute)" text-anchor="middle">'+({1:'I期',2:'II期',3:'III期',4:'晚期'})[s]+'</text>'; });
  out+='<text x="'+(W/2)+'" y="'+(H-4)+'" font-size="10.5" fill="var(--wv-mute)" text-anchor="middle">平均阶段 →</text>';
  items.forEach((it,k)=>{
    const cx=x(it.st)+ (it.jx||0), cy=y(it.n)+ (it.jy||0), rad=r(it.n);
    const col = it.pr>.6 ? 'var(--wv-pos)' : it.pr>.3 ? 'var(--wv-accent)' : 'var(--wv-stop)';
    out+='<circle class="wv-hit" data-d="'+it.d+'" cx="'+cx+'" cy="'+cy+'" r="'+rad+'" fill="'+col+'" fill-opacity=".22" stroke="'+col+'" stroke-width="1.4"/>';
    if (k<6) out+='<text x="'+(cx+rad+3)+'" y="'+(cy+3)+'" font-size="10" fill="var(--wv-mute)" pointer-events="none">'+D.drugs[it.d]+'</text>';
  });
  box.innerHTML='<svg class="wv-svg" viewBox="0 0 '+W+' '+H+'" style="height:300px">'+out+'</svg>';
  box.querySelectorAll('circle[data-d]').forEach(c=>{
    c.addEventListener('mousemove',(e)=>{ const it=items.find(z=>z.d===+c.dataset.d);
      showTip(e,'<b>'+D.drugs[it.d]+'</b><br>'+it.co+'<br>摘要 '+it.n+' 篇 · 积极 '+(it.pr*100).toFixed(0)+'%<br>平均阶段 '+it.st.toFixed(1)); });
    c.addEventListener('mouseleave',hideTip);
    c.addEventListener('click',()=>{ state.q = D.drugs[+c.dataset.d]; document.getElementById('wvQ').value=state.q; render(false); });
  });
}

/* ---------- 靶点 × 癌种 ---------- */
function matrix(rows){
  const box = document.getElementById('wvMatrix');
  const m = new Map(); const cs=new Map(), ts=new Map();
  rows.forEach(r=>r.c.forEach(c=>r.g.forEach(g=>{ const k=c+':'+g; m.set(k,(m.get(k)||0)+1); cs.set(c,(cs.get(c)||0)+1); ts.set(g,(ts.get(g)||0)+1); })));
  const C = [...cs.entries()].sort((a,b)=>b[1]-a[1]).slice(0,10).map(x=>x[0]);
  const T = [...ts.entries()].sort((a,b)=>b[1]-a[1]).slice(0,12).map(x=>x[0]);
  if (!C.length||!T.length){ box.innerHTML='<div class="wv-cap">当前筛选下不足以构成矩阵。</div>'; return; }
  const cw=78, ch=22, L=96, Tp=26;
  const W=L+cw*C.length+20, H=Tp+ch*T.length+10;
  const max=Math.max(1,...m.values());
  let out='';
  T.forEach((t,i)=>{ out+='<text x="'+(L-8)+'" y="'+(Tp+i*ch+ch/2+3.5)+'" font-size="10.5" fill="var(--wv-mute)" text-anchor="end">'+D.targets[t]+'</text>'; });
  C.forEach((c,j)=>{ out+='<text x="'+(L+j*cw+cw/2)+'" y="'+(Tp-8)+'" font-size="10.5" fill="var(--wv-mute)" text-anchor="middle">'+D.cancers[c].slice(0,7)+'</text>'; });
  T.forEach((t,i)=>C.forEach((c,j)=>{
    const v=m.get(c+':'+t)||0;
    const op = v? .10 + .80*Math.pow(v/max,.75) : 0;
    out+='<rect class="wv-hit" data-c="'+c+'" data-g="'+t+'" x="'+(L+j*cw+2)+'" y="'+(Tp+i*ch+2)+'" width="'+(cw-4)+'" height="'+(ch-4)+'" rx="4" fill="'+(v?'var(--wv-accent)':'var(--wv-line)')+'" fill-opacity="'+(v?op:.35)+'"/>';
    if (v) out+='<text x="'+(L+j*cw+cw/2)+'" y="'+(Tp+i*ch+ch/2+3.5)+'" font-size="10" text-anchor="middle" fill="'+(op>.55?'#fff':'var(--wv-ink)')+'" pointer-events="none">'+v+'</text>';
  }));
  box.innerHTML='<svg class="wv-svg" viewBox="0 0 '+W+' '+H+'" style="height:'+Math.min(340,H)+'px">'+out+'</svg>';
  box.querySelectorAll('rect[data-c]').forEach(rc=>rc.addEventListener('mousemove',(e)=>{
    const c=+rc.dataset.c, g=+rc.dataset.g, v=m.get(c+':'+g)||0;
    showTip(e,'<b>'+D.targets[g]+'</b> × <b>'+D.cancers[c]+'</b><br>'+(v? v+' 篇摘要':'该组合无摘要')+'<br><span style="opacity:.6">点击只看这个癌种</span>');
  }));
  box.querySelectorAll('rect[data-c]').forEach(rc=>rc.addEventListener('mouseleave',hideTip));
  box.querySelectorAll('rect[data-c]').forEach(rc=>rc.addEventListener('click',()=>{ const c=+rc.dataset.c; state.cancer = state.cancer===c?null:c; render(); }));
}

/* ---------- 可行动信号 ---------- */
function signals(rows){
  const score = (r) => (r.k?3:0) + (r.b?2:0) + (r.e===0?2:0) + (r.e===2?2:0) + (r.s>=0 && r.s<=2?1.5:0);
  const list = [...rows].sort((a,b)=>score(b)-score(a)).slice(0,12);
  document.getElementById('wvSignals').innerHTML = list.map((r,i)=>{
    const ev = r.e>=0 ? '<span class="wv-bdg '+(['wv-pos','wv-neg','wv-stop','wv-none'])[r.e]+'">'+(r.e===3?'未评价':EV[r.e])+'</span>' : '';
    const lba = r.b? '<span class="wv-bdg wv-lba">LBA</span>':'';
    const st = r.s>=0? '<span class="wv-bdg" style="color:var(--wv-mute)">'+D.stages[r.s]+'</span>':'';
    const ca = r.c.length? '<span class="wv-bdg" style="color:var(--wv-accent)">'+D.cancers[r.c[0]]+'</span>':'';
    const t = r.l ? '<a href="'+r.l+'" target="_blank" rel="noopener">'+r.t+'</a>' : r.t;
    return '<div class="wv-sig"><div class="wv-rk wv-mono">'+String(i+1).padStart(2,'0')+'</div><div><div class="wv-ttl">'+t+'</div>'+
      '<div style="margin-top:3px">'+ev+lba+st+ca+(r.co?'<span class="wv-bdg" style="color:var(--wv-mute)">'+r.co+'</span>':'')+'</div></div></div>';
  }).join('') || '<div class="wv-cap">没有匹配的摘要。</div>';
}

/* ---------- 列表 ---------- */
function list(rows){
  document.getElementById('wvCount').textContent = ' · '+rows.length+' 篇';
  const evName = ['积极','不佳','终止','未评价'];
  document.getElementById('wvList').innerHTML = rows.slice(0,120).map(r=>{
    const t = r.l? '<a href="'+r.l+'" target="_blank" rel="noopener" style="color:inherit">'+r.t+'</a>' : r.t;
    return '<div class="wv-row"><span class="wv-m wv-mono">'+String(r.y>=0?D.days[r.y].slice(5):'--').padEnd(5)+'</span>'+
      '<span style="flex:1">'+t+'</span><span class="wv-m">'+(r.e>=0?evName[r.e]:'')+(r.b?' · LBA':'')+'</span></div>';
  }).join('') || '<div class="wv-cap">没有匹配的摘要。</div>';
}

function render(resetScroll=true){
  const rows = M();
  kpi(rows); chips(); timeline(rows); ring(rows); scatter(rows); matrix(rows); signals(rows); list(rows);
  if (resetScroll) window.dispatchEvent(new Event('resize'));
}
render();
})();
</script>`;

if (/<(!doctype|html|head|body)/i.test(html)) throw new Error('fragment 校验失败：出现了 forbidden 文档包裹标签');
if (!html.trim().startsWith('<')) throw new Error('fragment 必须以 < 开头');
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, html);
// 仅本地预览用：补 charset，否则 http.server 默认按 latin-1 猜编码导致中文乱码
fs.writeFileSync(OUT.replace(/\.html$/, '.preview.html'), '<meta charset="utf-8">' + html);
console.log(`[interactive] ${OUT}  ${(Buffer.byteLength(html) / 1024).toFixed(0)} KB · rows=${rows.length}`);
