import { useState, useMemo, useEffect, useCallback } from "react";
import {
  ComposedChart, Area, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, Cell,
} from "recharts";

// ── FONT + ANIMATION INJECTION ─────────────────────────────────────────────────
const injectGlobals = () => {
  if (document.getElementById("mf-font")) return;
  const lnk = document.createElement("link");
  lnk.id = "mf-font"; lnk.rel = "stylesheet";
  lnk.href = "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600&display=swap";
  document.head.appendChild(lnk);
  const s = document.createElement("style");
  s.id = "mf-css";
  s.textContent = `
    @keyframes mfIn  { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
    @keyframes mfPop { from{opacity:0;transform:scale(.94)} to{opacity:1;transform:scale(1)} }
    .mf-hover{transition:border-color .15s,box-shadow .15s,transform .15s;}
    .mf-hover:hover{transform:translateY(-1px);border-color:#94a3b8!important;box-shadow:0 4px 12px rgba(0,0,0,.07)!important;}
    .mf-btn{transition:all .15s;cursor:pointer;}
    .mf-btn:hover{background:#e2e8f0!important;color:#0f4c81!important;border-color:#94a3b8!important;}
    .mf-btn:active{transform:scale(.97);}
  `;
  document.head.appendChild(s);
};

// ── DESIGN TOKENS (LIGHT THEME) ────────────────────────────────────────────────
const T = {
  bg: "#f1f5f9", s1: "#ffffff", s2: "#f8fafc",
  b1: "#e2e8f0", b2: "#cbd5e1",
  tx: "#1e293b", tx2: "#64748b", tx3: "#94a3b8",
  gr: "#059669", gr2: "#10b981",
  rd: "#dc2626", am: "#d97706",
  bl: "#2563eb", pu: "#7c3aed",
  dm: "#f1f5f9",
};

const sCol = (s, m = 4) => {
  const r = s / m;
  return r >= .6 ? T.gr : r >= .15 ? T.gr2 : r > -.15 ? T.am : r > -.6 ? "#ea580c" : T.rd;
};

const REGIME = {
  STRONG_BULL: { lb: "강한상승 ▲▲", c: "#065f46", bg: "rgba(5,150,105,.08)" },
  MILD_BULL: { lb: "완만상승 ▲", c: "#047857", bg: "rgba(16,185,129,.07)" },
  SIDEWAYS: { lb: "횡보 ◆", c: "#92400e", bg: "rgba(217,119,6,.08)" },
  MILD_BEAR: { lb: "완만하락 ▼", c: "#c2410c", bg: "rgba(234,88,12,.07)" },
  STRONG_BEAR: { lb: "강한하락 ▼▼", c: "#991b1b", bg: "rgba(220,38,38,.08)" },
  HIGH_VOL: { lb: "고변동성 !!", c: "#1d4ed8", bg: "rgba(37,99,235,.07)" },
  SQUEEZE: { lb: "스퀴즈 ○", c: "#6d28d9", bg: "rgba(124,58,237,.07)" },
};

// ── DATA GENERATION ────────────────────────────────────────────────────────────
const genData = (n = 300) => {
  const d = []; let p = 72000, t = .0002;
  for (let i = 0; i < n; i++) {
    if (Math.random() < .03) t = (Math.random() - .47) * .004;
    const vol = p * .013, ch = p * t + (Math.random() - .5) * vol;
    const o = p, c = Math.max(p + ch, 100);
    d.push({
      o, c, h: Math.max(o, c) + Math.random() * vol * .25,
      l: Math.min(o, c) - Math.random() * vol * .25,
      v: Math.floor((7e5 + Math.random() * 3e6) * (1 + Math.abs(ch / p) * 5)),
    });
    p = c;
  }
  return d;
};
// ── Fetch Data ────────────────────────────────────────────────────────────
const getData = (n = 300) => {
  const d = []; let p = 72000, t = .0002;
  for (let i = 0; i < n; i++) {
    if (Math.random() < .03) t = (Math.random() - .47) * .004;
    const vol = p * .013, ch = p * t + (Math.random() - .5) * vol;
    const o = p, c = Math.max(p + ch, 100);
    d.push({
      o, c, h: Math.max(o, c) + Math.random() * vol * .25,
      l: Math.min(o, c) - Math.random() * vol * .25,
      v: Math.floor((7e5 + Math.random() * 3e6) * (1 + Math.abs(ch / p) * 5)),
    });
    p = c;
  }
  return d;
};

// ── MATH ───────────────────────────────────────────────────────────────────────
const ema_ = (a, k) => { const α = 2 / (k + 1); let e = null; return a.map(v => (e = e === null ? (v ?? 0) : (v ?? e) * α + e * (1 - α))); };
const sma_ = (a, k) => a.map((_, i) => i < k - 1 ? null : a.slice(i - k + 1, i + 1).reduce((s, x) => s + x, 0) / k);

