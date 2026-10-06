// DODGE page: reads the daily screen and fills in the page.
(function () {
  "use strict";
  const REMOTE = "https://raw.githubusercontent.com/GautamTalksDev/dodge/data/";
  const local = /^(localhost|127\.0\.0\.1)$/.test(location.hostname);
  const BASE = local ? "/public-data/" : REMOTE;
  const $ = (id) => document.getElementById(id);
  const fmt = (n) => (n == null ? "-" : Number(n).toLocaleString("en-US"));
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const metres = (km) => (km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(2)} km`);

  async function getJSON(name) {
    const r = await fetch(BASE + name, { cache: "no-cache" });
    if (!r.ok) throw new Error(name + " " + r.status);
    return r.json();
  }

  function stats(d) {
    const t = d.totals, s = d.stats;
    $("s-5").textContent = fmt(t.under_5km);
    $("s-1").textContent = fmt(t.under_1km);
    $("s-05").textContent = fmt(t["under_0.5km"]);
    $("s-min").textContent = d.closest && d.closest.length ? metres(d.closest[0].miss_km) : "-";
    $("s-objs").textContent = fmt(s.others);
    $("s-star").textContent = fmt(s.starlink);
    $("lede-count").textContent = fmt(t.under_5km);
    const start = new Date(s.start);
    $("day-label").textContent = `Screened ${start.toISOString().slice(0, 16).replace("T", " ")} UTC, next 24 hours`;
    $("gen").textContent = `Last screen: ${d.generated_at.replace("T", " ").slice(0, 16)} UTC.`;
  }

  function findings(d) {
    const out = [];
    const t = d.totals;
    const own = d.by_owner || [];
    const typ = Object.fromEntries((d.by_type || []).map((r) => [r.key, r]));
    const pay = typ.PAY ? typ.PAY.under_5km : 0;
    out.push(`<b>${fmt(t.under_5km)}</b> predicted passes within 5 km of a Starlink satellite in the next 24 hours, <b>${fmt(t.under_1km)}</b> of them within 1 km.`);
    if (pay) out.push(`<b>${Math.round((pay / t.under_5km) * 100)}%</b> involve other satellites. Many are small spacecraft without propulsion, which cannot move out of the way, so Starlink has to.`);
    const dead = d.dead_hardware || [];
    if (dead.length) {
      const deadTotal = dead.reduce((a, r) => a + r.total, 0);
      const top = dead[0];
      out.push(`<b>${fmt(deadTotal)}</b> involve spent rocket stages and debris that nobody can steer. <b>${esc(top.name)}</b> owns the most: ${fmt(top.rocket_bodies)} passes with rocket bodies and ${fmt(top.debris)} with debris.`);
    }
    const tbd = own.find((r) => r.key === "TBD");
    if (tbd) out.push(`Objects with <b>no registered owner</b> come close ${tbd.per_object} times each, more than any major country's hardware. Many are recent rideshare deployments still waiting to be identified.`);
    const top2 = own.filter((r) => r.key !== "TBD").slice(0, 2);
    if (top2.length === 2) out.push(`Per object, <b>${esc(top2[0].name)}</b> (${top2[0].per_object}) and <b>${esc(top2[1].name)}</b> (${top2[1].per_object}) come close at similar rates. The raw totals mostly reflect how much hardware each has at Starlink's altitude.`);
    const fleets = (d.by_fleet || []).filter((f) => f.fleet !== "Starlink" && f.public_ephemerides === false && f.objects_screened > 0);
    if (fleets.length) out.push(`<b>${fleets.length}</b> fleets in Starlink's altitude band do not publish their own orbit predictions publicly, including ${fleets.slice(0, 3).map((f) => esc(f.fleet)).join(", ")}.`);
    $("findings-list").innerHTML = out.map((x) => `<li>${x}</li>`).join("");
  }

  function closest(d) {
    const rows = (d.closest || []).slice(0, 25).map((e) => {
      const hot = e.miss_km < 0.5;
      return `<tr>
        <td class="mono">${esc(e.tca.slice(5, 16).replace("T", " "))}</td>
        <td>${esc(e.starlink.name)}<span class="sub">#${esc(e.starlink.id)}</span></td>
        <td>${esc(e.other.name)}<span class="sub">#${esc(e.other.id)} · ${esc(e.other.intl || "")}</span></td>
        <td>${esc(e.other.owner_name || e.other.owner || "")}</td>
        <td>${esc(e.other.type || "")}</td>
        <td class="num"><span class="miss ${hot ? "hot" : ""}">${metres(e.miss_km)}</span></td>
        <td class="num">${e.vrel_kms.toFixed(1)} km/s</td></tr>`;
    });
    document.querySelector("#closest-table tbody").innerHTML = rows.join("");
  }

  const TABS = {
    owner: {
      head: ["Owner", "Under 5 km", "Under 1 km", "Share", "Objects screened", "Per object"],
      rows: (d) => (d.by_owner || []).slice(0, 20).map((r) => [esc(r.name), fmt(r.under_5km), fmt(r.under_1km), `${(r.share * 100).toFixed(1)}%`, fmt(r.objects_screened), r.per_object ?? "-"]),
      bar: 1,
    },
    fleet: {
      head: ["Fleet", "Operator", "Under 5 km", "Under 1 km", "Objects screened", "Per object", "Publishes orbits"],
      rows: (d) => (d.by_fleet || []).filter((r) => r.under_5km > 0).map((r) => [esc(r.fleet), esc(r.operator), fmt(r.under_5km), fmt(r.under_1km), fmt(r.objects_screened), r.per_object ?? "-",
        r.public_ephemerides == null ? '<span class="pill">unknown</span>' : r.public_ephemerides ? '<span class="pill yes">publicly</span>' : '<span class="pill no">not publicly</span>']),
      bar: 2,
    },
    object: {
      head: ["Object", "Owner", "Type", "Launched", "Under 5 km", "Under 1 km"],
      rows: (d) => (d.by_object || []).slice(0, 25).map((r) => [`${esc(r.name)}<span class="sub">#${esc(r.key)} · ${esc(r.intl || "")}</span>`, esc(r.owner), esc(r.type), esc(r.launched || ""), fmt(r.under_5km), fmt(r.under_1km)]),
      bar: 4,
    },
    dead: {
      head: ["Owner", "Rocket bodies", "Debris", "Total passes"],
      rows: (d) => (d.dead_hardware || []).slice(0, 15).map((r) => [esc(r.name), fmt(r.rocket_bodies), fmt(r.debris), fmt(r.total)]),
      bar: 3,
    },
  };

  function renderTab(d, key) {
    const tab = TABS[key];
    const table = $("who-table");
    const rows = tab.rows(d);
    const max = Math.max(1, ...rows.map((r) => Number(String(r[tab.bar]).replace(/,/g, "")) || 0));
    table.querySelector("thead").innerHTML = "<tr>" + tab.head.map((h, i) => `<th class="${i ? "num" : ""}">${h}</th>`).join("") + "</tr>";
    table.querySelector("tbody").innerHTML = rows.map((r) => "<tr>" + r.map((c, i) => {
      if (i === tab.bar) {
        const v = Number(String(c).replace(/,/g, "")) || 0;
        return `<td class="num"><span class="bar" data-w="${Math.max(2, Math.round((v / max) * 90))}"></span>${c}</td>`;
      }
      return `<td class="${i ? "num" : ""}">${c}</td>`;
    }).join("") + "</tr>").join("");
    // Widths go through the CSSOM: the CSP forbids inline style attributes.
    table.querySelectorAll(".bar").forEach((b) => { b.style.width = b.dataset.w + "px"; });
    document.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === key)));
  }

  function sharing(d) {
    const fleets = (d.by_fleet || []).filter((f) => f.public_ephemerides != null && f.objects_screened > 0);
    fleets.sort((a, b) => Number(b.public_ephemerides) - Number(a.public_ephemerides) || b.objects_screened - a.objects_screened);
    $("share-grid").innerHTML = fleets.map((f) => `<div class="share"><h3>${esc(f.fleet)}</h3><p>${esc(f.operator)} · ${fmt(f.objects_screened)} in Starlink's band</p>
      ${f.public_ephemerides ? '<span class="pill yes">Publishes orbits publicly</span>' : '<span class="pill no">Not publicly</span>'}</div>`).join("");
  }

  async function main() {
    let d;
    try {
      d = await getJSON("latest.json");
    } catch (e) {
      $("findings-list").innerHTML = '<li class="loading">The latest screen could not be loaded. Try again in a minute.</li>';
      return;
    }
    stats(d); findings(d); closest(d); sharing(d);
    renderTab(d, "owner");
    document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => renderTab(d, b.dataset.tab)));
    try {
      const [land, starlink, replay] = await Promise.all([
        fetch("/land.json").then((r) => r.json()), getJSON("starlink.json"), getJSON("replay.json"),
      ]);
      if (window.DODGE_GLOBE) window.DODGE_GLOBE.load({ land, starlink, replay, start: d.stats.start });
    } catch (e) {
      /* The page still works without the globe. */
    }
  }
  main();
})();
