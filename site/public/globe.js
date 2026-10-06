// DODGE globe: a dotted Earth, every Starlink, and a 24 h replay of the
// predicted close approaches. Canvas 2D, no libraries.
//
// Starlink positions use two-body motion plus J2 drift of the node and
// perigee from the day's published elements: right for a picture, not for
// screening (the screening itself runs SGP4 on the server).
(function () {
  "use strict";
  const canvas = document.getElementById("globe");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const RE = 6378.137, MU = 398600.4418, J2 = 1.08263e-3;
  const TAU = Math.PI * 2, D2R = Math.PI / 180;
  const LOOP_MS = 60000; // one simulated day per minute

  let W = 0, H = 0, DPR = 1, R = 1, cx = 0, cy = 0;
  let land = [], sats = [], replay = [], day0 = 0;
  let tilt = 18 * D2R, spin = 0, drag = null;
  const flashes = [];
  let lastSim = 0, tally = 0, start = performance.now();

  function resize() {
    DPR = Math.min(window.devicePixelRatio || 1, 2);
    W = canvas.clientWidth; H = canvas.clientHeight;
    canvas.width = Math.round(W * DPR); canvas.height = Math.round(H * DPR);
    const wide = W > 900;
    R = Math.min(W, H) * (wide ? 0.36 : 0.4);
    cx = wide ? W * 0.66 : W * 0.5;
    cy = wide ? H * 0.47 : H * 0.5;
  }

  function gmst(unix) {
    const d = unix / 86400 + 2440587.5 - 2451545.0;
    return ((280.46061837 + 360.98564736629 * d) % 360) * D2R;
  }

  // Earth-fixed (lat, lon) plus radius in Earth radii -> screen, or null if hidden.
  function project(lat, lon, rr) {
    const cl = Math.cos(lat), x0 = cl * Math.cos(lon + spin), y0 = cl * Math.sin(lon + spin), z0 = Math.sin(lat);
    // Rotate about the screen x axis by tilt: y is depth, z is up.
    const y = y0 * Math.cos(tilt) - z0 * Math.sin(tilt);
    const z = y0 * Math.sin(tilt) + z0 * Math.cos(tilt);
    const sx = cx + x0 * R * rr, sy = cy - z * R * rr;
    const front = -y; // depth toward the viewer
    if (front < 0) {
      // Behind: hidden if inside the Earth's disk.
      const dx = x0 * rr, dz = z * rr;
      if (dx * dx + dz * dz < 1) return null;
    }
    return [sx, sy, front];
  }

  function satLatLon(e, unix) {
    const [inc, raan0, argp0, ma0, mmRevDay, ecc, ep] = e;
    const n = mmRevDay * TAU / 86400;
    const a = Math.cbrt(MU / (n * n));
    const p = a * (1 - ecc * ecc);
    const i = inc * D2R, ci = Math.cos(i);
    const dt = unix - ep;
    const k = 1.5 * n * J2 * (RE / p) * (RE / p);
    const raan = raan0 * D2R - k * ci * dt;
    const argp = argp0 * D2R + 0.5 * k * (5 * ci * ci - 1) * dt;
    let M = (ma0 * D2R + n * dt) % TAU;
    let E = M;
    for (let it = 0; it < 4; it++) E = E - (E - ecc * Math.sin(E) - M) / (1 - ecc * Math.cos(E));
    const nu = 2 * Math.atan2(Math.sqrt(1 + ecc) * Math.sin(E / 2), Math.sqrt(1 - ecc) * Math.cos(E / 2));
    const r = a * (1 - ecc * Math.cos(E));
    const u = argp + nu;
    const cu = Math.cos(u), su = Math.sin(u), cO = Math.cos(raan), sO = Math.sin(raan);
    const x = r * (cO * cu - sO * su * ci), y = r * (sO * cu + cO * su * ci), z = r * su * Math.sin(i);
    return [Math.asin(z / r), Math.atan2(y, x) - gmst(unix), r / RE];
  }

  function draw(now) {
    const t = ((now - start) % LOOP_MS) / LOOP_MS;
    const sim = day0 + t * 86400;
    if (sim < lastSim) { tally = 0; flashes.length = 0; nextIdx = 0; }
    lastSim = sim;
    if (!drag && !reduce) spin += 0.0009;

    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    ctx.clearRect(0, 0, W, H);

    // Starlinks on the far side first, so the Earth covers them.
    const front = [];
    for (let k = 0; k < sats.length; k++) {
      const ll = satLatLon(sats[k], sim);
      const p = project(ll[0], ll[1], ll[2]);
      if (!p) continue;
      if (p[2] > 0) { front.push(p); continue; }
      ctx.fillStyle = "rgba(127,216,255,0.16)";
      ctx.fillRect(p[0] - 0.5, p[1] - 0.5, 1, 1);
    }

    // Atmosphere and disk.
    const glow = ctx.createRadialGradient(cx, cy, R * 0.9, cx, cy, R * 1.35);
    glow.addColorStop(0, "rgba(80,150,255,0.18)"); glow.addColorStop(1, "rgba(80,150,255,0)");
    ctx.fillStyle = glow; ctx.beginPath(); ctx.arc(cx, cy, R * 1.35, 0, TAU); ctx.fill();
    const disk = ctx.createRadialGradient(cx - R * 0.35, cy - R * 0.4, R * 0.1, cx, cy, R);
    disk.addColorStop(0, "#14203a"); disk.addColorStop(1, "#070b15");
    ctx.fillStyle = disk; ctx.beginPath(); ctx.arc(cx, cy, R, 0, TAU); ctx.fill();

    // Land dots.
    for (let k = 0; k < land.length; k += 2) {
      const p = project(land[k] * D2R, land[k + 1] * D2R, 1);
      if (p && p[2] > 0) {
        const s = 1 + p[2] * 1.4;
        ctx.fillStyle = `rgba(120,142,182,${0.25 + p[2] * 0.6})`;
        ctx.beginPath(); ctx.arc(p[0], p[1], s / 2, 0, TAU); ctx.fill();
      }
    }

    // Starlinks on the near side.
    ctx.fillStyle = "rgba(127,216,255,0.62)";
    for (let k = 0; k < front.length; k++) {
      const p = front[k];
      ctx.fillRect(p[0] - 0.55, p[1] - 0.55, 1.1, 1.1);
    }

    // Approaches whose time has come.
    while (nextIdx < replay.length && replay[nextIdx][0] <= sim) {
      flashes.push({ ev: replay[nextIdx], born: sim });
      nextIdx++; tally++;
    }
    for (let k = flashes.length - 1; k >= 0; k--) {
      const f = flashes[k];
      const [, lat, lon, missM] = f.ev;
      const hot = missM < 1000;
      // Passes under 1 km ring out for 40 simulated minutes; the rest glint for 12.
      const age = (sim - f.born) / (hot ? 2400 : 720);
      if (age > 1) { flashes.splice(k, 1); continue; }
      const p = project(lat * D2R, lon * D2R, 1 + 550 / RE);
      if (!p || p[2] < 0) continue;
      const a = 1 - age;
      if (hot) {
        ctx.strokeStyle = `rgba(255,59,92,${a})`;
        ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(p[0], p[1], 3 + age * 18, 0, TAU); ctx.stroke();
        ctx.fillStyle = `rgba(255,90,110,${a})`;
        ctx.beginPath(); ctx.arc(p[0], p[1], 2.2, 0, TAU); ctx.fill();
      } else {
        ctx.fillStyle = `rgba(255,138,61,${a * 0.9})`;
        ctx.beginPath(); ctx.arc(p[0], p[1], 1.6, 0, TAU); ctx.fill();
      }
    }

    const clock = document.getElementById("clock");
    if (clock) clock.textContent = new Date(sim * 1000).toISOString().slice(11, 16);
    const tl = document.getElementById("tally");
    if (tl) tl.textContent = tally.toLocaleString("en-US");
    if (!reduce) requestAnimationFrame(draw);
  }
  let nextIdx = 0;

  canvas.addEventListener("pointerdown", (e) => { drag = { x: e.clientX, y: e.clientY, spin, tilt }; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener("pointermove", (e) => {
    if (!drag) return;
    spin = drag.spin + (e.clientX - drag.x) * 0.006;
    tilt = Math.max(-1.2, Math.min(1.2, drag.tilt + (e.clientY - drag.y) * 0.004));
  });
  canvas.addEventListener("pointerup", () => { drag = null; });

  window.DODGE_GLOBE = {
    load(data) {
      land = data.land || [];
      sats = (data.starlink && data.starlink.elements) || [];
      replay = (data.replay || []).slice().sort((a, b) => a[0] - b[0]);
      day0 = data.start ? Date.parse(data.start) / 1000 : (replay.length ? replay[0][0] : Date.now() / 1000);
      nextIdx = 0; tally = 0; start = performance.now();
      resize();
      if (reduce) {
        // One still frame, halfway through the day, with every approach shown.
        start = performance.now() - LOOP_MS / 2;
        draw(performance.now());
      } else {
        requestAnimationFrame(draw);
      }
    },
  };
  window.addEventListener("resize", () => { resize(); if (reduce) draw(performance.now()); });
  resize();
})();
