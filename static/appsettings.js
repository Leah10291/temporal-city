/* Temporal City · one settings panel for the whole site
   ------------------------------------------------------------------
   A ⚙ button in the app bar (Story, Collector, Atlas) opens a drawer with:
     · Appearance  — day / night theme (same switch as the bar)
     · Atlas data  — Google Places sample or Collector database
     · Collection  — on the Collector page, the Collector's own settings (sources, AI model,
                     Google key, proxy, reset) are moved into this drawer; elsewhere a link to them.
   API: TCSettings.mount(slotElement), TCSettings.open(section?), TCSettings.close()
*/
(function () {
  const css = document.createElement('style');
  css.textContent = `
.tc-gear{display:grid;place-items:center;width:34px;height:34px;border-radius:50%;border:1px solid var(--tc-line,var(--line,#e0e4da));background:transparent;color:var(--tc-ink-2,var(--ink-2,#4b6157));cursor:pointer;flex:none;transition:background .2s,color .2s,transform .4s}
.tc-gear:hover{background:var(--tc-ink,var(--ink,#173c33));color:var(--tc-paper,var(--paper,#f6f5ef));transform:rotate(45deg)}
.tc-gear svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:1.6}
.tc-drawer{position:fixed;inset:0;z-index:3000;display:flex;justify-content:flex-end}
.tc-drawer[hidden]{display:none}
.tc-drawer-back{position:absolute;inset:0;background:rgba(10,20,17,.38);opacity:0;transition:opacity .25s}
.tc-drawer.open .tc-drawer-back{opacity:1}
.tc-drawer aside{position:relative;width:min(520px,100%);height:100%;overflow-y:auto;background:var(--tc-paper,var(--paper,#f6f5ef));color:var(--tc-ink,var(--ink,#173c33));
  box-shadow:-20px 0 60px -30px rgba(0,0,0,.5);transform:translateX(100%);transition:transform .3s cubic-bezier(.2,.7,.2,1);padding:0 24px 40px}
.tc-drawer.open aside{transform:none}
.tc-drawer header.tc-dh{position:sticky;top:0;z-index:2;display:flex;align-items:center;justify-content:space-between;padding:18px 0 14px;background:inherit;border-bottom:1px solid var(--tc-line,var(--line,#e0e4da))}
.tc-drawer h2{font:800 24px 'Manrope',system-ui,sans-serif;letter-spacing:-.03em;margin:0}
.tc-drawer .tc-x{width:34px;height:34px;border-radius:50%;border:1px solid var(--tc-line,var(--line,#e0e4da));background:transparent;color:inherit;font-size:18px;cursor:pointer}
.tc-drawer nav.tc-dtabs{display:flex;gap:4px;margin:14px 0 4px;flex-wrap:wrap}
.tc-drawer nav.tc-dtabs a{font:700 11px 'DM Sans',system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;padding:6px 11px;border-radius:999px;border:1px solid var(--tc-line,var(--line,#e0e4da));color:var(--tc-ink-2,var(--ink-2,#4b6157));text-decoration:none}
.tc-drawer section.tc-ds{padding:18px 0;border-bottom:1px solid var(--tc-line,var(--line,#e0e4da));scroll-margin-top:70px}
.tc-drawer section.tc-ds>h3{font:700 11px 'DM Sans',system-ui,sans-serif;letter-spacing:.18em;text-transform:uppercase;color:var(--tc-gold-deep,#9b7a3b);margin:0 0 6px}
.tc-drawer section.tc-ds>p{font-size:13px;line-height:1.6;color:var(--tc-ink-2,var(--ink-2,#4b6157));margin:0 0 10px}
.tc-drawer .tc-seg{display:inline-flex;gap:2px;padding:3px;border:1px solid var(--tc-line,var(--line,#e0e4da));border-radius:999px}
.tc-drawer .tc-seg a,.tc-drawer .tc-seg button{font:700 12px 'DM Sans',system-ui,sans-serif;letter-spacing:.04em;padding:7px 14px;border-radius:999px;border:0;background:transparent;color:var(--tc-ink-2,var(--ink-2,#4b6157));text-decoration:none;cursor:pointer}
.tc-drawer .tc-seg .on,.tc-drawer .tc-seg [aria-pressed="true"]{background:var(--tc-ink,var(--ink,#173c33));color:var(--tc-paper,var(--paper,#f6f5ef))}
.tc-drawer .tc-link{display:inline-block;margin-top:4px;font:700 12px 'DM Sans',system-ui,sans-serif;color:var(--tc-ink,var(--ink,#173c33))}
.tc-drawer .pane{display:block!important}
.tc-drawer .pane>h2{display:none}
body.tc-drawer-open{overflow:hidden}
@media (prefers-reduced-motion:reduce){.tc-drawer aside,.tc-drawer-back{transition:none}}`;
  document.head.appendChild(css);

  const GEAR = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3.2"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>';
  let drawer = null, lastFocus = null;
  const page = /collector/.test(location.pathname) ? 'collector' : /atlas/.test(location.pathname) ? 'atlas' : 'story';

  function build() {
    if (drawer) return drawer;
    const src = page === 'atlas' && /source=collector/.test(location.search) ? 'collector' : 'sample';
    drawer = document.createElement('div');
    drawer.className = 'tc-drawer'; drawer.hidden = true;
    drawer.innerHTML = `<div class="tc-drawer-back" data-close></div>
<aside role="dialog" aria-modal="true" aria-labelledby="tcSetTitle">
 <header class="tc-dh"><h2 id="tcSetTitle">Settings</h2><button type="button" class="tc-x" data-close aria-label="Close settings">×</button></header>
 <nav class="tc-dtabs"><a href="#tcs-look">Appearance</a><a href="#tcs-atlas">Atlas data</a><a href="#tcs-collect">Collection</a></nav>
 <section class="tc-ds" id="tcs-look"><h3>Appearance</h3>
  <p>Auto follows the hour shown on the page (the Atlas time slider, the Collector's Explore hour); Day and Night lock the whole site.</p>
  <div class="tc-seg" id="tcsTheme"><button type="button" data-mode="auto">Auto</button><button type="button" data-mode="day">Day</button><button type="button" data-mode="night">Night</button></div>
 </section>
 <section class="tc-ds" id="tcs-atlas"><h3>Atlas data</h3>
  <p>The Atlas can show the group's Google Places sample (three case studies) or the data you collected. With Collector data, choose study areas in the Collector (tick them, then View in Atlas) or with “Choose study areas” at the top of the Atlas.</p>
  <div class="tc-seg"><a href="atlas.html" class="${page === 'atlas' && src === 'sample' ? 'on' : ''}">Google Places sample</a><a href="atlas.html?source=collector" data-needs-app class="${src === 'collector' ? 'on' : ''}">Collector database</a></div>
 </section>
 <section class="tc-ds" id="tcs-collect"><h3>Collection</h3>
  <div id="tcsCollect">${page === 'collector' ? '' : '<p>Sources, AI model, Google Places key, proxy and database reset are set in the Collector (local app only).</p><a class="tc-link" href="collector.html#settings" data-needs-app>Open collection settings →</a>'}</div>
 </section>
</aside>`;
    document.body.appendChild(drawer);
    drawer.addEventListener('click', (e) => {
      if (e.target.closest('[data-close]')) close();
      const t = e.target.closest('#tcsTheme button'); if (t && window.TCDayNight) { TCDayNight.setMode(t.dataset.mode); syncTheme(); }
      const a = e.target.closest('nav.tc-dtabs a'); if (a) { e.preventDefault(); drawer.querySelector(a.getAttribute('href')).scrollIntoView({ behavior: 'smooth' }); }
    });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && drawer.classList.contains('open')) close(); });
    // the Collector's settings pane lives in the drawer
    const pane = document.querySelector('[data-pane="settings"]');
    if (pane) { drawer.querySelector('#tcsCollect').appendChild(pane); pane.classList.add('on'); }
    window.addEventListener('tc-daynight', syncTheme);
    syncTheme();
    return drawer;
  }
  function syncTheme() { if (!drawer || !window.TCDayNight) return; drawer.querySelectorAll('#tcsTheme button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.mode === TCDayNight.mode))); }
  function open(section) {
    build(); lastFocus = document.activeElement;
    drawer.hidden = false; document.body.classList.add('tc-drawer-open');
    requestAnimationFrame(() => { drawer.classList.add('open'); });
    if (typeof window.loadSettings === 'function') try { window.loadSettings(); } catch (e) {}
    setTimeout(() => {
      if (section) { const s = drawer.querySelector('#tcs-' + section); if (s) s.scrollIntoView({ block: 'start' }); }
      drawer.querySelector('.tc-x').focus();
    }, 60);
  }
  function close() {
    if (!drawer) return;
    drawer.classList.remove('open'); document.body.classList.remove('tc-drawer-open');
    setTimeout(() => { drawer.hidden = true; }, 280);
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  function mount(slot) {
    if (!slot) return;
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'tc-gear'; b.title = 'Settings'; b.setAttribute('aria-label', 'Settings'); b.innerHTML = GEAR;
    b.addEventListener('click', () => open());
    slot.appendChild(b);
    if (page === 'collector') build(); // move the settings pane in now so its form is wired normally
    if (location.hash === '#settings') setTimeout(() => open('collect'), 300);
  }
  window.TCSettings = { mount, open, close };
})();
