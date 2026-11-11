/* Temporal City · public Collector (GitHub Pages)
   The Collector normally talks to the local Python server. GitHub Pages has no server, so this file
   answers the same API calls in the browser. It replays the pre-collected Google Places sample of the
   three case areas (docs/static/demo/data.json, built by tools/build_demo_data.py): the page starts
   empty, and adding the case areas, Discover and Retrieve fill it step by step, as in the real app.
   Other areas, AI tests and edits need the local app. Progress lives in this browser tab only. */
(function () {
  const realFetch = window.fetch.bind(window);
  const BASE = document.currentScript.src.replace(/static\/demo-api\.js.*$/, '');
  const KEY = 'tc-demo-state';
  let D = null;
  const load = () => D ? Promise.resolve(D) : realFetch(BASE + 'static/demo/data.json').then(r => r.json()).then(j => (D = j));
  const USABLE = ['verified', 'observed', 'retrieved'];
  const DAYS = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su'];
  const DAYTYPES = { weekday: [0, 1, 2, 3, 4], saturday: [5], sunday: [6], weekend: [5, 6] };
  DAYS.forEach((d, i) => DAYTYPES[d] = [i]);
  const LOCAL = 'In this public demo the Collector replays the pre-collected sample of the three case areas. Run the app on your own computer (py app.py) to do this.';

  /* ---------- state: which areas are added / discovered, which places have been retrieved */
  let st = { added: [], discovered: [], retrieved: [], settings: {} };
  try { st = Object.assign(st, JSON.parse(sessionStorage.getItem(KEY) || '{}')); } catch (e) {}
  const save = () => { try { sessionStorage.setItem(KEY, JSON.stringify(st)); } catch (e) {} };
  let job = { id: 0, kind: null, status: 'idle', total: 0, done: 0, current: '', log: [] };
  const stamp = () => new Date().toTimeString().slice(0, 8) + ' ';
  const log = m => { job.log.push(stamp() + m); };

  const json = (obj, status = 200) => new Response(JSON.stringify(obj), { status, headers: { 'Content-Type': 'application/json' } });
  const no = (msg = LOCAL, status = 403) => json({ error: msg, message: msg }, status);
  const areaPois = id => D.poiAreas[String(id)] || [];
  const visibleIds = aid => {
    const ids = new Set();
    (aid ? [+aid] : st.discovered).forEach(a => { if (st.discovered.includes(+a)) areaPois(a).forEach(i => ids.add(i)); });
    return ids;
  };
  const retrieved = new Set();
  const syncRetrieved = () => { retrieved.clear(); st.retrieved.forEach(i => retrieved.add(i)); };
  syncRetrieved();
  const poiRow = p => retrieved.has(p.id) ? p : { ...p, final_label: 'pending', hours_text: '', n_sources: 0, agreement: null, retrieved_at: null };
  const pois = aid => { const ids = visibleIds(aid); return D.pois.filter(p => ids.has(p.id)).map(poiRow); };
  const matrix = id => { if (!retrieved.has(id)) return null; const s = D.mat[id]; if (!s) return null; const m = [];
    for (let d = 0; d < 7; d++) { m.push([]); for (let h = 0; h < 24; h++) { const c = s[d * 24 + h]; m[d].push(c === '.' ? null : +c); } } return m; };
  const labelsOf = q => (q.get('labels') ? q.get('labels').split(',') : USABLE);

  function areas() {
    return D.areas.filter(a => st.added.includes(a.id)).map(a => {
      const disc = st.discovered.includes(a.id);
      if (!disc) return { ...a, n_pois: 0, discovered_at: null, discovery_stats: null };
      const rows = D.pois.filter(p => areaPois(a.id).includes(p.id)), by = {};
      rows.forEach(p => by[p.category] = (by[p.category] || 0) + 1);
      return { ...a, n_pois: rows.length, discovered_at: a.discovered_at || Date.now() / 1000,
        discovery_stats: { raw: rows.length, non_functional: 0, kept: rows.length, with_osm_hours: 0, by_category: by } };
    });
  }
  function coverage(aid) {
    const labels = ['verified', 'observed', 'retrieved', 'conflict', 'estimated', 'missing', 'pending'];
    const tab = {}; [...D.meta.categories, 'All'].forEach(c => { tab[c] = { total: 0 }; labels.forEach(l => tab[c][l] = 0); });
    for (const p of pois(aid)) for (const c of [p.category, 'All']) { tab[c][p.final_label || 'pending']++; tab[c].total++; }
    return tab;
  }
  function availability(q) {
    const labels = labelsOf(q), days = DAYTYPES[q.get('daytype')] || DAYTYPES.weekday, cats = [...D.meta.categories, 'All'];
    const total = {}, usable = {}, open = {};
    cats.forEach(c => { total[c] = 0; usable[c] = 0; open[c] = Array(24).fill(0); });
    for (const p of pois(q.get('area_id'))) {
      if (p.perm_closed) continue;
      const c = p.category; total[c]++; total.All++;
      if (!labels.includes(p.final_label)) continue;
      const m = matrix(p.id); if (!m || days.some(d => m[d][0] === null)) continue;
      usable[c]++; usable.All++;
      for (let h = 0; h < 24; h++) { const v = days.reduce((a, d) => a + m[d][h], 0) / days.length; open[c][h] += v; open.All[h] += v; }
    }
    const out = {};
    cats.forEach(c => out[c] = { total: total[c], usable: usable[c], coverage: total[c] ? +(usable[c] / total[c]).toFixed(3) : null,
      open: open[c].map(v => +v.toFixed(2)), share: open[c].map(v => usable[c] ? +(v / usable[c]).toFixed(3) : null) });
    return out;
  }
  function states(q) {
    const labels = labelsOf(q), di = Math.max(0, DAYS.indexOf(q.get('day') || 'mo')), h = +(q.get('hour') || 12);
    return pois(q.get('area_id')).map(p => {
      let s = 'nodata';
      if (labels.includes(p.final_label)) { const m = matrix(p.id); const v = m ? m[di][h] : null; s = v === 1 ? 'open' : v === 0 ? 'closed' : 'nodata'; }
      return { id: p.id, state: s };
    });
  }
  function queue(q) {
    const labels = (q.get('labels') || 'missing,pending').split(','), cat = q.get('category') || '';
    const aids = (q.get('area_ids') || '').split(',').filter(Boolean);
    const ids = new Set(aids.length ? aids.flatMap(a => [...visibleIds(a)]) : [...visibleIds()]);
    return D.pois.filter(p => ids.has(p.id)).map(poiRow).filter(p => labels.includes(p.final_label) && p.name && !p.perm_closed && (!cat || p.category === cat))
      .sort((a, b) => (a.category + a.name).localeCompare(b.category + b.name))
      .map(p => ({ id: p.id, name: p.name, category: p.category, subtype: p.subtype, address: null, label: p.final_label, lat: p.lat, lon: p.lon,
        hours_text: p.hours_text, google_url: 'https://www.google.com/search?hl=en&q=' + encodeURIComponent(p.name + ' Singapore opening hours'),
        maps_url: 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(p.name + ' ' + p.lat + ',' + p.lon) }));
  }
  function detail(id) {
    const d = D.details[id]; if (!d) return null;
    if (retrieved.has(id)) return { ...d, matrix: matrix(id) };
    return { ...d, final_label: 'pending', final_weekly: null, hours_text: '', matrix: null, sources: [], attempts: [], n_sources: 0, agreement: null, retrieved_at: null };
  }

  /* ---------- simulated jobs, paced so the progress bar and log behave like the real run */
  function runJob(kind, steps, onStep, onEnd) {
    job = { id: job.id + 1, kind, status: 'running', total: steps.length, done: 0, current: '', log: [] };
    let i = 0;
    const tick = () => {
      if (job.status !== 'running') return;
      if (i >= steps.length) { onEnd && onEnd(); job.status = 'finished'; job.current = ''; save(); return; }
      onStep(steps[i], i); i++; job.done = i; save(); setTimeout(tick, kind === 'discover' ? 700 : 120);
    };
    setTimeout(tick, 300);
  }
  function discover(ids) {
    const todo = ids.filter(a => st.added.includes(a));
    runJob('discover', todo, a => {
      const area = D.areas.find(x => x.id === a);
      job.current = area.name;
      log(`${area.name}: ${areaPois(a).length} amenities (pre-collected Google Places sample)`);
      if (!st.discovered.includes(a)) st.discovered.push(a);
    }, () => log('Done. Next: 03 Hours → Run automatic retrieval.'));
    log('Public demo: loading the case-area sample instead of querying OpenStreetMap.');
  }
  function retrieve(ids, cats) {
    const want = new Set(); ids.filter(a => st.discovered.includes(a)).forEach(a => areaPois(a).forEach(i => want.add(i)));
    const list = D.pois.filter(p => want.has(p.id) && !retrieved.has(p.id) && (!cats || !cats.length || cats.includes(p.category)));
    const chunks = []; for (let i = 0; i < list.length; i += 12) chunks.push(list.slice(i, i + 12));
    runJob('retrieve', chunks, ch => {
      ch.forEach(p => { retrieved.add(p.id); st.retrieved.push(p.id);
        log(`${p.name}: ${p.final_label === 'retrieved' ? 'Google Places → ' + (p.hours_text || 'hours').split('\n')[0] : 'no opening hours in Google Places'}`); });
      job.current = ch[ch.length - 1].name; job.total = chunks.length;
    }, () => log(`Done. ${list.filter(p => p.final_label === 'retrieved').length} with hours, ${list.filter(p => p.final_label !== 'retrieved').length} missing.`));
    job.log.unshift(stamp() + `Public demo: replaying stored Google Places results for ${list.length} places.`);
  }

  async function answer(url, opt) {
    await load();
    const u = new URL(url, location.href), q = u.searchParams, path = u.pathname.replace(/^.*\/api\//, '');
    const method = (opt.method || 'GET').toUpperCase();
    let body = {}; try { body = opt.body ? JSON.parse(opt.body) : {}; } catch (e) {}
    if (method === 'GET') {
      if (path === 'meta') return json({ ...D.meta, demo: false });
      if (path === 'settings') return json({ ...D.settings, ...st.settings });
      if (path === 'job') return json(job);
      if (path === 'areas') return json(areas());
      if (path === 'pois') return json(pois(q.get('area_id')));
      if (path.startsWith('pois/')) { const d = detail(decodeURIComponent(path.slice(5))); return d ? json(d) : json({ error: 'not found' }, 404); }
      if (path === 'coverage') return json(coverage(q.get('area_id')));
      if (path === 'validation') return json(D.validation);
      if (path === 'audit_sample') return json(D.auditSample.filter(r => retrieved.has(r.poi_id || r.id)));
      if (path === 'queue') return json(queue(q));
      if (path === 'availability') return json(availability(q));
      if (path === 'states') return json(states(q));
      return no();
    }
    if (path === 'areas' && method === 'POST') {
      const list = Array.isArray(body) ? body : [body], ids = [];
      for (const a of list) {
        const hit = D.areas.find(x => x.name.toLowerCase() === String(a.name || '').toLowerCase());
        if (!hit) return no(`“${a.name || 'This area'}” is not in the public demo: it holds the three case areas only. Run the app on your own computer to collect any other area.`);
        if (!st.added.includes(hit.id)) st.added.push(hit.id);
        ids.push(hit.id);
      }
      save(); return json({ ids });
    }
    if (path.startsWith('areas/') && method === 'DELETE') {
      const id = +path.slice(6);
      st.added = st.added.filter(x => x !== id); st.discovered = st.discovered.filter(x => x !== id);
      const keep = new Set(st.discovered.flatMap(a => areaPois(a)));
      st.retrieved = st.retrieved.filter(i => keep.has(i)); syncRetrieved(); save(); return json({ ok: true });
    }
    if (path.startsWith('jobs/')) {
      const kind = path.slice(5);
      if (kind === 'stop') { if (job.status === 'running') { job.status = 'stopped'; save(); } return json({ ok: true }); }
      if (job.status === 'running') return json({ ok: false, message: 'a job is already running' }, 409);
      const ids = (body.area_ids || st.added).map(Number);
      if (kind === 'discover') { if (!ids.length) return json({ ok: false, message: 'Add a study area first' }, 400); discover(ids); return json({ ok: true }); }
      if (kind === 'retrieve') {
        if (!ids.some(a => st.discovered.includes(a))) return json({ ok: false, message: 'Run 02 Discover first' }, 400);
        retrieve(ids, body.categories); return json({ ok: true });
      }
      return no();
    }
    if (path === 'settings' && method === 'POST') { const { google_api_key, llm_api_key, ...rest } = body || {}; st.settings = { ...st.settings, ...rest }; save(); return json({ ok: true }); }
    if (path === 'reset' && method === 'POST') { st = { added: [], discovered: [], retrieved: [], settings: {} }; syncRetrieved(); save(); return json({ ok: true }); }
    return no();
  }
  window.fetch = function (input, opt = {}) {
    const url = typeof input === 'string' ? input : input.url;
    const u = new URL(url, location.href);
    if (u.origin === location.origin && /(^|\/)api\//.test(u.pathname)) return answer(url, opt);
    return realFetch(input, opt);
  };
  window.TC_STATIC_DEMO = true;
  document.addEventListener('DOMContentLoaded', () => {
    const b = document.getElementById('demoBanner');
    if (b) { b.hidden = false; b.textContent = 'Public demo: the Collector replays the pre-collected Google Places sample for the three case areas (Bencoolen, Tanjong Pagar, Promenade). Start with 01 Area → Add the 3 case studies. To collect any other area, run the app on your own computer.'; }
  });
})();
