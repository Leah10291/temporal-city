/* Floating optical lens for navigation and option bars. No data or map state changes. */
(() => {
  const groups = '.appnav,.top .nav,.top .app-links,#daySeg,#mmHours,#districtButtons,.map-tools,#filters,#states,#exDay,#exMetric';
  const target = 'a,button,label.upload-label';
  function bind(group) {
    if (group.dataset.lensBound) return;
    group.dataset.lensBound = '1';
    group.classList.add('lens-nav');
    function move(el) {
      if (!el || !group.contains(el)) { group.classList.remove('lens-on'); return; }
      const parent = group.getBoundingClientRect(), box = el.getBoundingClientRect();
      group.style.setProperty('--lens-left', `${box.left-parent.left+group.scrollLeft}px`);
      group.style.setProperty('--lens-top', `${box.top-parent.top+group.scrollTop}px`);
      group.style.setProperty('--lens-width', `${box.width}px`);
      group.style.setProperty('--lens-height', `${box.height}px`);
      group.classList.add('lens-on');
    }
    group.addEventListener('pointermove', e => move(e.target.closest(target)));
    group.addEventListener('pointerleave', () => group.classList.remove('lens-on'));
    group.addEventListener('focusin', e => move(e.target.closest(target)));
    group.addEventListener('focusout', e => {
      if (!group.contains(e.relatedTarget)) group.classList.remove('lens-on');
    });
  }
  function scan() {
    document.querySelectorAll(groups).forEach(bind);
    addReadingRoute();
    document.querySelectorAll('#discover .note,#compare .note,#reveal .note').forEach(note => {
      if (note.closest('details')) return;
      const disclosure = document.createElement('details');
      disclosure.className = 'tc-inline-note';
      const title = document.createElement('summary');
      title.textContent = 'Method detail';
      note.replaceWith(disclosure);
      disclosure.append(title, note);
    });
  }
  function addReadingRoute() {
    if (document.querySelector('.tc-reading-route')) return;
    const main = document.querySelector('main');
    if (!main) return;
    function getSections() {
      if (document.documentElement.hasAttribute('data-tc-info'))
        return [...document.querySelectorAll('main .layout .sec')].filter(Boolean);
      if (document.documentElement.hasAttribute('data-tc-story'))
        return [...document.querySelectorAll('main > section')].filter(el => el.getBoundingClientRect().height > 0);
      if (document.querySelector('#flow'))
        return [main.querySelector('.hero'), document.getElementById('flow'), main.querySelector(':scope > .grid')].filter(Boolean);
      const active = main.querySelector('.view.active');
      return active ? [...active.querySelectorAll(':scope > .grid, :scope > .panel')].filter(el => el.getBoundingClientRect().height > 0) : [];
    }
    if (!getSections().length) return;
    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    svg.classList.add('tc-reading-route');
    svg.setAttribute('aria-hidden', 'true');
    svg.innerHTML = '<defs><linearGradient id="tc-route-gradient" x1="0" y1="0" x2="1" y2="0">'
      + '<stop stop-color="#a963f1"/><stop offset=".52" stop-color="#ee6ea8"/>'
      + '<stop offset="1" stop-color="#ff9659"/></linearGradient>'
      + '<filter id="tc-route-trail-blur"><feGaussianBlur stdDeviation="2.5"/></filter></defs>'
      + '<path class="tc-route-track" fill="none"/>'
      + '<g class="tc-route-trails">'
      + [0,1,2,3].map(i => `<rect class="tc-route-trail" data-trail="${i}" x="-25" y="-2.5" width="50" height="5" rx="2.5" fill="url(#tc-route-gradient)" opacity="${(.34-i*.065).toFixed(2)}" filter="url(#tc-route-trail-blur)"/>`).join('')
      + '</g>'
      + '<rect class="tc-route-cursor" x="-28" y="-3" width="56" height="6" rx="3" fill="url(#tc-route-gradient)"/>';
    document.body.append(svg);
    const track = svg.querySelector('.tc-route-track');
    const cursor = svg.querySelector('.tc-route-cursor');
    const trails = [...svg.querySelectorAll('.tc-route-trail')];
    let start = 0, end = 1, length = 1, ticking = false, lastDistance = 0;
    const docY = element => element.getBoundingClientRect().top + scrollY;
    const pose = distance => {
      const p = track.getPointAtLength(distance);
      const before = track.getPointAtLength(Math.max(0, distance - 2));
      const after = track.getPointAtLength(Math.min(length, distance + 2));
      return {point:p, angle:Math.atan2(after.y - before.y, after.x - before.x) * 180 / Math.PI};
    };
    // Story and Information: the cursor rides the reading line and makes each crossing
    // within about a third of a screen of scrolling, so it never leaves the viewport.
    let seams = [];
    const followsReading = () => document.documentElement.hasAttribute('data-tc-story') || document.documentElement.hasAttribute('data-tc-info');
    function distanceAt(visibleY) {
      if (!seams.length) {
        const fraction = Math.min(1, Math.max(0, (visibleY - start) / (end - start)));
        return fraction * length;
      }
      let prevY = start, prevD = 0;
      for (const s of seams) {
        if (visibleY < s.y0) return prevD + Math.min(1, Math.max(0, (visibleY - prevY) / Math.max(1, s.y0 - prevY))) * (s.d0 - prevD);
        if (visibleY <= s.y1) return s.d0 + (visibleY - s.y0) / Math.max(1, s.y1 - s.y0) * (s.d1 - s.d0);
        prevY = s.y1; prevD = s.d1;
      }
      return prevD + Math.min(1, Math.max(0, (visibleY - prevY) / Math.max(1, end - prevY))) * (length - prevD);
    }
    function update() {
      ticking = false;
      const visibleY = scrollY + innerHeight * .38;
      const distance = distanceAt(visibleY);
      const {point,angle} = pose(distance);
      cursor.setAttribute('transform', `translate(${point.x} ${point.y}) rotate(${angle})`);
      const direction = distance >= lastDistance ? 1 : -1;
      trails.forEach((trail,i) => {
        const d = Math.max(0, Math.min(length, distance - direction * (11 + i * 13)));
        const faded = pose(d);
        trail.setAttribute('transform', `translate(${faded.point.x} ${faded.point.y}) rotate(${faded.angle})`);
      });
      lastDistance = distance;
    }
    function draw() {
      const sections = getSections();
      if (!sections.length) return;
      const information = document.documentElement.hasAttribute('data-tc-info');
      const atlasView = !information && !!main.querySelector('.view.active') && !document.documentElement.hasAttribute('data-tc-story');
      const container = information
        ? (main.querySelector('.layout .content') || main.querySelector('.layout'))
        : atlasView ? sections[0]
        : (sections[0].querySelector('.wrap') || main.querySelector('.wrap') || main);
      const box = container.getBoundingClientRect();
      const compact = innerWidth <= (information ? 1000 : 1100);
      const left = information || atlasView
        ? Math.max(9, Math.floor(box.left - (compact ? 10 : 18)))
        : (compact ? 9 : Math.max(12, Math.floor(box.left - 36)));
      const right = compact ? left : Math.min(innerWidth - 12, Math.ceil(box.right + (information || atlasView ? 18 : 36)));
      start = docY(sections[0]) + 26;
      end = Math.max(start + 1, docY(sections.at(-1)) + sections.at(-1).offsetHeight - 28);
      const height = document.documentElement.scrollHeight;
      svg.setAttribute('viewBox', `0 0 ${innerWidth} ${height}`);
      svg.style.height = height + 'px';
      let x = left, path = `M ${left} ${start}`;
      const marks = [];
      for (let i = 1; i < sections.length; i++) {
        const boundary = docY(sections[i]);
        if (compact) { path += ` L ${left} ${boundary}`; continue; }
        // Reading pages: stay on the same side around very short sections.
        if (followsReading() && Math.min(sections[i - 1].offsetHeight, sections[i].offsetHeight) < 450) continue;
        const next = x === left ? right : left;
        const direction = next > x ? 1 : -1;
        path += ` L ${x} ${boundary - 18}`;
        const before = path;
        path += ` Q ${x} ${boundary} ${x + direction * 18} ${boundary}`;
        path += ` L ${next - direction * 18} ${boundary}`;
        path += ` Q ${next} ${boundary} ${next} ${boundary + 18}`;
        marks.push({boundary, before, after: path});
        x = next;
      }
      path += ` L ${x} ${end}`;
      seams = [];
      if (followsReading()) {
        let lastY = start;
        marks.forEach((m, i) => {
          const nextB = i + 1 < marks.length ? marks[i + 1].boundary : end;
          const half = Math.max(40, Math.min(innerHeight * .25, (m.boundary - lastY) * .45, (nextB - m.boundary) * .45));
          track.setAttribute('d', m.before); const d0 = track.getTotalLength();
          track.setAttribute('d', m.after); const d1 = track.getTotalLength();
          seams.push({y0: m.boundary - half, y1: m.boundary + half, d0, d1});
          lastY = m.boundary + half;
        });
      }
      track.setAttribute('d', path);
      length = track.getTotalLength() || 1;
      update();
    }
    addEventListener('scroll', () => {
      if (!ticking) { ticking = true; requestAnimationFrame(update); }
    }, {passive:true});
    addEventListener('resize', () => requestAnimationFrame(draw), {passive:true});
    if (window.ResizeObserver) new ResizeObserver(() => requestAnimationFrame(draw)).observe(main);
    if (window.MutationObserver) {
      const observer = new MutationObserver(() => requestAnimationFrame(draw));
      main.querySelectorAll('.view,.pane').forEach(section => observer.observe(section, {attributes:true,attributeFilter:['class']}));
    }
    document.fonts?.ready.then(draw);
    draw();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', scan, {once:true});
  else scan();
})();
