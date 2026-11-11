/* Temporal City · public read-only Collector (GitHub Pages)
   The Collector normally talks to the local Python server. On the public site there is no server, so this
   file answers the same API calls from docs/static/demo/data.json: the Google Places sample of the three
   case areas, run through the normal pipeline (tools/build_demo_data.py). Reading works as in the app;
   anything that would change data answers "read-only", exactly like the server's public-demo mode. */
(function () {
  const realFetch = window.fetch.bind(window);
  const BASE = document.currentScript.src.replace(/static\/demo-api\.js.*$/, '');
  let D = null;
  const load = () => D ? Promise.resolve(D) : realFetch(BASE + 'static/demo/data.json').then(r => r.json()).then(j => (D = j));
  const USABLE = ['verified', 'observed', 'retrieved'];
  const DAYS = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su'];
  const DAYTYPES = { weekday: [0, 1, 2, 3, 4], saturday: [5], sunday: [6], weekend: [5, 6] };
  DAYS.forEach((d, i) => DAYTYPES[d] = [i]);
  const json = (obj, status = 200) => new Response(JSON.stringify(obj), { status, headers: { 'Content-Type': 'application/json' } });
  const readOnly = () => json({ error: 'This is a read-only public demo. Run the app locally to collect data.', message: 'Read-only public demo' }, 403);
  const matrix = id => { const s = D.mat[id]; if (!s) return null; const m = []; for (let d = 0; d < 7; d++) { m.push([]); for (let h = 0; h < 24; h++) { const c = s[d * 24 + h]; m[d].push(c === '.' ? null : +c); } } return m; };
  const poisIn = aid => { const all = D.pois.filter(p => !p.perm_closed); if (!aid) return all; const set = new Set(D.poiAreas[aid] || []); return all.filter(p => set.has(p.id)); };
  const labelsOf = q => (q.get('labels') ? q.get('labels').split(',') : USABLE);

  function availability(q) {
    const labels = labelsOf(q), days = DAYTYPES[q.get('daytype')] || DAYTYPES.weekday;
    const cats = [...D.meta.categories, 'All'];
    const total = {}, usable = {}, open = {};
    cats.forEach(c => { total[c] = 0; usable[c] = 0; open[c] = Array(24).fill(0); });
    for (const p of poisIn(q.get('area_id'))) {
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
    return poisIn(q.get('area_id')).map(p => {
      let st = 'nodata';
      if (labels.includes(p.final_label)) { const m = matrix(p.id); const v = m ? m[di][h] : null; st = v === 1 ? 'open' : v === 0 ? 'closed' : 'nodata'; }
      return { id: p.id, state: st };
    });
  }
  function queue(q) {
    const labels = (q.get('labels') || 'missing,pending').split(','), cat = q.get('category') || '';
    const aids = (q.get('area_ids') || '').split(',').filter(Boolean);
    const ids = aids.length ? new Set(aids.flatMap(a => D.poiAreas[a] || [])) : null;
    return D.pois.filter(p => (!ids || ids.has(p.id)) && labels.includes(p.final_label) && p.name && !p.perm_closed && (!cat || p.category === cat))
      .sort((a, b) => (a.category + a.name).localeCompare(b.category + b.name))
      .map(p => ({ id: p.id, name: p.name, category: p.category, subtype: p.subtype, address: null, label: p.final_label, lat: p.lat, lon: p.lon,
        hours_text: p.hours_text, google_url: 'https://www.google.com/search?hl=en&q=' + encodeURIComponent(p.name + ' Singapore opening hours'),
        maps_url: 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(p.name + ' ' + p.lat + ',' + p.lon) }));
  }

  async function answer(url, opt) {
    await load();
    const u = new URL(url, location.href), q = u.searchParams, path = u.pathname.replace(/^.*\/api\//, '');
    if ((opt.method || 'GET').toUpperCase() !== 'GET') return readOnly();
    if (path === 'meta') return json(D.meta);
    if (path === 'settings') return json(D.settings);
    if (path === 'job') return json(D.job);
    if (path === 'areas') return json(D.areas);
    if (path === 'pois') return json(q.get('area_id') ? poisIn(q.get('area_id')) : D.pois);
    if (path.startsWith('pois/')) { const id = decodeURIComponent(path.slice(5)); const d = D.details[id]; return d ? json({ ...d, matrix: matrix(id) }) : json({ error: 'not found' }, 404); }
    if (path === 'coverage') return json(D.coverage[q.get('area_id') || 'all'] || D.coverage.all);
    if (path === 'validation') return json(D.validation);
    if (path === 'audit_sample') return json(D.auditSample);
    if (path === 'queue') return json(queue(q));
    if (path === 'availability') return json(availability(q));
    if (path === 'states') return json(states(q));
    return readOnly();
  }
  window.fetch = function (input, opt = {}) {
    const url = typeof input === 'string' ? input : input.url;
    if (/(^|\/)api\//.test(new URL(url, location.href).pathname) && new URL(url, location.href).origin === location.origin) return answer(url, opt);
    return realFetch(input, opt);
  };
  window.TC_STATIC_DEMO = true;
})();
