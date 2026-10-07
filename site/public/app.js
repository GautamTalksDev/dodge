// DODGE page: reads the daily screen and drives the page and the globe.
(function () {
  "use strict";
  const REMOTE = "https://raw.githubusercontent.com/GautamTalksDev/dodge/data/";
  const local = /^(localhost|127\.0\.0\.1)$/.test(location.hostname);
  const BASE = local ? "/public-data/" : REMOTE;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (id) => document.getElementById(id);
  const setHTML = (el, html) => window.dodgeSetHTML(el, html);
  const fmt = (n) => (n == null ? "-" : Number(n).toLocaleString("en-US"));
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const metres = (km) => (km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(2)} km`);
  const TYPE = { Satellite: "PAY", "Rocket body": "RB", Debris: "DEB" };
  const typeTag = (t) => `<span class="tag t-${TYPE[t] || "UNK"}"><i></i>${esc(t || "Unknown")}</span>`;
  const hhmmss = (s) => { s = Math.max(0, Math.floor(s)); return [s / 3600, (s % 3600) / 60, s % 60].map((v) => String(Math.floor(v)).padStart(2, "0")).join(":"); };

  let D = null, focusEvent = null;

  async function getJSON(name) {
    const r = await fetch(BASE + name, { cache: "no-cache" });
    if (!r.ok) throw new Error(name + " " + r.status);
    return r.json();
  }

  // Count-up for big figures. The final value is set first; the animation is cosmetic.
  function tick(el, value) {
    el.textContent = fmt(value);
    if (reduce || !value) return;
    const start = performance.now(), dur = 1200;
    const step = (now) => {
      const t = Math.min(1, (now - start) / dur), e = t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
      el.textContent = fmt(Math.round(value * e));
      if (t < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  function toFocus(e) {
    return {
      t: Date.parse(e.tca) / 1000, a: e.starlink.el, b: e.other.el,
      lat: e.at[0], lon: e.at[1], alt: e.at[2],
      missLabel: metres(e.miss_km),
      label: `${esc(e.starlink.name)} × ${esc(e.other.name)}`,
    };
  }
  const passId = (e) => `${e.starlink.id}-${e.other.id}-${Math.floor(Date.parse(e.tca) / 1000)}`;

  function header(d) {
    const s = d.stats;
    $("tm-screen").textContent = s.start.slice(0, 16).replace("T", " ");
    $("tm-star").textContent = fmt(s.starlink);
    $("tm-objs").textContent = fmt(s.others);
    $("eyebrow").textContent = `Screened ${s.start.slice(0, 10)} · next 24 hours`;
    $("gen").textContent = `Last screen ${d.generated_at.replace("T", " ").slice(0, 16)} UTC.`;
    $("fresh").textContent = `${s.start.slice(0, 16).replace("T", " ")} UTC`;
    const ageH = (Date.now() - Date.parse(d.generated_at)) / 3600000;
    if (ageH > 30) $("eyebrow").textContent = `Data is ${Math.floor(ageH)} hours old. The daily screen may have failed; numbers below are from ${s.start.slice(0, 10)}.`;
    const nextRun = () => {
      const now = new Date();
      const n = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 1, 47));
      if (n <= now) n.setUTCDate(n.getUTCDate() + 1);
      $("tm-next").textContent = hhmmss((n - now) / 1000);
    };
    nextRun(); setInterval(nextRun, 1000);
  }

  function story(d) {
    const t = d.totals;
    $("lede-n").textContent = fmt(t.under_5km);
    $("st-star").textContent = fmt(d.stats.starlink);
    $("st-5").textContent = fmt(t.under_5km);
    $("st-1").textContent = fmt(t.under_1km);
    const c = d.closest && d.closest[0];
    if (c) { focusEvent = focusEvent || c; setFocusText(focusEvent); }
    const deadRows = d.dead_hardware || [];
    $("st-dead").textContent = fmt(deadRows.reduce((a, r) => a + r.total, 0));
    const top = deadRows[0];
    if (top) $("st-dead-p").textContent = `Spent stages and fragments cannot move, so Starlink always dodges. ${top.name} owns the most of this hardware: ${fmt(top.rocket_bodies)} passes with its rocket bodies and ${fmt(top.debris)} with its debris.`;
    const own = d.by_owner || [];
    const tbd = own.find((r) => r.key === "TBD");
    if (tbd) {
      const us = (own.find((r) => r.key === "US") || {}).per_object, cn = (own.find((r) => r.key === "PRC") || {}).per_object;
      $("st-tbd").textContent = Number(tbd.per_object).toFixed(2);
      $("st-tbd-p").textContent = `Across ${fmt(tbd.objects_screened)} objects with no owner on record, against ${us} for US and ${cn} for Chinese hardware. Many are recent rideshare deployments still waiting to be identified.`;
    }
  }

  function setFocusText(e) {
    const m = e.miss_km < 1 ? [String(Math.round(e.miss_km * 1000)), "metres apart"] : [e.miss_km.toFixed(2), "km apart"];
    $("st-min").textContent = m[0]; $("st-min-u").textContent = m[1];
    setHTML($("st-min-who"), `<b>${esc(e.starlink.name)}</b> and <b>${esc(e.other.name)}</b> (${esc(e.other.owner_name || e.other.owner || "")}, ${esc((e.other.type || "").toLowerCase())}) at ${esc(e.tca.slice(11, 19))} UTC on ${esc(e.tca.slice(0, 10))}, closing at ${e.vrel_kms.toFixed(1)}&nbsp;km/s.`);
    $("st3").textContent = e === (D.closest || [])[0] ? "The closest predicted pass of the day." : "A predicted close pass.";
  }

  function figs(d) {
    const io = new IntersectionObserver((es) => es.forEach((x) => {
      if (!x.isIntersecting) return;
      io.unobserve(x.target);
      tick(x.target, Number(x.target.dataset.v));
    }), { threshold: 0.6 });
    [["f-5", d.totals.under_5km], ["f-1", d.totals.under_1km], ["f-objs", d.stats.others]].forEach(([id, v]) => {
      const el = $(id); el.dataset.v = v; el.textContent = fmt(v); io.observe(el);
    });
  }

  function nextPass(d) {
    const subkm = (d.closest || []).filter((e) => e.miss_km < 1).sort((a, b) => a.tca.localeCompare(b.tca));
    const box = $("next");
    let cur = null;
    const update = () => {
      const now = Date.now();
      cur = subkm.find((x) => Date.parse(x.tca) > now) || null;
      if (!cur) { box.hidden = true; return; }
      box.hidden = false;
      $("next-t").textContent = "T-" + hhmmss((Date.parse(cur.tca) - now) / 1000);
      $("next-who").textContent = `${cur.starlink.name} × ${cur.other.name}`;
      $("next-meta").textContent = `Predicted miss ${metres(cur.miss_km)} · ${cur.vrel_kms.toFixed(1)} km/s · ${cur.other.owner_name || cur.other.owner || ""}`;
    };
    update(); setInterval(update, 1000);
    $("next-show").addEventListener("click", () => cur && showPass(cur));
  }

  function showPass(e) {
    focusEvent = e;
    setFocusText(e);
    history.replaceState(null, "", "#pass=" + passId(e));
    document.querySelector('.step[data-mode="focus"]').scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "center" });
    if (window.DODGE_GLOBE && window.DODGE_GLOBE.ready) { window.DODGE_GLOBE.setMode("focus", { event: toFocus(e) }); $("mode-label").textContent = "Focus"; }
  }

  // Sticky story: each step decides what the globe shows.
  function apply(m) {
    const G = window.DODGE_GLOBE, label = $("mode-label");
    if (!G || !G.ready) return;
    if (m === "live") { G.setMode("live"); label.textContent = "Live"; }
    else if (m === "replay") { G.setMode("replay"); label.textContent = "Replay"; }
    else if (m === "focus" && focusEvent) { G.setMode("focus", { event: toFocus(focusEvent) }); label.textContent = "Focus"; }
    else if (m === "dead") { G.setMode("replay", { filter: (ev) => ev[4] === 1 || ev[4] === 2 }); label.textContent = "Stages and debris"; }
    else if (m === "tbd") { G.setMode("replay", { filter: (ev) => ev[5] === 1 }); label.textContent = "No owner"; }
  }
  function steps() {
    const io = new IntersectionObserver((es) => es.forEach((x) => { if (x.isIntersecting) apply(x.target.dataset.mode || "live"); }), { rootMargin: "-50% 0px -50% 0px" });
    document.querySelectorAll(".step, .hero").forEach((s) => io.observe(s));
  }

  function shareURL(e) {
    const when = `${e.tca.slice(11, 16)} UTC on ${e.tca.slice(0, 10)}`;
    const text = `${e.starlink.name} and ${e.other.name} (${e.other.owner_name || e.other.owner}, ${(e.other.type || "").toLowerCase()}) are predicted to pass ${metres(e.miss_km).replace(" ", " ")} apart at ${when}, closing at ${e.vrel_kms.toFixed(1)} km/s.`;
    const url = `https://dodge.gautamkhosla.com/#pass=${passId(e)}`;
    return `https://x.com/intent/post?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`;
  }

  function closest(d) {
    const rows = (d.closest || []).slice(0, 30);
    const tb = document.querySelector("#closest-table tbody");
    setHTML(tb, rows.map((e, i) => `<tr class="clickable" data-i="${i}" tabindex="0" aria-label="Show ${esc(e.starlink.name)} and ${esc(e.other.name)} on the globe">
        <td class="num">${esc(e.tca.slice(11, 19))}<span class="when" data-t="${Date.parse(e.tca)}">${esc(e.tca.slice(0, 10))}</span></td>
        <td>${esc(e.starlink.name)}<span class="sub">#${esc(e.starlink.id)}</span></td>
        <td>${esc(e.other.name)}<span class="sub">#${esc(e.other.id)} · ${esc(e.other.intl || "")}</span></td>
        <td>${esc(e.other.owner_name || e.other.owner || "")}</td>
        <td>${typeTag(e.other.type)}</td>
        <td class="r"><span class="miss">${metres(e.miss_km)}</span><span class="missbar" aria-hidden="true"><i data-w="${Math.round(100 * (1 - Math.log10(Math.max(e.miss_km * 1000, 10)) / Math.log10(5000)) + 25)}"></i></span></td>
        <td class="r num">${e.vrel_kms.toFixed(1)}&nbsp;km/s</td>
        <td class="r"><a class="btn" href="${esc(shareURL(e))}" target="_blank" rel="noopener" aria-label="Post this pass on X">Post</a></td></tr>`).join(""));
    tb.querySelectorAll(".missbar i").forEach((b) => { b.style.width = Math.min(100, Math.max(4, Number(b.dataset.w))) + "%"; });
    const rel = () => tb.querySelectorAll(".when").forEach((w) => {
      const d = (Number(w.dataset.t) - Date.now()) / 1000, a = Math.abs(d), h = Math.floor(a / 3600), m = Math.floor((a % 3600) / 60);
      w.textContent = (d >= 0 ? "in " : "") + (h ? `${h}h ${m}m` : `${m}m`) + (d < 0 ? " ago" : "");
    });
    rel(); setInterval(rel, 30000);
    const open = (tr) => { tb.querySelectorAll("tr").forEach((r) => r.removeAttribute("aria-selected")); tr.setAttribute("aria-selected", "true"); showPass(rows[Number(tr.dataset.i)]); };
    tb.addEventListener("click", (ev) => { if (ev.target.closest("a")) return; const tr = ev.target.closest("tr"); if (tr) open(tr); });
    tb.addEventListener("keydown", (ev) => { if (ev.key === "Enter" && ev.target.matches("tr")) open(ev.target); });
  }

  // Leaderboards with sortable columns: [label, key, kind, isBarColumn].
  const TABS = {
    owner: {
      cols: [["Owner", "name", "s"], ["Under 5 km", "under_5km", "n", true], ["Under 1 km", "under_1km", "n"], ["Share", "share", "p"], ["Objects screened", "objects_screened", "n"], ["Per object", "per_object", "f"]],
      rows: (d) => (d.by_owner || []).slice(0, 25),
    },
    fleet: {
      cols: [["Fleet", "fleet", "s"], ["Operator", "operator", "s"], ["Under 5 km", "under_5km", "n", true], ["Under 1 km", "under_1km", "n"], ["Objects screened", "objects_screened", "n"], ["Per object", "per_object", "f"], ["Publishes orbits", "public_ephemerides", "b"]],
      rows: (d) => (d.by_fleet || []).filter((r) => r.under_5km > 0),
    },
    object: {
      cols: [["Object", "name", "o"], ["Owner", "owner", "s"], ["Type", "type", "t"], ["Launched", "launched", "s"], ["Under 5 km", "under_5km", "n", true], ["Under 1 km", "under_1km", "n"]],
      rows: (d) => (d.by_object || []).slice(0, 30),
    },
    dead: {
      cols: [["Owner", "name", "s"], ["Rocket bodies", "rocket_bodies", "n"], ["Debris", "debris", "n"], ["Total passes", "total", "n", true]],
      rows: (d) => (d.dead_hardware || []).slice(0, 15),
    },
  };
  let tabKey = "owner", sortKey = null, sortDir = -1;

  function cell(kind, r, key, barMax, isBar) {
    const v = r[key];
    if (kind === "s") return esc(v);
    if (kind === "o") return `${esc(v)}<span class="sub">#${esc(r.key)} · ${esc(r.intl || "")}</span>`;
    if (kind === "t") return typeTag(v);
    if (kind === "p") return `${(v * 100).toFixed(1)}%`;
    if (kind === "pc") return v == null ? "-" : `${Math.round(v * 100)}%`;
    if (kind === "f") return v == null ? "-" : Number(v).toFixed(2);
    if (kind === "b") return v == null ? '<span class="pill">Unknown</span>' : v ? '<span class="pill yes">Publicly</span>' : '<span class="pill no">Not publicly</span>';
    const s = fmt(v);
    return isBar ? `<span class="hbar" data-w="${Math.max(2, Math.round(((v || 0) / barMax) * 100))}"></span><span class="bn">${s}</span>` : s;
  }

  function renderTab() {
    const tab = TABS[tabKey];
    const rows = tab.rows(D).slice();
    const barCol = tab.cols.find((c) => c[3]);
    const sk = sortKey || barCol[1];
    rows.sort((a, b) => {
      const x = a[sk], y = b[sk];
      if (typeof x === "string" || typeof y === "string") return sortDir * String(x ?? "").localeCompare(String(y ?? ""));
      return sortDir * ((Number(x) || 0) - (Number(y) || 0));
    });
    const max = Math.max(1, ...rows.map((r) => Number(r[barCol[1]]) || 0));
    const table = $("who-table");
    const isNum = (k) => ["n", "p", "f", "pc"].includes(k);
    setHTML(table.querySelector("thead"), "<tr><th class=\"rank-h\"><span class=\"sr\">Rank</span></th>" + tab.cols.map((c) => {
      const s = c[1] === sk ? (sortDir < 0 ? "descending" : "ascending") : "none";
      return `<th class="${isNum(c[2]) ? "r" : ""}" aria-sort="${s}"><button class="sortbtn" data-k="${c[1]}" type="button">${c[0]}${s === "none" ? "" : s === "descending" ? " ↓" : " ↑"}</button></th>`;
    }).join("") + "</tr>");
    setHTML(table.querySelector("tbody"), rows.map((r, i) => `<tr><td class="rank">${String(i + 1).padStart(2, "0")}</td>` + tab.cols.map((c) =>
      `<td class="${isNum(c[2]) ? "r num" : ""}">${cell(c[2], r, c[1], max, c[3])}</td>`).join("") + "</tr>").join(""));
    // Widths go through the CSSOM: the CSP forbids inline style attributes.
    table.querySelectorAll(".hbar").forEach((b) => { b.style.setProperty("--w", b.dataset.w + "%"); });
    table.querySelectorAll(".sortbtn").forEach((b) => b.addEventListener("click", () => {
      if (sortKey === b.dataset.k || (!sortKey && b.dataset.k === sk)) sortDir = -sortDir; else { sortKey = b.dataset.k; sortDir = -1; }
      sortKey = b.dataset.k;
      renderTab();
    }));
    document.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === tabKey)));
  }

  function sharing(d) {
    const fleets = (d.by_fleet || []).filter((f) => f.public_ephemerides != null && f.objects_screened > 0 && f.fleet !== "Starlink");
    fleets.sort((a, b) => Number(b.public_ephemerides) - Number(a.public_ephemerides) || b.objects_screened - a.objects_screened);
    const cardOf = (f) => `<div class="share"><span class="micro">${esc(f.operator)}</span><h3>${esc(f.fleet)}</h3>
      <p>${fmt(f.objects_screened)} in Starlink's altitude band · ${fmt(f.under_5km)} passes</p>
      ${f.public_ephemerides ? '<span class="pill yes">Publishes orbits publicly</span>' : '<span class="pill no">Not publicly</span>'}</div>`;
    const yes = fleets.filter((f) => f.public_ephemerides), no = fleets.filter((f) => !f.public_ephemerides);
    setHTML($("share-grid"), `<div class="share-group micro">Publish their orbits publicly · ${yes.length}</div>` + yes.map(cardOf).join("") +
      `<div class="share-group micro">Do not publish publicly · ${no.length}</div>` + no.map(cardOf).join(""));
  }

  function briefing(d) {
    const b = d.brief;
    if (!b) { $("brief").hidden = true; return; }
    $("brief-head").textContent = b.headline;
    setHTML($("brief-lines"), b.lines.map((l) => `<li>${esc(l)}</li>`).join(""));
    $("brief-post").href = `https://x.com/intent/post?text=${encodeURIComponent(b.headline + " Who is on the other side:")}&url=${encodeURIComponent("https://dodge.gautamkhosla.com/")}`;
    $("brief-copy").addEventListener("click", async () => {
      const btn = $("brief-copy");
      try { await navigator.clipboard.writeText([b.headline, ...b.lines, "https://dodge.gautamkhosla.com"].join("\n")); btn.textContent = "Copied"; }
      catch (e) { btn.textContent = "Select and copy"; }
      setTimeout(() => { btn.textContent = "Copy the brief"; }, 2000);
    });
  }

  function reveals() {
    const io = new IntersectionObserver((es) => es.forEach((x) => { if (x.isIntersecting) { x.target.classList.add("in"); io.unobserve(x.target); } }), { rootMargin: "0px 0px -8% 0px" });
    document.querySelectorAll(".rv").forEach((el) => io.observe(el));
  }

  function pauseButton() {
    const b = $("pause");
    const sync = () => {
      const p = !!(window.DODGE_GLOBE && window.DODGE_GLOBE.paused);
      b.setAttribute("aria-pressed", String(p)); b.textContent = p ? "Play" : "Pause";
      b.setAttribute("aria-label", p ? "Play the globe" : "Pause the globe");
    };
    b.addEventListener("click", () => { const G = window.DODGE_GLOBE; if (!G) return; G.setPaused(!G.paused); sync(); });
    setTimeout(sync, 0);
  }

  function rail() {
    const r = $("rail"), items = [...r.querySelectorAll("li")];
    new IntersectionObserver((es) => es.forEach((x) => r.classList.toggle("on", x.isIntersecting)), { rootMargin: "-40% 0px -40% 0px" })
      .observe(document.querySelector(".steps"));
    const io = new IntersectionObserver((es) => es.forEach((x) => {
      if (!x.isIntersecting) return;
      const i = Number(x.target.id.slice(2)) - 1;
      items.forEach((li, k) => li.classList.toggle("on", k === i));
      document.querySelectorAll(".step").forEach((s, k) => s.classList.toggle("on", k === i));
    }), { rootMargin: "-50% 0px -50% 0px" });
    document.querySelectorAll(".step").forEach((s) => io.observe(s));
  }

  function pointerLight() {
    if (!matchMedia("(hover: hover) and (pointer: fine)").matches) return;
    document.querySelectorAll(".glass").forEach((g) => g.addEventListener("pointermove", (e) => {
      const b = g.getBoundingClientRect();
      g.style.setProperty("--mx", (e.clientX - b.left) + "px"); g.style.setProperty("--my", (e.clientY - b.top) + "px");
    }));
    document.querySelectorAll(".spot").forEach((grid) => grid.addEventListener("pointermove", (e) => {
      for (const c of grid.children) {
        const b = c.getBoundingClientRect();
        c.style.setProperty("--x", (e.clientX - b.left) + "px"); c.style.setProperty("--y", (e.clientY - b.top) + "px");
      }
    }));
  }

  function citeCopy() {
    const b = $("cite-copy");
    b.addEventListener("click", async () => {
      try { await navigator.clipboard.writeText($("cite-text").textContent); b.textContent = "Copied"; }
      catch (e) { b.textContent = "Select and copy"; }
      setTimeout(() => { b.textContent = "Copy"; }, 2000);
    });
  }

  async function main() {
    reveals(); rail(); pointerLight(); citeCopy();
    pauseButton();
    try {
      D = await getJSON("latest.json");
    } catch (e) {
      $("eyebrow").textContent = "The latest screen could not be loaded. Try again in a minute.";
      return;
    }
    const m = /#pass=(\d+)-(\d+)-(\d+)/.exec(location.hash);
    if (m) focusEvent = (D.closest || []).find((e) => passId(e) === `${m[1]}-${m[2]}-${m[3]}`) || null;
    if (D.maneuvers) {
      const mv = Object.fromEntries(D.maneuvers.by_fleet.map((f) => [f.fleet, f]));
      (D.by_fleet || []).forEach((f) => { const m = mv[f.fleet]; f.maneuvering = m && m.payloads ? m.share : null; });
      TABS.fleet.cols.push([`Seen maneuvering (${D.maneuvers.window_days} d)`, "maneuvering", "pc"]);
    }
    header(D); story(D); figs(D); nextPass(D); closest(D); sharing(D); briefing(D); renderTab();
    document.body.removeAttribute("data-loading");
    pointerLight();
    document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => { tabKey = b.dataset.tab; sortKey = null; sortDir = -1; renderTab(); }));
    $("announce").textContent = `Screen loaded: ${fmt(D.totals.under_5km)} predicted passes under 5 kilometres.`;
    steps();
    try {
      const [land, star, replay] = await Promise.all([fetch("/land.json").then((r) => r.json()), getJSON("starlink.json"), getJSON("replay.json")]);
      const G = window.DODGE_GLOBE;
      if (!G) return;
      G.load({ land, starlink: star.elements, replay, start: D.stats.start });
      G.ready = true;
      if (focusEvent && m) showPass(focusEvent); else apply("live");
    } catch (e) { /* the page still works without the globe */ }
  }
  main();
})();
