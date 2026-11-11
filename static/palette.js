/* Shared visual semantics for Story, Collector, Atlas and Information. */
(function () {
  const palette = {
    category: {
      'Food & Beverage': '#ff715f', Retail: '#24d8bd', Services: '#5da6ff',
      Education: '#ad8cff', 'Community & Civic': '#b5e96a',
      'Culture & Recreation': '#ff70c2', All: '#8d78ff'
    },
    landUse: {
      Residential: '#55dca9', Mixed: '#ffc46b', Commercial: '#34d2dc',
      Hotel: '#ff8c71', Civic_Edu: '#909dff', Open_Space: '#b8e874',
      Other: '#9ba8c4', EXCLUDE: '#7d8599'
    },
    district: {
      Bencoolen: '#36d7bc', 'Tanjong Pagar': '#ffbf66', Promenade: '#e684f4'
    },
    fallbackDistrict: ['#52b8ff', '#ff8e71', '#b8e874', '#ad8cff', '#24d8bd', '#ff70c2'],
    label: {
      verified: '#36dca5', observed: '#6bafff', retrieved: '#4ed9df',
      conflict: '#ff9564', estimated: '#b28dff', missing: '#95a0b8', pending: '#b6bed2'
    },
    opening: ['#ffe9de', '#ffc1a7', '#ff9079', '#ff5e6b', '#c9315a'],
    nightHeat: ['#472867', '#8d43b8', '#e452a2', '#ff7771', '#ffbd68'],
    gfa: ['#dceeff', '#a6d8ff', '#65afff', '#4b84f2', '#584bd6'],
    gfaLine: '#a890ff', poiLine: '#29d6bf', hourLine: '#ff9273'
  };
  window.TC_PALETTE = palette;
  const root = document.documentElement.style;
  const assign = (prefix, values) => Object.entries(values).forEach(([key, value]) =>
    root.setProperty('--tc-' + prefix + '-' + key.toLowerCase().replace(/[^a-z0-9]+/g, '-'), value));
  assign('category', palette.category);
  assign('land-use', palette.landUse);
  assign('district', palette.district);
  assign('label', palette.label);
  Object.entries(palette.label).forEach(([key, value]) => root.setProperty('--' + key, value));
  palette.opening.forEach((value, i) => root.setProperty('--tc-opening-' + i, value));
  palette.nightHeat.forEach((value, i) => root.setProperty('--tc-night-heat-' + i, value));
  palette.gfa.forEach((value, i) => root.setProperty('--tc-gfa-' + i, value));
  root.setProperty('--tc-gfa-line', palette.gfaLine);
  root.setProperty('--tc-poi-line', palette.poiLine);
  root.setProperty('--tc-hour-line', palette.hourLine);
})();
