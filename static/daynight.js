/* Temporal City · day / night
   ------------------------------------------------------------------
   One switch for the whole app:  AUTO · DAY · NIGHT  (remembered across pages).

   AUTO follows the hour the page is showing, with the same curve as the
   Story hero: full day 08–16, dusk 16–21, full night 21–04, dawn 04–08.
     - maps blend smoothly from the day basemap to a dark city, and open
       places light up in gold (the "city lights" heat ramp);
     - the page has a separate, continuously blended twilight theme.
   DAY / NIGHT lock the whole app to one theme, including the Story page.

   API
     TCDayNight.setHour(h)        h = 0–23, or null when no hour applies (→ day)
     TCDayNight.addMap(map, opts) opts.ownSources: sources whose layers are app data,
                                  not basemap; opts.night: [[layerId, paintProp, value | fn(dayValue)]]
     TCDayNight.mountSwitch(el)   puts the AUTO/DAY/NIGHT control into el
     window event 'tc-daynight'   {detail:{n, night, mode}} after every change
*/
(function () {
  const KEY = 'tc-daynight';
  const root = document.documentElement;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let mode = 'auto';
  try { mode = localStorage.getItem(KEY) || 'auto'; } catch (e) {}
  if (!['auto', 'day', 'night'].includes(mode)) mode = 'auto';
  let hour = null, n = 0, lastNight = null;
  const maps = [];

  function nightFactor(h) {
    if (h === null || h === undefined || isNaN(h)) return 0;
    if (h >= 8 && h <= 16) return 0;
    if (h > 16 && h < 21) return (h - 16) / 5;
    if (h >= 4 && h < 8) return 1 - (h - 4) / 4;
    return 1;
  }

  /* ---------- colour helpers (any CSS colour → rgba numbers, via a 1×1 canvas) */
  const cx = document.createElement('canvas').getContext('2d');
  const cache = new Map();
  function rgba(c) {
    if (cache.has(c)) return cache.get(c);
    cx.clearRect(0, 0, 1, 1); cx.fillStyle = '#000'; cx.fillStyle = c; cx.fillRect(0, 0, 1, 1);
    const d = cx.getImageData(0, 0, 1, 1).data;
    // keep the original alpha (getImageData premultiplies poorly for low alpha)
    const m = String(c).match(/rgba?\([^)]*,\s*([\d.]+)\s*\)$/) || String(c).match(/hsla\([^)]*,\s*([\d.]+)\s*\)$/);
    const out = [d[0], d[1], d[2], m ? +m[1] : (d[3] / 255 || 1)];
    cache.set(c, out); return out;
  }
  const isColor = (v) => typeof v === 'string' && !/^\s*\[/.test(v);
  function mix(a, b, t) {
    const A = rgba(a), B = rgba(b);
    const f = (i) => Math.round(A[i] + (B[i] - A[i]) * t);
    return `rgba(${f(0)},${f(1)},${f(2)},${(A[3] + (B[3] - A[3]) * t).toFixed(3)})`;
  }

  /* ---------- the dark city: night colours for basemap layers, by type and name */
  const BG = '#0e1423';
  function nightFor(layer, prop) {
    const id = layer.id.toLowerCase();
    if (prop === 'background-color') return BG;
    if (prop === 'fill-color') {
      if (/water|ocean|sea|river/.test(id)) return '#0a1c2d';
      if (/build/.test(id)) return '#293145';
      if (/park|wood|grass|forest|landcover|green|cemetery|pitch/.test(id)) return '#17243a';
      return '#141d2d';
    }
    if (prop === 'fill-outline-color') return '#36445b';
    if (prop === 'line-color') {
      if (/water|river|stream|canal/.test(id)) return '#1d344a';
      if (/boundary|admin/.test(id)) return '#43506a';
      if (/rail|transit/.test(id)) return '#37445a';
      if (/motorway|trunk|primary|major/.test(id)) return '#4b5870';
      return '#344157';
    }
    if (prop === 'text-color') return '#a9b4ca';
    if (prop === 'text-halo-color') return BG;
    if (prop === 'icon-opacity') return 0.35;
    return null;
  }
  const PROPS = { background: ['background-color'], fill: ['fill-color', 'fill-outline-color'], line: ['line-color'], symbol: ['text-color', 'text-halo-color', 'icon-opacity'] };

  function addMap(map, opts = {}) {
    const own = new Set(opts.ownSources || []);
    const entry = { map, rules: [], applied: new Map() };
    const style = map.getStyle();
    for (const layer of style.layers) {
      if (layer.source && own.has(layer.source)) continue;
      for (const prop of PROPS[layer.type] || []) {
        let day = map.getPaintProperty(layer.id, prop);
        if (day === undefined) { if (prop === 'icon-opacity') day = 1; else continue; }
        const night = nightFor(layer, prop);
        if (night !== null) entry.rules.push({ id: layer.id, prop, day, night });
      }
    }
    for (const [id, prop, val] of opts.night || []) {
      if (!map.getLayer(id)) continue;
      const day = map.getPaintProperty(id, prop);
      entry.rules.push({ id, prop, day, night: typeof val === 'function' ? val(day) : val });
    }
    maps.push(entry);
    applyMap(entry);
    return entry;
  }

  function valueAt(r, t) {
    if (t <= 0) return r.day;
    if (t >= 1) return r.night;
    if (isColor(r.day) && isColor(r.night)) return mix(r.day, r.night, t);
    if (typeof r.day === 'number' && typeof r.night === 'number') return r.day + (r.night - r.day) * t;
    return t >= 0.5 ? r.night : r.day;   // expressions switch at the half-way point
  }
  function applyMap(entry) {
    const t = +n.toFixed(2);
    for (const r of entry.rules) {
      const v = valueAt(r, t), key = r.id + '|' + r.prop, s = JSON.stringify(v);
      if (entry.applied.get(key) === s) continue;
      try { if (entry.map.getLayer(r.id)) entry.map.setPaintProperty(r.id, r.prop, v); entry.applied.set(key, s); } catch (e) {}
    }
  }

  /* ---------- state */
  function apply() {
    n = mode === 'day' ? 0 : mode === 'night' ? 1 : nightFactor(hour);
    if (root.dataset.tcStory !== undefined) {
      // Keep every Story surface on the same continuous day → dusk → night scale.
      // The type changes only once the surface is dark enough for pale text.
      const storyMix = (day, dusk, dark) => n <= 0.5
        ? mix(day, dusk, n * 2) : mix(dusk, dark, (n - 0.5) * 2);
      const paleType = n >= 0.75;
      root.style.setProperty('--tc-story-bg', storyMix('#f8f9fc', '#d7bbca', '#171820'));
      root.style.setProperty('--tc-story-card', storyMix('#ffffff', '#e9dce5', '#242330'));
      root.style.setProperty('--tc-story-line', storyMix('#e5e7ec', '#bca8ba', '#50475a'));
      root.style.setProperty('--tc-story-ink', paleType ? '#f8f7fc' : '#24222d');
      root.style.setProperty('--tc-story-muted', paleType ? '#dad6e4' : '#4d4654');
    }
    const twilight = n > 0 && n < 1;
    const night = n >= 1;
    root.style.setProperty('--tc-n', n.toFixed(3));
    // Smoothstep keeps the surface light enough for dark type before the
    // midpoint and dark enough for light type after it.
    root.style.setProperty('--tc-dusk-weight', (100 * n * n * (3 - 2 * n)).toFixed(1) + '%');
    root.classList.toggle('tc-twilight', twilight);
    root.classList.toggle('tc-twilight-deep', twilight && n >= 0.5);
    root.classList.toggle('tc-night', night);
    root.dataset.tcMode = mode;
    // The Story and Information pages use the effective hour, including AUTO.
    if (root.dataset.tcStory !== undefined) root.setAttribute('data-theme', night ? 'dark' : 'light');
    for (const m of maps) applyMap(m);
    document.querySelectorAll('.tc-dn button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.mode === mode)));
    document.querySelectorAll('.tc-dn').forEach((el) => { el.dataset.state = night ? 'night' : 'day'; });
    window.dispatchEvent(new CustomEvent('tc-daynight', { detail: { n, night, mode } }));
    lastNight = night;
  }
  function setHour(h) { hour = (h === null || h === undefined) ? null : +h; apply(); }
  function setMode(m) { mode = m; try { localStorage.setItem(KEY, m); } catch (e) {} apply(); }

  const SUN = '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="3.2"/><g stroke="currentColor" stroke-width="1.4" stroke-linecap="round"><path d="M8 1v1.6M8 13.4V15M1 8h1.6M13.4 8H15M3 3l1.1 1.1M11.9 11.9 13 13M3 13l1.1-1.1M11.9 4.1 13 3"/></g></svg>';
  const MOON = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M13.5 10.2A5.8 5.8 0 0 1 5.8 2.5a5.8 5.8 0 1 0 7.7 7.7z"/></svg>';
  function mountSwitch(el) {
    if (!el) return;
    // Keep the switch out of transformed or blurred headers: those create a
    // containing block and make position:fixed drift between pages.
    if (el.closest('header')) document.body.prepend(el);
    el.classList.add('tc-dn');
    el.setAttribute('role', 'group');
    el.setAttribute('aria-label', 'Day or night theme');
    el.innerHTML = `<button type="button" data-mode="auto" title="Follow the clock on the page">Auto</button>`
      + `<button type="button" data-mode="day" title="Day theme" aria-label="Day">${SUN}</button>`
      + `<button type="button" data-mode="night" title="Night theme" aria-label="Night">${MOON}</button>`;
    el.addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) setMode(b.dataset.mode); });
    apply();
  }

  /* the switch looks the same on every page, so its styles live here */
  const css = document.createElement('style');
  css.textContent = `
.tc-dn{display:inline-flex;align-items:center;gap:2px;padding:2px;border:1px solid var(--tc-line,var(--line,#e0e4da));border-radius:999px;flex:none}
.tc-dn button{display:grid;place-items:center;min-width:30px;height:28px;padding:0 9px;border:0;border-radius:999px;background:transparent;color:var(--tc-muted,var(--muted,#7c8a81));
  font:700 11px 'DM Sans',system-ui,sans-serif;letter-spacing:.06em;cursor:pointer;transition:background .25s,color .25s}
.tc-dn button svg{width:14px;height:14px;fill:currentColor}
.tc-dn button:hover{color:var(--tc-ink,var(--ink,#173c33))}
.tc-dn button[aria-pressed="true"]{background:var(--tc-ink,var(--ink,#173c33));color:var(--tc-paper,var(--paper,#f6f5ef))}
.tc-dn[data-state="night"] button[data-mode="auto"][aria-pressed="true"]{box-shadow:inset 0 0 0 1px #e9b94f}
@media (max-width:560px){.tc-dn button{min-width:26px;height:26px;padding:0 7px}}`;
  document.head.appendChild(css);

  if (!reduce) root.classList.add('tc-dn-anim');
  window.TCDayNight = { setHour, setMode, addMap, mountSwitch, nightFactor, get n() { return n; }, get mode() { return mode; } };
  apply();
})();
