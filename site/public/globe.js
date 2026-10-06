// DODGE globe. Canvas 2D, no libraries.
// Modes: live (real time), replay (24 h in 60 s), focus (one pass, both
// orbits), with optional filters. Starlink motion here is two-body plus J2
// drift from the day's elements: right for a picture, not for screening.
// The screening itself runs SGP4 on the server.
(function () {
  "use strict";
  const canvas = document.getElementById("globe");
  if (!canvas) return;
  const ctx = canvas.getContext("2d", { alpha: true });
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const RE = 6378.137, MU = 398600.4418, J2 = 1.08263e-3;
  const TAU = Math.PI * 2, D2R = Math.PI / 180;
  const REPLAY_MS = 60000;
  const SIGNAL = [244, 115, 59];
  const sig = (a) => `rgba(${SIGNAL[0]},${SIGNAL[1]},${SIGNAL[2]},${a})`;

  let W = 0, H = 0, DPR = Math.min(devicePixelRatio || 1, 1.5), R = 1, cx = 0, cy = 0;
  let land = [], sats = [], replay = [], window0 = 0;
  const cam = { spin: 0, tilt: 0.32, zoom: 1, lift: 0 }, target = { spin: null, tilt: 0.32, zoom: 1, lift: 0 };
  let mode = "live", filter = null, focusEv = null, paused = reduce, dragging = null, userMoved = false;
  let replayStart = performance.now(), focusStart = performance.now(), lastFrame = 0, raf = 0, visible = true;
  let slowFrames = 0, satStride = 1;
  // Satellite positions are recomputed at about 20 Hz and cached between;
  // while the page is scrolling, the whole globe drops to about 30 fps.
  let satCache = null, satCacheAt = 0, scrolling = 0, lastDraw = 0;
  addEventListener("scroll", () => { scrolling = performance.now(); }, { passive: true });
  const callout = document.getElementById("callout");

  function layout() {
    W = canvas.clientWidth; H = canvas.clientHeight;
    canvas.width = Math.round(W * DPR); canvas.height = Math.round(H * DPR);
    const wide = W > 1000;
    R = Math.min(W, H) * (wide ? 0.38 : 0.42);
    cx = wide ? W * 0.62 : W * 0.5;
    cy = H * (wide ? 0.5 : 0.5);
  }

  const gmst = (u) => (((280.46061837 + 360.98564736629 * (u / 86400 + 2440587.5 - 2451545.0)) % 360) * D2R);

  // Earth-fixed lat/lon (rad) at radius rr (Earth radii) -> [x, y, depth] or null when behind the Earth.
  function project(lat, lon, rr) {
    const cl = Math.cos(lat);
    const a = lon + cam.spin;
    const x0 = cl * Math.cos(a), y0 = cl * Math.sin(a), z0 = Math.sin(lat);
    const ct = Math.cos(cam.tilt), st = Math.sin(cam.tilt);
    const y = y0 * ct - z0 * st, z = y0 * st + z0 * ct;
    const k = R * cam.zoom * rr;
    const sx = cx + x0 * k, sy = cy - cam.lift * H - z * k, depth = -y;
    if (depth < 0 && x0 * x0 * rr * rr + z * z * rr * rr < 1) return null;
    return [sx, sy, depth];
  }

  function kepler(e, unix) {
    const [inc, raan0, argp0, ma0, mmRevDay, ecc, ep] = e;
    const n = mmRevDay * TAU / 86400, a = Math.cbrt(MU / (n * n)), p = a * (1 - ecc * ecc);
    const i = inc * D2R, ci = Math.cos(i), dt = unix - ep;
    const k = 1.5 * n * J2 * (RE / p) * (RE / p);
    const raan = raan0 * D2R - k * ci * dt, argp = argp0 * D2R + 0.5 * k * (5 * ci * ci - 1) * dt;
    const M = (ma0 * D2R + n * dt) % TAU;
    let E = M;
    for (let it = 0; it < 3; it++) E -= (E - ecc * Math.sin(E) - M) / (1 - ecc * Math.cos(E));
    const nu = 2 * Math.atan2(Math.sqrt(1 + ecc) * Math.sin(E / 2), Math.sqrt(1 - ecc) * Math.cos(E / 2));
    const r = a * (1 - ecc * Math.cos(E)), u = argp + nu;
    const cu = Math.cos(u), su = Math.sin(u), cO = Math.cos(raan), sO = Math.sin(raan);
    const x = r * (cO * cu - sO * su * ci), y = r * (sO * cu + cO * su * ci), z = r * su * Math.sin(i);
    return [Math.asin(z / r), Math.atan2(y, x) - gmst(unix), r / RE];
  }

  function simTime(now) {
    if (mode === "replay") return window0 + (((now - replayStart) % REPLAY_MS) / REPLAY_MS) * 86400;
    if (mode === "focus" && focusEv) {
      // Loop the 8 minutes around the pass, compressed into 10 seconds.
      const t = ((now - focusStart) % 10000) / 10000;
      return focusEv.t - 360 + t * 480;
    }
    return Date.now() / 1000;
  }

  function easeCam() {
    if (dragging) return;
    if (target.spin !== null) {
      let d = (target.spin - cam.spin) % TAU;
      if (d > Math.PI) d -= TAU; if (d < -Math.PI) d += TAU;
      cam.spin += d * 0.07;
    } else if (!paused && !userMoved) {
      cam.spin += TAU / (180 * 60); // one turn in about 180 s
    }
    cam.tilt += (target.tilt - cam.tilt) * 0.07;
    cam.zoom += (target.zoom - cam.zoom) * 0.07;
    cam.lift += (target.lift - cam.lift) * 0.07;
  }

  let frozenSim = null;
  function frame(now) {
    raf = 0;
    if (now - scrolling < 200 && now - lastDraw < 32 && !dragging) { schedule(); return; }
    lastDraw = now;
    const t0 = performance.now();
    easeCam();
    const sim = paused ? (frozenSim ?? (frozenSim = simTime(now))) : (frozenSim = null, simTime(now));
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const Rz = R * cam.zoom;
    const cyl = cy - cam.lift * H;

    // Far-side Starlinks, before the Earth hides them.
    const near = [];
    if (!satCache || Math.abs(now - satCacheAt) > 50 || Math.abs(sim - satCache.sim) > 600) {
      const pos = new Float64Array(sats.length * 3);
      for (let k = 0; k < sats.length; k += satStride) {
        const ll = kepler(sats[k], sim);
        pos[k * 3] = ll[0]; pos[k * 3 + 1] = ll[1]; pos[k * 3 + 2] = ll[2];
      }
      satCache = { pos, sim }; satCacheAt = now;
    }
    const P = satCache.pos;
    for (let k = 0; k < sats.length; k += satStride) {
      if (!P[k * 3 + 2]) continue;
      const p = project(P[k * 3], P[k * 3 + 1], P[k * 3 + 2]);
      if (!p) continue;
      if (p[2] >= 0) near.push(p[0], p[1], p[2]);
      else { ctx.fillStyle = "rgba(230,238,248,0.10)"; ctx.fillRect(p[0] - 0.5, p[1] - 0.5, 1, 1); }
    }

    // Halo and disk.
    let g = ctx.createRadialGradient(cx, cyl, Rz * 0.96, cx, cyl, Rz * 1.16);
    g.addColorStop(0, "rgba(120,160,220,0.16)"); g.addColorStop(1, "rgba(120,160,220,0)");
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cyl, Rz * 1.16, 0, TAU); ctx.fill();
    g = ctx.createRadialGradient(cx - Rz * 0.4, cyl - Rz * 0.45, Rz * 0.05, cx, cyl, Rz);
    g.addColorStop(0, "#151b28"); g.addColorStop(1, "#090b10");
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cyl, Rz, 0, TAU); ctx.fill();

    // Land: four alpha buckets, one fill style each, faded toward the limb.
    const buckets = [[], [], [], []];
    for (let k = 0; k < land.length; k += 2) {
      const p = project(land[k] * D2R, land[k + 1] * D2R, 1);
      if (!p || p[2] <= 0.04) continue;
      buckets[Math.min(3, (p[2] * 4) | 0)].push(p[0], p[1]);
    }
    const ds = Math.max(1.4, 1.7 * Math.sqrt(cam.zoom));
    for (let b = 0; b < 4; b++) {
      ctx.fillStyle = `rgba(160,176,204,${0.2 + b * 0.17})`;
      const arr = buckets[b];
      for (let k = 0; k < arr.length; k += 2) ctx.fillRect(arr[k] - ds / 2, arr[k + 1] - ds / 2, ds, ds);
    }

    // Near-side Starlinks.
    const ss = cam.zoom > 1.4 ? 1.6 : 1.15;
    for (let k = 0; k < near.length; k += 3) {
      ctx.fillStyle = `rgba(230,238,248,${0.25 + near[k + 2] * 0.55})`;
      ctx.fillRect(near[k] - ss / 2, near[k + 1] - ss / 2, ss, ss);
    }

    // Approaches.
    if (mode === "focus" && focusEv) drawFocus(sim);
    else drawEvents(sim);

    if (!paused || dragging) schedule();
    const dt = performance.now() - t0;
    if (dt > 14) { if (++slowFrames > 50) degrade(); } else slowFrames = Math.max(0, slowFrames - 1);
    lastFrame = now;
    const clock = document.getElementById("clock");
    if (clock) clock.textContent = new Date(sim * 1000).toISOString().slice(11, 19);
  }

  function degrade() {
    slowFrames = 0;
    if (DPR > 1.5) { DPR = 1.5; layout(); } else if (satStride < 3) satStride++;
  }

  function drawEvents(sim) {
    const span = mode === "live" ? 1800 : 2400; // seconds of afterglow
    let shown = 0, lo = 0, hi = replay.length;
    while (lo < hi) { const m = (lo + hi) >> 1; if (replay[m][0] < sim - span) lo = m + 1; else hi = m; }
    for (let k = lo; k < replay.length && replay[k][0] <= sim; k++) {
      const ev = replay[k];
      if (filter && !filter(ev)) continue;
      const age = (sim - ev[0]) / (ev[3] < 1000 ? span : span * 0.35);
      if (age > 1) continue;
      const p = project(ev[1] * D2R, ev[2] * D2R, 1 + 550 / RE);
      if (!p || p[2] < 0) continue;
      const a = 1 - age;
      shown++;
      if (ev[3] < 1000) {
        ctx.strokeStyle = sig(a); ctx.lineWidth = 1.25;
        ctx.beginPath(); ctx.arc(p[0], p[1], 3 + age * 16, 0, TAU); ctx.stroke();
        ctx.fillStyle = sig(Math.min(1, a + 0.2)); ctx.fillRect(p[0] - 1.5, p[1] - 1.5, 3, 3);
      } else {
        ctx.fillStyle = sig(a * 0.85); ctx.fillRect(p[0] - 1.1, p[1] - 1.1, 2.2, 2.2);
      }
    }
    const tl = document.getElementById("tally");
    if (tl) {
      let n = 0;
      for (let k = 0; k < replay.length && replay[k][0] <= sim; k++) if (!filter || filter(replay[k])) n++;
      tl.textContent = n.toLocaleString("en-US");
    }
    if (callout) callout.style.opacity = "0";
  }

  function track(el, t0, t1, step) {
    const pts = [];
    for (let t = t0; t <= t1; t += step) {
      const ll = kepler(el, t);
      pts.push(project(ll[0], ll[1], ll[2]));
    }
    return pts;
  }

  function strokeTrack(pts, color, width) {
    ctx.strokeStyle = color; ctx.lineWidth = width;
    ctx.beginPath();
    let pen = false;
    for (const p of pts) {
      if (!p || p[2] < 0) { pen = false; continue; }
      if (pen) ctx.lineTo(p[0], p[1]); else { ctx.moveTo(p[0], p[1]); pen = true; }
    }
    ctx.stroke();
  }

  function drawFocus(sim) {
    const e = focusEv;
    strokeTrack(track(e.a, e.t - 1500, e.t + 600, 15), "rgba(230,238,248,0.55)", 1.2);
    strokeTrack(track(e.b, e.t - 1500, e.t + 600, 15), sig(0.8), 1.2);
    const pa = (() => { const l = kepler(e.a, sim); return project(l[0], l[1], l[2]); })();
    const pb = (() => { const l = kepler(e.b, sim); return project(l[0], l[1], l[2]); })();
    if (pa && pa[2] >= 0) { ctx.fillStyle = "#e6eef8"; ctx.beginPath(); ctx.arc(pa[0], pa[1], 3.2, 0, TAU); ctx.fill(); }
    if (pb && pb[2] >= 0) { ctx.fillStyle = sig(1); ctx.beginPath(); ctx.arc(pb[0], pb[1], 3.2, 0, TAU); ctx.fill(); }
    const at = project(e.lat * D2R, e.lon * D2R, 1 + e.alt / RE);
    const dt = sim - e.t;
    if (at && at[2] >= 0) {
      const ring = Math.abs(dt) < 20 ? 1 : 0.35;
      ctx.strokeStyle = sig(ring); ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.arc(at[0], at[1], 10 + (Math.abs(dt) < 20 ? (20 - Math.abs(dt)) : 0), 0, TAU); ctx.stroke();
      if (callout) {
        callout.style.opacity = "1";
        callout.style.left = at[0] + "px"; callout.style.top = at[1] + "px";
        callout.classList.toggle("above", W < 700);
        callout.classList.toggle("flip", W >= 700 && at[0] > W - 280);
        const s = Math.abs(Math.round(dt)), mm = String(Math.floor(s / 60)).padStart(2, "0"), sc = String(s % 60).padStart(2, "0");
        window.dodgeSetHTML(callout, `${dt < 0 ? "T-" : "T+"}${mm}:${sc} &nbsp;·&nbsp; predicted miss <b>${e.missLabel}</b><br>${e.label}`);
      }
    } else if (callout) callout.style.opacity = "0";
  }

  function schedule() { if (!raf && visible) raf = requestAnimationFrame(frame); }

  // Interaction: drag to rotate.
  canvas.addEventListener("pointerdown", (e) => { dragging = { x: e.clientX, y: e.clientY, spin: cam.spin, tilt: cam.tilt }; target.spin = null; userMoved = true; canvas.setPointerCapture(e.pointerId); schedule(); });
  canvas.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    cam.spin = dragging.spin + (e.clientX - dragging.x) * 0.006;
    cam.tilt = target.tilt = Math.max(-1.3, Math.min(1.3, dragging.tilt + (e.clientY - dragging.y) * 0.004));
    schedule();
  });
  const end = () => { dragging = null; schedule(); };
  canvas.addEventListener("pointerup", end);
  canvas.addEventListener("pointercancel", end);

  new IntersectionObserver((es) => { visible = es[0].isIntersecting; if (visible) schedule(); }).observe(canvas);
  document.addEventListener("visibilitychange", () => { visible = !document.hidden; if (visible) schedule(); });
  addEventListener("resize", () => { layout(); schedule(); });

  window.DODGE_GLOBE = {
    load(d) {
      land = d.land || []; sats = d.starlink || []; replay = (d.replay || []).slice().sort((a, b) => a[0] - b[0]);
      window0 = d.start ? Date.parse(d.start) / 1000 : (replay[0] ? replay[0][0] : Date.now() / 1000);
      // Start facing the viewer's own side of the planet.
      cam.spin = -Math.PI / 2 - ((-new Date().getTimezoneOffset() / 60) * 15) * D2R;
      layout();
      canvas.classList.add("ready");
      schedule();
      if (paused) requestAnimationFrame(frame);
    },
    setMode(m, opts = {}) {
      mode = m; filter = opts.filter || null; userMoved = false;
      if (m === "focus" && opts.event) {
        const e = opts.event;
        focusEv = e; focusStart = performance.now();
        target.spin = -Math.PI / 2 - e.lon * D2R; target.tilt = e.lat * D2R; target.zoom = W < 700 ? 1.7 : 1.9;
        target.lift = W < 700 ? 0.16 : 0;
      } else {
        focusEv = null; target.spin = null; target.tilt = 0.32; target.zoom = 1; target.lift = 0;
        if (m === "replay") replayStart = performance.now();
      }
      schedule();
    },
    setPaused(p) { paused = p; frozenSim = null; schedule(); },
    get paused() { return paused; },
    get mode() { return mode; },
  };
  layout();
})();