// ── INDICATORS ─────────────────────────────────────────────────────────────────
function calcInd(D) {
  const Cx = D.map(d => d.c), H = D.map(d => d.h), L = D.map(d => d.l), V = D.map(d => d.v);
  const TR = Cx.map((c, i) => i === 0 ? H[i] - L[i] : Math.max(H[i] - L[i], Math.abs(H[i] - Cx[i - 1]), Math.abs(L[i] - Cx[i - 1])));
  const ATR = ema_(TR, 14), ATRP = ATR.map((a, i) => a / Cx[i] * 100);
  const BM = sma_(Cx, 20);
  const BB = BM.map((m, i) => {
    if (!m) return null;
    const sl = Cx.slice(i - 19, i + 1), std = Math.sqrt(sl.reduce((s, v) => s + (v - m) ** 2, 0) / 20);
    return { u: m + 2 * std, m, l: m - 2 * std, pb: (Cx[i] - (m - 2 * std)) / (4 * std + .001), bw: 4 * std / (m + .001) * 100 };
  });
  const E12 = ema_(Cx, 12), E26 = ema_(Cx, 26), ML = E12.map((v, i) => v - E26[i]), SL = ema_(ML, 9), HIST = ML.map((v, i) => v - SL[i]);
  const G = Cx.map((c, i) => i === 0 ? 0 : Math.max(c - Cx[i - 1], 0)), LS = Cx.map((c, i) => i === 0 ? 0 : Math.max(Cx[i - 1] - c, 0));
  const AG = ema_(G, 14), AL = ema_(LS, 14), RSI = AG.map((g, i) => AL[i] < .001 ? 100 : 100 - 100 / (1 + g / AL[i]));
  const MA5 = sma_(Cx, 5), MA20 = sma_(Cx, 20), MA60 = sma_(Cx, 60), MA120 = sma_(Cx, 120), MA200 = sma_(Cx, 200);
  let obv = 0; const OBV = Cx.map((c, i) => { if (i === 0) return 0; obv += c > Cx[i - 1] ? V[i] : c < Cx[i - 1] ? -V[i] : 0; return obv; });
  const TP = D.map(d => (d.h + d.l + d.c) / 3), RMF = TP.map((t, i) => t * V[i]);
  const MFI = TP.map((_, i) => {
    if (i < 14) return 50; let pos = 0, neg = 0;
    for (let j = i - 13; j <= i; j++) TP[j] > (TP[j - 1] ?? TP[j]) ? (pos += RMF[j]) : (neg += RMF[j]);
    return neg < 1 ? 100 : 100 - 100 / (1 + pos / neg);
  });
  let ctpv = 0, cv = 0;
  const VWAP = D.map(d => { ctpv += (d.h + d.l + d.c) / 3 * d.v; cv += d.v; return ctpv / cv; });
  return { ATRP, BB, ML, SL, HIST, RSI, MA5, MA20, MA60, MA120, MA200, OBV, MFI, VWAP };
}

