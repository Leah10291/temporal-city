// Regression check for the embedded Google Places sample and its three curves.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const html = fs.readFileSync(path.join(__dirname, '..', 'static', 'atlas.html'), 'utf8');
const match = html.match(/const DATA=(\[.*?\]);const /s);
assert(match, 'sample DATA is embedded');
const data = JSON.parse(match[1]);
assert.equal(data.length, 595);
assert(html.includes('href="atlas.html?source=sample"'));

const districts = ['Bencoolen', 'Tanjong Pagar', 'Promenade'];
for (const name of districts) {
  const counts = [3, 12, 20].map(hour => data.filter(p => p.d === name && p.s[hour] === 1).length);
  assert(new Set(counts).size > 1, `${name} has a varying hourly profile`);
}

const nodes = {
  '#profileSubtitle': { textContent: '' },
  '#linechart': { innerHTML: '' },
  '#profileLegend': { replaceChildren(...children) { this.children = children; } },
};
const document = {
  createElement() { return { style: {}, append() {} }; },
  createTextNode(text) { return text; },
};
const fragment = html.slice(html.indexOf('function profile('), html.indexOf('function update(){'));
const makeChart = new Function('DATA', 'days', 'cats', 'all', 'districts', 'TC_PALETTE',
  'enabled', 'day', 'district', 'hour', '$', 'document',
  fragment + ';return {drawChart,setMetric:metric=>profileMetric=metric};');
const cats = [...new Set(data.map(p => p.c))];
const palette = { district: { Bencoolen: '#36d7bc', 'Tanjong Pagar': '#ffbf66', Promenade: '#e684f4' },
  fallbackDistrict: ['#52b8ff'], hourLine: '#ff9273' };
const chart = makeChart(data, ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
  cats, d => data.filter(p => p.d === d), districts, palette, new Set(cats), 'Whole week',
  'Overview', 12, key => nodes[key], document);
for (const metric of ['absolute', 'relative']) {
  chart.setMetric(metric);
  chart.drawChart();
  const paths = [...nodes['#linechart'].innerHTML.matchAll(/<path d="([^"]+)"/g)];
  assert.equal(paths.length, 3, `${metric} plots all three areas`);
  assert.equal(new Set(paths.map(x => x[1])).size, 3, `${metric} uses distinct measured profiles`);
  assert.equal(nodes['#profileLegend'].children.length, 3);
}
console.log('Sample source and three measured profile curves: OK');
