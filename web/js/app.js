/* ============================================================
   Maharashtra Schools Dashboard — app.js
   ============================================================ */

const DATA_URL = 'data/schools_data.json';

const SOURCE_ICONS = {
  'UDISE+ Portal':        '🏫',
  'data.gov.in':          '🗄️',
  'Ministry of Education':'📘',
  'Census of India':      '🗺️'
};

// ── Helpers ──────────────────────────────────────────────────

function fmt(n) {
  return n != null ? n.toLocaleString('en-IN') : '—';
}

function hideLoading() {
  document.getElementById('loading').style.display = 'none';
}

function showError(msg) {
  document.getElementById('loading').innerHTML = `
    <div class="error-box">
      <h2>Failed to Load Data</h2>
      <p>${msg}</p>
    </div>`;
}

// ── Data Load ────────────────────────────────────────────────

async function loadData() {
  try {
    const res = await fetch(DATA_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    showError('Could not load <code>data/schools_data.json</code>. ' +
      'Open this page via a local server (e.g. <code>npx serve web</code>), ' +
      'or run the scraper first: <code>cd scraper &amp;&amp; python scrape.py</code>');
    return null;
  }
}

// ── Render: Sources ──────────────────────────────────────────

function renderSources(sources) {
  const grid = document.getElementById('sources-grid');
  grid.innerHTML = sources.map(s => `
    <div class="source-card">
      <div class="source-card-icon">${SOURCE_ICONS[s.name] || '📂'}</div>
      <h3>${s.name}</h3>
      <p>${s.description}</p>
      <a href="${s.url}" target="_blank" rel="noopener noreferrer">${s.url}</a>
      <br>
      <span class="source-status">${s.status}</span>
    </div>
  `).join('');
}

// ── Render: Summary Stats ────────────────────────────────────

function renderStats(yearlyData) {
  const latest = yearlyData[yearlyData.length - 1];

  document.getElementById('latest-year-label').textContent = latest.year;

  const items = [
    {
      num: fmt(latest.total),
      label: 'Total Government Schools',
      change: latest.change_pct != null
        ? `${latest.change_pct > 0 ? '+' : ''}${latest.change_pct}% vs previous year`
        : null,
      cls: latest.change_pct >= 0 ? 'positive' : 'negative'
    },
    { num: fmt(latest.primary),          label: 'Primary Schools (I–V)',         change: null },
    { num: fmt(latest.upper_primary),    label: 'Upper Primary (VI–VIII)',        change: null },
    { num: fmt(latest.secondary),        label: 'Secondary Schools (IX–X)',       change: null },
    { num: fmt(latest.higher_secondary), label: 'Higher Secondary (XI–XII)',      change: null },
    {
      num: yearlyData.length,
      label: 'Years of Data Available',
      change: `${yearlyData[0].year} – ${latest.year}`,
      cls: 'neutral'
    },
    {
      num: '36',
      label: 'Districts Covered',
      change: 'All Maharashtra districts',
      cls: 'neutral'
    }
  ];

  document.getElementById('stats-grid').innerHTML = items.map(it => `
    <div class="stat-card">
      <div class="stat-number">${it.num}</div>
      <div class="stat-label">${it.label}</div>
      ${it.change ? `<div class="stat-change ${it.cls || ''}">${it.change}</div>` : ''}
    </div>
  `).join('');
}

// ── Render: Trend Line Chart ─────────────────────────────────

function renderTrendChart(yearlyData) {
  const ctx = document.getElementById('trendChart').getContext('2d');
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: yearlyData.map(d => d.year),
      datasets: [{
        label: 'Total Schools',
        data: yearlyData.map(d => d.total),
        borderColor: '#2e86c1',
        backgroundColor: 'rgba(46,134,193,0.07)',
        borderWidth: 2.5,
        pointRadius: 5,
        pointHoverRadius: 7,
        pointBackgroundColor: '#2e86c1',
        fill: true,
        tension: 0.35
      }]
    },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` Schools: ${ctx.raw.toLocaleString('en-IN')}`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: false,
          ticks: { callback: v => (v / 1000).toFixed(0) + 'K' },
          grid: { color: '#eef1f4' }
        },
        x: { grid: { display: false } }
      }
    }
  });
}

// ── Render: Doughnut — Category ──────────────────────────────

function renderCategoryChart(yearlyData) {
  const latest = yearlyData[yearlyData.length - 1];
  const ctx = document.getElementById('categoryChart').getContext('2d');
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Primary', 'Upper Primary', 'Secondary', 'Higher Secondary'],
      datasets: [{
        data: [latest.primary, latest.upper_primary, latest.secondary, latest.higher_secondary],
        backgroundColor: ['#3498db', '#2ecc71', '#f39c12', '#e74c3c'],
        borderWidth: 3,
        borderColor: '#fff',
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      cutout: '58%',
      plugins: {
        legend: { position: 'bottom', labels: { padding: 16, font: { size: 12 } } },
        tooltip: {
          callbacks: {
            label: ctx => {
              const pct = ((ctx.raw / latest.total) * 100).toFixed(1);
              return ` ${ctx.label}: ${ctx.raw.toLocaleString('en-IN')} (${pct}%)`;
            }
          }
        }
      }
    }
  });
}

// ── Render: Bar — Management Type ────────────────────────────