// ── SIGNAL ENGINE ──────────────────────────────────────────────────────────────
function calcSig(D, I) {
  const n = D.length - 1, c = D[n].c, cp = D[n - 1]?.c ?? c;
  const chP = ((c - cp) / cp * 100).toFixed(2);

  // ATR
  const ap = I.ATRP[n] ?? 2;
  const aS = [...I.ATRP].sort((a, b) => a - b);
  const aQ = r => aS[Math.floor(aS.length * r)] ?? 2;
  const aRg = ap < aQ(.25) ? "LOW" : ap < aQ(.75) ? "NORMAL" : ap < aQ(.9) ? "HIGH" : "EXTREME";
  const aScore = { LOW: 0, NORMAL: 0, HIGH: -1, EXTREME: -2 }[aRg];

  // BB
  const bb = I.BB[n] ?? { u: c, m: c, l: c, pb: .5, bw: 3 };
  const bwSrt = I.BB.filter(Boolean).map(b => b.bw).sort((a, b) => a - b);
  const bwMin = bwSrt[Math.floor(bwSrt.length * .05)] ?? 1;
  const sq = bb.bw <= bwMin * 1.25;
  const r4 = I.BB.slice(-4).filter(Boolean).map(b => b.pb);
  const bwU = r4.length === 4 && r4.every(p => p > .85), bwD = r4.length === 4 && r4.every(p => p < .15);
  let bbS = bwU ? 3 : bwD ? -3 : sq ? 0 : bb.pb > .8 ? 1 : bb.pb < .2 ? -1 : 0;
  const bbSig = bwU ? "band_walk↑" : bwD ? "band_walk↓" : sq ? "squeeze" : bb.pb > .8 ? "상단구간" : bb.pb < .2 ? "하단구간" : "neutral";
  bbS = Math.max(-4, Math.min(4, bbS));

  // MACD
  const h0 = I.HIST[n] ?? 0, h1 = I.HIST[n - 1] ?? 0;
  let mS = (h0 > h1 ? 1 : -1) + ((I.ML[n] ?? 0) > 0 ? 1 : -1);
  let mX = "—";
  if (h1 < 0 && h0 > 0) { mX = "골든크로스"; mS += 2; } else if (h1 > 0 && h0 < 0) { mX = "데드크로스"; mS -= 2; }
  const mSt = h0 > 0 ? (h0 > h1 ? "bull↑가속" : "bull↓약화") : (Math.abs(h0) > Math.abs(h1) ? "bear↓가속" : "bear↑약화");
  const mScore = Math.max(-4, Math.min(4, mS));

  // RSI
  const rv = I.RSI[n] ?? 50, rp = I.RSI[n - 1] ?? 50;
  let rS = rv > 75 ? -2 : rv > 65 ? -1 : rv < 25 ? 2 : rv < 35 ? 1 : 0, rX = "—";
  if (rp < 50 && rv >= 50) { rS += 1; rX = "50선↑"; } else if (rp > 50 && rv <= 50) { rS -= 1; rX = "50선↓"; }
  const rSig = rv > 75 ? "과매수" : rv > 65 ? "OB존" : rv < 25 ? "과매도" : rv < 35 ? "OS존" : rv >= 55 ? "강세구간" : "약세구간";
  const rScore = Math.max(-4, Math.min(4, rS));

  // MA
  const [m5, m20, m60, m120, m200] = [I.MA5[n], I.MA20[n], I.MA60[n], I.MA120[n], I.MA200[n]];
  let mAl = "mixed";
  if (m5 && m20 && m60 && m120 && m200) {
    if (m5 > m20 && m20 > m60 && m60 > m120 && m120 > m200) mAl = "full_bull";
    else if (m5 < m20 && m20 < m60 && m60 < m120 && m120 < m200) mAl = "full_bear";
    else if (m5 > m20 && m20 > m60) mAl = "short_bull";
    else if (m5 < m20 && m20 < m60) mAl = "short_bear";
  }
  const maAS = { full_bull: 3, short_bull: 1, mixed: 0, short_bear: -1, full_bear: -3 }[mAl] ?? 0;
  const m200S = m200 ? (c > m200 ? 1 : -1) : 0;
  const sp = m20 && I.MA20[n - 5] ? ((m20 - I.MA20[n - 5]) / I.MA20[n - 5] * 100) : 0;
  const spS = sp > 1 ? 2 : sp > .3 ? 1 : sp > -.3 ? 0 : sp > -1 ? -1 : -2;
  const maScore = Math.max(-4, Math.min(4, maAS + m200S + spS));
  const d20 = m20 ? ((c - m20) / m20 * 100).toFixed(1) : "0";

  // Fibonacci
  const rc_ = D.slice(-60), fH = Math.max(...rc_.map(d => d.h)), fL = Math.min(...rc_.map(d => d.l)), fD = fH - fL;
  const fLvs = [[0, fH], [.236, fH - fD * .236], [.382, fH - fD * .382], [.5, fH - fD * .5], [.618, fH - fD * .618], [.786, fH - fD * .786], [1, fL]];
  const belowF = fLvs.filter(([, v]) => v <= c), ns = belowF[belowF.length - 1];
  const fScore = Math.max(-2, Math.min(2, ns ? (ns[0] <= .382 ? 2 : ns[0] <= .5 ? 1 : ns[0] <= .618 ? 0 : -1) : 0));

  // Volume
  const obvSl = I.OBV.slice(-20);
  const obvSlp = (obvSl[obvSl.length - 1] - obvSl[0]) / (Math.abs(obvSl[0]) || 1) * 100;
  const mfi = I.MFI[n] ?? 50;
  const p20 = D.slice(-20).map(d => d.c);
  const pMx = Math.max(...p20), pMn = Math.min(...p20), oMx = Math.max(...obvSl), oMn = Math.min(...obvSl);
  let obvDv = "—";
  if (c >= pMx * .98 && I.OBV[n] < oMx * .92) obvDv = "약세다이버전스";
  else if (c <= pMn * 1.02 && I.OBV[n] > oMn * 1.05) obvDv = "강세다이버전스";
  let vS = (obvSlp > 5 ? 2 : obvSlp > 0 ? 1 : obvSlp < -5 ? -2 : -1) + (mfi < 20 ? 1 : mfi > 80 ? -1 : 0);
  if (obvDv.includes("강세")) vS += 2; else if (obvDv.includes("약세")) vS -= 2;
  const vScore = Math.max(-4, Math.min(4, vS));

  // Regime
  const raw = (aScore * .1 + bbS * .2 + mScore * .25 + rScore * .2 + maScore * .15 + fScore * .05 + vScore * .05) / 4 * 10;
  let regime = "SIDEWAYS";
  if (aRg === "EXTREME") regime = "HIGH_VOL"; else if (sq) regime = "SQUEEZE";
  else if (mAl === "full_bull" && raw > 3) regime = "STRONG_BULL";
  else if (mAl === "full_bear" && raw < -3) regime = "STRONG_BEAR";
  else if (raw > 1) regime = "MILD_BULL"; else if (raw < -1) regime = "MILD_BEAR";

  const WTS = {
    STRONG_BULL: { atr: .05, bb: .15, macd: .30, rsi: .20, ma: .20, fib: .05, vol: .05 },
    MILD_BULL: { atr: .05, bb: .15, macd: .25, rsi: .20, ma: .20, fib: .05, vol: .10 },
    SIDEWAYS: { atr: .05, bb: .25, macd: .10, rsi: .30, ma: .10, fib: .10, vol: .10 },
    MILD_BEAR: { atr: .05, bb: .15, macd: .25, rsi: .20, ma: .20, fib: .05, vol: .10 },
    STRONG_BEAR: { atr: .05, bb: .15, macd: .30, rsi: .20, ma: .20, fib: .05, vol: .05 },
    HIGH_VOL: { atr: .30, bb: .15, macd: .10, rsi: .15, ma: .15, fib: .05, vol: .10 },
    SQUEEZE: { atr: .10, bb: .35, macd: .15, rsi: .15, ma: .10, fib: .05, vol: .10 },
  }[regime] ?? { atr: .1, bb: .15, macd: .2, rsi: .2, ma: .2, fib: .05, vol: .1 };

  const NRM = { atr: 2, bb: 4, macd: 4, rsi: 4, ma: 4, fib: 2, vol: 4 };
  const con = {
    atr: aScore / NRM.atr * WTS.atr, bb: bbS / NRM.bb * WTS.bb,
    macd: mScore / NRM.macd * WTS.macd, rsi: rScore / NRM.rsi * WTS.rsi,
    ma: maScore / NRM.ma * WTS.ma, fib: fScore / NRM.fib * WTS.fib,
    vol: vScore / NRM.vol * WTS.vol,
  };
  const comp = Math.max(-10, Math.min(10, Object.values(con).reduce((a, b) => a + b, 0) * 10));
  const action = comp >= 5 ? "STRONG BUY" : comp >= 2 ? "BUY" : comp >= 1 ? "WEAK BUY" :
    comp >= -1 ? "HOLD" : comp >= -2 ? "WEAK SELL" : comp >= -5 ? "SELL" : "STRONG SELL";

  return {
    close: c, chP, regime, comp, action, WTS,
    contrib: Object.fromEntries(Object.entries(con).map(([k, v]) => [k, parseFloat((v * 10).toFixed(3))])),
    stopPct: (ap * 2).toFixed(2), tpPct: (ap * 4).toFixed(2),
    posSize: comp >= 5 ? "80%" : comp >= 2 ? "60%" : comp >= 1 ? "30%" : "0%",
    indicators: {
      atr: { score: aScore, max: 2, label: "ATR%", val: ap.toFixed(2) + "%", sub: aRg },
      bb: { score: bbS, max: 4, label: "BB", val: "B%=" + bb.pb.toFixed(3), sub: bbSig },
      macd: { score: mScore, max: 4, label: "MACD", val: mSt, sub: mX },
      rsi: { score: rScore, max: 4, label: "RSI", val: rv.toFixed(1), sub: rSig + " " + rX },
      ma: { score: maScore, max: 4, label: "MA", val: "이격 " + d20 + "%", sub: mAl },
      fib: { score: fScore, max: 2, label: "FIB", val: "Fib " + (ns ? ns[0] : "0.5"), sub: "ext:" + (fL + fD * 1.618).toFixed(0) },
      vol: { score: vScore, max: 4, label: "VOL", val: "MFI=" + mfi.toFixed(1), sub: obvDv },
    },
  };
}