function renderManagementChart(mgmt) {
  const ctx = document.getElementById('managementChart').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: mgmt.types.map(t => t.type),
      datasets: [{
        label: 'Schools',
        data: mgmt.types.map(t => t.count),
        backgroundColor: ['#1a5276', '#2e86c1', '#7fb3d3', '#aed6f1'],
        borderRadius: 6,
        borderSkipped: false
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const pct = mgmt.types[ctx.dataIndex].percentage;
              return ` ${ctx.raw.toLocaleString('en-IN')} schools (${pct}%)`;
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { callback: v => (v / 1000).toFixed(0) + 'K' },
          grid: { color: '#eef1f4' }
        },
        x: { grid: { display: false } }
      }
    }
  });
}

// ── Render: Bar — YoY Change ─────────────────────────────────

function renderChangeChart(yearlyData) {
  const rows = yearlyData.filter(d => d.change_pct != null);
  const ctx = document.getElementById('changeChart').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: rows.map(d => d.year),
      datasets: [{
        label: 'YoY Change %',
        data: rows.map(d => d.change_pct),
        backgroundColor: rows.map(d => d.change_pct >= 0
          ? 'rgba(39,174,96,0.75)'
          : 'rgba(231,76,60,0.75)'),
        borderColor: rows.map(d => d.change_pct >= 0 ? '#27ae60' : '#e74c3c'),
        borderWidth: 1,
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.raw > 0 ? '+' : ''}${ctx.raw}%`
          }
        }
      },
      scales: {
        y: {
          ticks: { callback: v => v + '%' },
          grid: { color: '#eef1f4' }
        },
        x: { grid: { display: false } }
      }
    }
  });
}

// ── Render: Year-wise Table ──────────────────────────────────

function renderYearlyTable(yearlyData) {
  const tbody = document.getElementById('yearly-tbody');
  tbody.innerHTML = [...yearlyData].reverse().map((d, i) => {
    const changeHtml = d.change_pct != null
      ? `<span class="${d.change_pct >= 0 ? 'change-positive' : 'change-negative'}">
           ${d.change_pct > 0 ? '+' : ''}${d.change_pct}%
         </span>`
      : '<span style="color:var(--text-muted)">—</span>';

    const isLatest = i === 0;
    return `
      <tr ${isLatest ? 'style="background:#eef7ff;font-weight:600"' : ''}>
        <td>${d.year}</td>
        <td>${fmt(d.total)}</td>
        <td>${fmt(d.primary)}</td>
        <td>${fmt(d.upper_primary)}</td>
        <td>${fmt(d.secondary)}</td>
        <td>${fmt(d.higher_secondary)}</td>
        <td>${changeHtml}</td>
      </tr>
    `;
  }).join('');
}

// ── Render: District Table ───────────────────────────────────

let allDistricts = [];
let grandTotal   = 0;

function renderDistrictTable(rows) {
  const tbody = document.getElementById('district-tbody');
  tbody.innerHTML = rows.map((d, i) => {
    const share   = grandTotal ? ((d.total / grandTotal) * 100).toFixed(2) : 0;
    const barWidth = Math.max(2, (share / 5) * 100).toFixed(0); // max ~5% → full bar
    const rankCls  = i < 3 ? 'top' : '';
    return `
      <tr>
        <td><span class="rank-badge ${rankCls}">${i + 1}</span></td>
        <td><strong>${d.district}</strong></td>
        <td>${fmt(d.total)}</td>
        <td>${fmt(d.primary)}</td>
        <td>${fmt(d.secondary)}</td>
        <td>${fmt(d.higher_secondary)}</td>
        <td>
          <div class="share-bar">
            <div class="share-bar-fill" style="width:${barWidth}px"></div>
            <span class="share-bar-label">${share}%</span>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function setupDistrictControls() {
  const search = document.getElementById('district-search');
  const sort   = document.getElementById('district-sort');

  function apply() {
    let rows = [...allDistricts];
    const q  = search.value.trim().toLowerCase();
    if (q) rows = rows.filter(d => d.district.toLowerCase().includes(q));

    if      (sort.value === 'total-desc') rows.sort((a, b) => b.total - a.total);
    else if (sort.value === 'total-asc')  rows.sort((a, b) => a.total - b.total);
    else if (sort.value === 'name-asc')   rows.sort((a, b) => a.district.localeCompare(b.district));

    renderDistrictTable(rows);
  }

  search.addEventListener('input', apply);
  sort.addEventListener('change', apply);
}

// ── Init ─────────────────────────────────────────────────────

async function init() {
  const data = await loadData();
  if (!data) return;

  renderSources(data.data_sources);
  renderStats(data.yearly_data);
  renderTrendChart(data.yearly_data);
  renderCategoryChart(data.yearly_data);
  renderManagementChart(data.management_type_data);
  renderChangeChart(data.yearly_data);
  renderYearlyTable(data.yearly_data);

  grandTotal   = data.district_data.reduce((s, d) => s + d.total, 0);
  allDistricts = [...data.district_data].sort((a, b) => b.total - a.total);
  renderDistrictTable(allDistricts);
  setupDistrictControls();

  if (data.source_info?.last_updated) {
    document.getElementById('last-updated').textContent =
      `Data last updated: ${data.source_info.last_updated}`;
  }

  hideLoading();
}

init();