// ── CHART DATA ────────────────────────────────────────────────────────────────
function buildChart(data, ind) {
  const W = 80, base = data.length - W;
  return data.slice(-W).map((d, i) => {
    const bb = ind.BB[base + i], m = ind.MA20[base + i];
    return { i, close: Math.round(d.c), bbU: bb ? Math.round(bb.u) : null, bbL: bb ? Math.round(bb.l) : null, ma20: m ? Math.round(m) : null };
  });
}

// ── GAUGE ─────────────────────────────────────────────────────────────────────
function Gauge({ comp }) {
  const cx = 100, cy = 85, r = 66, sw = 10;
  const pct = Math.max(0, Math.min(1, (comp + 10) / 20));
  const ang = Math.PI * (1 - pct);
  const ex = cx + r * Math.cos(ang), ey = cy - r * Math.sin(ang);
  const la = pct > .5 ? 1 : 0, col = sCol(comp, 10);
  const bg = `M${cx - r} ${cy} A${r} ${r} 0 0 1 ${cx + r} ${cy}`;
  const fp = pct > .005 ? `M${cx - r} ${cy} A${r} ${r} 0 ${la} 1 ${ex.toFixed(1)} ${ey.toFixed(1)}` : null;
  const ticks = [-10, -5, 0, 5, 10].map(v => {
    const a = Math.PI * (1 - (v + 10) / 20), ri = r - 8;
    return {
      v, x1: (cx + ri * Math.cos(a)).toFixed(1), y1: (cy - ri * Math.sin(a)).toFixed(1),
      x2: (cx + r * Math.cos(a)).toFixed(1), y2: (cy - r * Math.sin(a)).toFixed(1)
    };
  });
  return (
    <svg width="200" height="98" viewBox="0 0 200 98">
      {ticks.map(t => <line key={t.v} x1={t.x1} y1={t.y1} x2={t.x2} y2={t.y2} stroke="#e2e8f0" strokeWidth="2" />)}
      <path d={bg} fill="none" stroke="#e2e8f0" strokeWidth={sw} strokeLinecap="butt" />
      {fp && <path d={fp} fill="none" stroke={col} strokeWidth={sw} strokeLinecap="butt" opacity=".9" />}
      <circle cx={ex.toFixed(1)} cy={ey.toFixed(1)} r="6" fill={col} />
      <circle cx={ex.toFixed(1)} cy={ey.toFixed(1)} r="2.5" fill="#ffffff" />
      <text x={cx} y={cy - 2} textAnchor="middle" fill={col} fontSize="28" fontWeight="600"
        style={{ fontFamily: "'JetBrains Mono',monospace" }}>
        {comp >= 0 ? "+" : ""}{Number(comp).toFixed(1)}
      </text>
      <text x={cx - r + 5} y={cy + 17} fill={T.tx2} fontSize="9" style={{ fontFamily: "'JetBrains Mono',monospace" }}>-10</text>
      <text x={cx + r - 5} y={cy + 17} textAnchor="end" fill={T.tx2} fontSize="9" style={{ fontFamily: "'JetBrains Mono',monospace" }}>+10</text>
    </svg>
  );
}

// ── INDICATOR CARD ────────────────────────────────────────────────────────────
function IndCard({ score, max, label, val, sub, delay }) {
  const col = sCol(score, max), bw = Math.abs(score / max) * 50, bl = score >= 0 ? "50%" : `${50 - bw}%`;
  return (
    <div className="mf-hover" style={{
      background: T.s1, border: `1px solid ${T.b1}`, borderRadius: 6, padding: "10px 10px 8px",
      boxShadow: "0 1px 4px rgba(0,0,0,.04)",
      animation: `mfIn .4s ease ${delay}s both`,
    }}>
      <div style={{ fontSize: 9, color: T.tx2, letterSpacing: ".12em", marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 600, color: col, lineHeight: 1.15 }}>{score >= 0 ? "+" : ""}{score}</div>
      <div style={{ height: 3, background: T.b2, borderRadius: 2, margin: "5px 0", position: "relative" }}>
        <div style={{ position: "absolute", top: 0, height: "100%", width: `${bw}%`, left: bl, background: col, borderRadius: 2, transition: "width .6s cubic-bezier(.4,0,.2,1)" }} />
        <div style={{ position: "absolute", left: "50%", top: -2, height: 7, width: 1, background: T.b2 }} />
      </div>
      <div style={{ fontSize: 10, color: T.tx, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{val}</div>
      <div style={{ fontSize: 9, color: T.tx2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", marginTop: 1 }}>{sub}</div>
    </div>
  );
}

// ── TOOLTIPS ──────────────────────────────────────────────────────────────────
const PTip = ({ active, payload }) => !active || !payload?.length ? null : (
  <div style={{ background: "#ffffff", border: `1px solid #e2e8f0`, borderRadius: 5, padding: "5px 9px", fontSize: 9, fontFamily: "'JetBrains Mono',monospace", boxShadow: "0 4px 12px rgba(0,0,0,.08)" }}>
    {payload.map(p => p.value != null && <div key={p.name} style={{ color: p.color || T.tx, marginBottom: 1 }}>{p.name}: {p.value?.toLocaleString("ko-KR")}</div>)}
  </div>
);
const CTip = ({ active, payload }) => !active || !payload?.length ? null : (
  <div style={{ background: "#ffffff", border: `1px solid #e2e8f0`, borderRadius: 5, padding: "5px 9px", fontSize: 10, color: sCol(payload[0]?.value ?? 0, 3), boxShadow: "0 4px 12px rgba(0,0,0,.08)" }}>
    {(payload[0]?.value ?? 0) >= 0 ? "+" : ""}{(payload[0]?.value ?? 0).toFixed(3)}
  </div>
);

// ── MAIN COMPONENT ─────────────────────────────────────────────────────────────
export default function MultiFactorDashboard() {
  useEffect(() => { injectGlobals(); }, []);

  const [data, setData] = useState(() => getData(300));
  const [tick, setTick] = useState(0);
  const [ticker, setTicker] = useState("005930");

  const ind = useMemo(() => calcInd(data), [data]);
  const sig = useMemo(() => calcSig(data, ind), [data, ind]);
  const cdata = useMemo(() => buildChart(data, ind), [data, ind]);

  const refresh = useCallback(() => { setData(getData(300)); setTick(t => t + 1); }, []);

  const { close, chP, regime, comp, action, WTS, contrib, stopPct, tpPct, posSize, indicators } = sig;
  const rc = REGIME[regime] ?? REGIME.SIDEWAYS;
  const col = sCol(comp, 10), isPos = comp >= 0;

  const yVals = cdata.flatMap(d => [d.close, d.bbU, d.bbL].filter(Boolean));
  const yMin = Math.floor(Math.min(...yVals) * .998 / 100) * 100;
  const yMax = Math.ceil(Math.max(...yVals) * 1.002 / 100) * 100;

  const CK = ["atr", "bb", "macd", "rsi", "ma", "fib", "vol"];
  const CL = ["ATR%", "BB", "MACD", "RSI", "MA", "FIB", "VOL"];
  const cdata2 = CK.map((k, i) => ({ n: CL[i], v: contrib[k], fill: contrib[k] > 0 ? T.gr : contrib[k] < 0 ? T.rd : T.am }));

  const wCfg = [
    { k: "atr", l: "ATR%", c: "#3b82f6" }, { k: "bb", l: "BB", c: "#2563eb" },
    { k: "macd", l: "MACD", c: "#7c3aed" }, { k: "rsi", l: "RSI", c: "#d97706" },
    { k: "ma", l: "MA", c: "#059669" }, { k: "fib", l: "FIB", c: "#ea580c" },
    { k: "vol", l: "VOL", c: "#db2777" },
  ];

  const bgGrid = {
    backgroundImage: `linear-gradient(#e2e8f066 1px,transparent 1px),linear-gradient(90deg,#e2e8f066 1px,transparent 1px)`,
    backgroundSize: "24px 24px",
  };

  return (
    <div style={{ fontFamily: "'Plus Jakarta Sans','JetBrains Mono',monospace", background: T.bg, minHeight: "100vh", padding: 16, color: T.tx, ...bgGrid }}>

      {/* HEADER */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14, flexWrap: "wrap" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3 }}>
            <div style={{ width: "1.5em", height: "1.5em", flexShrink: 0 }}>
              <svg viewBox="0 0 48 48" fill="none" version="1.1" xmlns="http://www.w3.org/2000/svg" desc="Created with imagetracer.js version 1.2.6">
                <path fill="rgb(0,0,0)" stroke="rgb(0,0,0)" stroke-width="1" opacity="0" d="M 0 0 L 48 0 L 48 48 L 0 48 L 0 0 Z M 23 3 L 19 5 L 10 14 L 9 21 L 22 29 Q 22 33 20 33 L 19 32 Q 18 28 15 29 Q 12 30 13 34 L 17 36 Q 15 37 16 42 L 20 44 L 27 42 L 36 33 L 37 30 L 36 25 Q 28 23 23 18 L 30 10 L 29 5 Q 28 2 23 3 Z M 29 12 L 27 14 Q 26 18 30 18 L 32 17 Q 34 18 33 14 Q 32 11 29 12 Z "></path>
                <path fill="rgb(42,194,238)" stroke="rgb(42,194,238)" stroke-width="1" opacity="0.8274509803921568" d="M 22.5 3 Q 27.8 1.8 29 4.5 L 30 9.5 L 22 16.5 L 24 13.5 Q 23 11 18.5 12 L 13.5 18 L 10.5 17 L 10 20.5 L 16 24.5 L 14.5 24 L 9 20.5 L 10 13.5 L 18.5 5 L 22.5 3 Z "></path>
                <path fill="rgb(42,194,238)" stroke="rgb(42,194,238)" stroke-width="1" opacity="0.8274509803921568" d="M 18.5 31 L 19 33.5 L 17 34.5 L 18.5 31 Z "></path>
                <path fill="rgb(33,71,218)" stroke="rgb(33,71,218)" stroke-width="1" opacity="0.9568627450980393" d="M 18.5 12 Q 23 11 24 13.5 L 22 16.5 L 25.5 21 L 28 22.5 L 25.5 23 L 19.5 26 L 10 20.5 L 10.5 17 L 13.5 18 L 18.5 12 Z "></path>
                <path fill="rgb(33,71,218)" stroke="rgb(33,71,218)" stroke-width="1" opacity="0.9568627450980393" d="M 14 30 Q 19.6 27.8 18 33.5 L 15.5 35 Q 11.3 33.2 14 31.5 L 14 30 Z "></path>
                <path fill="rgb(147,24,200)" stroke="rgb(147,24,200)" stroke-width="1" opacity="0.9333333333333333" d="M 26.5 22 L 30.5 24 L 36 27.5 L 35.5 30 L 31.5 27 L 27.5 35 L 20.5 40 L 17 40 Q 16 36.2 18.5 35 L 22 32.5 L 23 30.5 L 21.5 27 L 20 26.5 L 26.5 22 Z "></path>
                <path fill="rgb(233,66,201)" stroke="rgb(233,66,201)" stroke-width="1" opacity="0.7607843137254902" d="M 28.5 12 Q 32.3 11.3 33 13.5 Q 34.5 17.9 31.5 17 L 29.5 18 Q 26.5 17.5 27 13.5 L 28.5 12 Z "></path>
                <path fill="rgb(233,66,201)" stroke="rgb(233,66,201)" stroke-width="1" opacity="0.7607843137254902" d="M 29.5 22 L 36 25 L 37 29.5 L 36 32.5 L 26.5 42 L 19.5 44 L 16 41.5 L 16 36.5 L 22.5 30 L 22 31.5 L 19.5 35 L 17 36.5 Q 15.3 41.8 20.5 40 L 29 33.5 L 31.5 27 L 35.5 30 L 36 27.5 L 30.5 24 L 29.5 22 Z "></path>
                <path fill="rgb(233,66,201)" stroke="rgb(233,66,201)" stroke-width="1" opacity="0.7607843137254902" d="M 18.5 25 L 19.5 27 L 18.5 25 Z "></path>
                <path fill="rgb(233,66,201)" stroke="rgb(233,66,201)" stroke-width="1" opacity="0.7607843137254902" d="M 21.5 27 L 22.5 29 L 21.5 27 Z "></path>
                <path fill="rgb(233,66,201)" stroke="rgb(233,66,201)" stroke-width="1" opacity="0.7607843137254902" d="M 14.5 29 L 13.5 31 L 14.5 29 Z "></path>
              </svg>
            </div>
            <div style={{ fontSize: 14, color: T.tx2, letterSpacing: ".2em", marginBottom: 3 }}>
              멀티 팩터 시그널 · v0.1 · 테크니컬 지표 분석
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
            <span style={{ fontSize: 24, fontWeight: 600 }}>{close.toLocaleString("ko-KR")}원</span>
            <span style={{
              fontSize: 12, padding: "2px 8px", borderRadius: 4,
              background: parseFloat(chP) > 0 ? "rgba(0,245,160,.09)" : "rgba(255,43,85,.09)",
              color: parseFloat(chP) > 0 ? T.gr : T.rd,
              border: `1px solid ${parseFloat(chP) > 0 ? "rgba(0,245,160,.18)" : "rgba(255,43,85,.18)"}`,
            }}>{parseFloat(chP) > 0 ? "+" : ""}{chP}%</span>
            <span style={{
              fontSize: 11, padding: "2px 10px", borderRadius: 4,
              background: rc.bg, color: rc.c, border: `1px solid ${rc.c}33`,
            }}>{rc.lb}</span>
          </div>
        </div>
        <div style={{ display: "flex", gap: 6, marginLeft: "auto", alignItems: "center" }}>
          <span style={{ fontSize: 10, color: T.tx2 }}>종목코드</span>
          <input value={ticker} onChange={e => setTicker(e.target.value)}
            style={{
              background: T.s1, border: `1px solid ${T.b2}`, borderRadius: 4, padding: "4px 8px",
              fontSize: 11, color: T.tx, width: 80, fontFamily: "inherit", outline: "none", boxShadow: "inset 0 1px 2px rgba(0,0,0,.04)"
            }} />
          <button className="mf-btn" onClick={refresh}
            style={{
              background: T.s1, border: `1px solid ${T.b2}`, borderRadius: 4,
              padding: "5px 12px", fontSize: 11, color: T.tx2, fontFamily: "inherit"
            }}>갱신 ↻</button>
        </div>
      </div>

      {/* ROW 1: GAUGE + ACTION + WEIGHTS */}
      <div style={{ display: "grid", gridTemplateColumns: "200px 1fr 194px", gap: 10, marginBottom: 10 }}>

        {/* Gauge */}
        <div style={{
          background: T.s1, border: `1px solid ${T.b1}`, borderRadius: 8, padding: "12px 6px 8px",
          display: "flex", flexDirection: "column", alignItems: "center", animation: "mfIn .4s ease both",
          boxShadow: "0 1px 6px rgba(0,0,0,.05)"
        }}>
          <div style={{ fontSize: 9, color: T.tx2, letterSpacing: ".12em", marginBottom: 2 }}>복합 스코어</div>
          <Gauge comp={comp} key={tick} />
          <div style={{ fontSize: 9, color: T.tx3 }}>범위  -10 ~ +10</div>
        </div>

        {/* Action */}
        <div style={{
          background: T.s1, border: `1px solid ${T.b1}`, borderRadius: 8, padding: "12px 14px",
          display: "flex", flexDirection: "column", gap: 8, animation: "mfIn .4s ease .05s both",
          boxShadow: "0 1px 6px rgba(0,0,0,.05)"
        }}>
          <div style={{ fontSize: 9, color: T.tx2, letterSpacing: ".12em" }}>권장 액션</div>
          <div style={{
            fontSize: 22, fontWeight: 600, padding: "5px 16px", borderRadius: 5, alignSelf: "flex-start",
            color: comp >= 2 ? T.gr : comp <= -2 ? T.rd : T.am,
            background: comp >= 2 ? "rgba(5,150,105,.08)" : comp <= -2 ? "rgba(220,38,38,.08)" : "rgba(217,119,6,.08)",
            border: `1px solid ${comp >= 2 ? "rgba(5,150,105,.20)" : comp <= -2 ? "rgba(220,38,38,.20)" : "rgba(217,119,6,.20)"}`,
          }}>{action}</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
            {[{ l: "손절", v: `-${stopPct}%`, c: T.rd }, { l: "목표가", v: `+${tpPct}%`, c: T.gr }, { l: "포지션", v: posSize, c: col }].map(x => (
              <div key={x.l} style={{ background: T.dm, borderRadius: 5, padding: "7px 10px", textAlign: "center", border: `1px solid ${T.b1}` }}>
                <div style={{ fontSize: 9, color: T.tx2, marginBottom: 3 }}>{x.l}</div>
                <div style={{ fontSize: 15, fontWeight: 600, color: x.c }}>{x.v}</div>
              </div>
            ))}
          </div>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
              <span style={{ fontSize: 9, color: T.tx2 }}>신호 신뢰도</span>
              <span style={{ fontSize: 9, color: col }}>{Math.round(Math.abs(comp) / 10 * 100)}%</span>
            </div>
            <div style={{ height: 3, background: T.b1, borderRadius: 2 }}>
              <div style={{ height: "100%", borderRadius: 2, width: `${Math.abs(comp) / 10 * 100}%`, background: col, transition: "width .6s ease" }} />
            </div>
          </div>
        </div>

        {/* Weights */}
        <div style={{
          background: T.s1, border: `1px solid ${T.b1}`, borderRadius: 8, padding: "12px 12px",
          animation: "mfIn .4s ease .10s both", boxShadow: "0 1px 6px rgba(0,0,0,.05)"
        }}>
          <div style={{ fontSize: 9, color: T.tx2, letterSpacing: ".1em", marginBottom: 5 }}>레짐 가중치</div>
          <div style={{ fontSize: 9, color: rc.c, marginBottom: 7, fontWeight: 500 }}>{regime}</div>
          {wCfg.map(w => (
            <div key={w.k} style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 4 }}>
              <span style={{ minWidth: 30, fontSize: 9, color: T.tx2 }}>{w.l}</span>
              <div style={{ flex: 1, height: 4, background: T.b1, borderRadius: 2 }}>
                <div style={{ width: `${WTS[w.k] * 200}%`, height: "100%", background: w.c, borderRadius: 2, opacity: .85, transition: "width .4s" }} />
              </div>
              <span style={{ minWidth: 26, fontSize: 9, color: T.tx2, textAlign: "right" }}>{Math.round(WTS[w.k] * 100)}%</span>
            </div>
          ))}
        </div>
      </div>

      {/* ROW 2: 7 INDICATOR CARDS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7,minmax(0,1fr))", gap: 8, marginBottom: 10 }}>
        {Object.entries(indicators).map(([k, d], i) => (
          <IndCard key={k + tick} score={d.score} max={d.max} label={d.label}
            val={d.val} sub={d.sub} delay={.14 + i * .04} />
        ))}
      </div>

      {/* ROW 3: CHARTS */}
      <div style={{ display: "grid", gridTemplateColumns: "3fr 2fr", gap: 10 }}>

        {/* Price Chart */}
        <div style={{
          background: T.s1, border: `1px solid ${T.b1}`, borderRadius: 8, padding: "12px 14px",
          animation: "mfIn .4s ease .40s both", boxShadow: "0 1px 6px rgba(0,0,0,.05)"
        }}>
          <div style={{ fontSize: 9, color: T.tx2, letterSpacing: ".1em", marginBottom: 8, display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            가격 차트 (최근 80봉) · 볼린저밴드 + MA20
            <span style={{ display: "flex", gap: 10, marginLeft: "auto" }}>
              <span style={{ color: isPos ? T.gr : T.rd }}>— 종가</span>
              <span style={{ color: T.am, opacity: .9 }}>-- MA20</span>
              <span style={{ color: T.bl, opacity: .7 }}>□ BB밴드</span>
            </span>
          </div>
          <div style={{ background: T.bg, borderRadius: 4 }}>
            <ResponsiveContainer width="100%" height={185}>
              <ComposedChart data={cdata} margin={{ top: 4, right: 42, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="bbGrd" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={T.bl} stopOpacity=".12" />
                    <stop offset="100%" stopColor={T.bl} stopOpacity=".03" />
                  </linearGradient>
                </defs>
                <XAxis dataKey="i" hide />
                <YAxis orientation="right" domain={[yMin, yMax]}
                  tick={{ fill: T.tx3, fontSize: 9 }} tickLine={false} axisLine={false} width={40}
                  tickFormatter={v => v >= 1000 ? (v / 1000).toFixed(0) + "K" : v} />
                <Tooltip content={<PTip />} />
                <Area dataKey="bbU" type="monotone" name="BB상단" fill="url(#bbGrd)" stroke={T.bl + "66"} strokeWidth={1} dot={false} legendType="none" />
                <Area dataKey="bbL" type="monotone" name="BB하단" fill={T.bg} stroke={T.bl + "66"} strokeWidth={1} dot={false} legendType="none" />
                <Line dataKey="ma20" type="monotone" name="MA20" stroke={T.am + "cc"} strokeWidth={1.5} strokeDasharray="5 3" dot={false} />
                <Line dataKey="close" type="monotone" name="종가" stroke={isPos ? T.gr : T.rd} strokeWidth={2} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Contribution Chart */}
        <div style={{
          background: T.s1, border: `1px solid ${T.b1}`, borderRadius: 8, padding: "12px 14px",
          animation: "mfIn .4s ease .45s both", boxShadow: "0 1px 6px rgba(0,0,0,.05)"
        }}>
          <div style={{ fontSize: 9, color: T.tx2, letterSpacing: ".1em", marginBottom: 8 }}>
            팩터 기여도 (가중치 × 정규화 점수)
          </div>
          <ResponsiveContainer width="100%" height={185}>
            <BarChart data={cdata2} layout="vertical" margin={{ top: 0, right: 28, bottom: 0, left: 0 }}>
              <XAxis type="number" domain={[-3, 3]} tick={{ fill: T.tx3, fontSize: 9 }} tickLine={false}
                axisLine={{ stroke: T.b1 }} tickFormatter={v => v > 0 ? `+${v}` : v} />
              <YAxis type="category" dataKey="n" width={32} tick={{ fill: T.tx2, fontSize: 10 }} tickLine={false} axisLine={false} />
              <Tooltip content={<CTip />} />
              <ReferenceLine x={0} stroke={T.b2} strokeWidth={1} />
              <Bar dataKey="v" radius={[0, 3, 3, 0]} maxBarSize={13}>
                {cdata2.map((e, i) => <Cell key={i} fill={e.fill} opacity={.9} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* FOOTER */}
      <div style={{
        marginTop: 10, padding: "8px 14px", background: T.s1, border: `1px solid ${T.b1}`,
        borderRadius: 6, fontSize: 10, color: T.tx2, display: "flex", gap: 20, flexWrap: "wrap",
        animation: "mfIn .4s ease .50s both", boxShadow: "0 1px 4px rgba(0,0,0,.04)"
      }}>
        {[
          { l: "REGIME", v: regime, c: rc.c },
          { l: "SCORE", v: `${comp >= 0 ? "+" : ""}${Number(comp).toFixed(2)}`, c: col },
          { l: "ACTION", v: action, c: col },
          { l: "상승신호", v: `${Object.values(indicators).filter(d => d.score > 0).length}개`, c: T.gr },
          { l: "하락신호", v: `${Object.values(indicators).filter(d => d.score < 0).length}개`, c: T.rd },
          { l: "ATR%", v: `${(ind.ATRP[data.length - 1] ?? 0).toFixed(2)}%`, c: T.tx },
          { l: "RSI", v: `${(ind.RSI[data.length - 1] ?? 50).toFixed(1)}`, c: T.tx },
          { l: "MFI", v: `${(ind.MFI[data.length - 1] ?? 50).toFixed(1)}`, c: T.tx },
        ].map(x => (
          <div key={x.l} style={{ display: "flex", gap: 5, alignItems: "center" }}>
            <span style={{ color: T.tx3 }}>{x.l}</span>
            <span style={{ color: x.c, fontWeight: 500 }}>{x.v}</span>
          </div>
        ))}
      </div>
    </div >
  );
}
