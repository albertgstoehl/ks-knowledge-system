// ==========================================================================
// SHARED COMPONENT UTILITIES
// JavaScript utilities for shared UI components
// ==========================================================================

// Accordion
function toggleAccordion(id) {
  const content = document.getElementById('content-' + id);
  const toggle = document.getElementById('toggle-' + id);
  const isOpen = content.classList.contains('accordion__content--open');

  if (isOpen) {
    content.classList.remove('accordion__content--open');
    toggle.textContent = '▶';
  } else {
    content.classList.add('accordion__content--open');
    toggle.textContent = '▼';
  }
}

// Dropdown
function toggleDropdown(id) {
  const menu = document.getElementById('dropdown-' + id);
  const backdrop = document.getElementById('backdrop-' + id);
  menu.classList.toggle('dropdown__menu--open');
  if (backdrop) backdrop.classList.toggle('dropdown__backdrop--open');
}

function closeDropdown(id) {
  const menu = document.getElementById('dropdown-' + id);
  const backdrop = document.getElementById('backdrop-' + id);
  menu.classList.remove('dropdown__menu--open');
  if (backdrop) backdrop.classList.remove('dropdown__backdrop--open');
}

// Source panel
function toggleSourcePanel() {
  const details = document.getElementById('source-details');
  const toggle = document.getElementById('source-toggle');
  if (details.style.display === 'none') {
    details.style.display = 'block';
    toggle.textContent = '[-]';
  } else {
    details.style.display = 'none';
    toggle.textContent = '[+]';
  }
}

// Close dropdowns on outside click
document.addEventListener('click', function(e) {
  if (!e.target.closest('.dropdown')) {
    document.querySelectorAll('.dropdown__menu--open').forEach(menu => {
      const id = menu.id.replace('dropdown-', '');
      closeDropdown(id);
    });
  }
});

// ==========================================================================
// PRIORITY LIST - Up/down reorder
// ==========================================================================

function movePriority(btn, direction) {
  const item = btn.closest('.priority-list__item');
  const list = item.closest('.priority-list');

  if (direction === 'up' && item.previousElementSibling) {
    item.previousElementSibling.before(item);
  } else if (direction === 'down' && item.nextElementSibling) {
    item.nextElementSibling.after(item);
  }

  updatePriorityList(list);
}

function updatePriorityList(list) {
  const items = list.querySelectorAll('.priority-list__item');
  items.forEach((item, index) => {
    // Update rank number
    const rank = item.querySelector('.priority-list__rank');
    if (rank) rank.textContent = index + 1;

    // Update button states
    const upBtn = item.querySelector('.priority-list__arrow[data-dir="up"]');
    const downBtn = item.querySelector('.priority-list__arrow[data-dir="down"]');
    if (upBtn) upBtn.disabled = index === 0;
    if (downBtn) downBtn.disabled = index === items.length - 1;
  });
}

/* ==========================================================================
   CHART
   Simple SVG line chart renderer
   ========================================================================== */

function renderLineChart(containerId, data, options = {}) {
  const container = document.getElementById(containerId);
  if (!container || !data || data.length === 0) return;

  const padding = { top: 20, right: 20, bottom: 30, left: 40 };
  const width = container.clientWidth;
  const height = container.clientHeight || 200;
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Calculate scales
  const xValues = data.map((d, i) => i);
  const yValues = data.map(d => d.y);
  const yMin = Math.min(...yValues) * 0.95;
  const yMax = Math.max(...yValues) * 1.05;

  const xScale = (i) => padding.left + (i / (data.length - 1)) * chartWidth;
  const yScale = (v) => padding.top + chartHeight - ((v - yMin) / (yMax - yMin)) * chartHeight;

  // Build SVG
  let svg = `<svg class="chart__svg" viewBox="0 0 ${width} ${height}">`;

  // Y-axis grid lines
  const yTicks = 4;
  for (let i = 0; i <= yTicks; i++) {
    const y = padding.top + (i / yTicks) * chartHeight;
    const val = yMax - (i / yTicks) * (yMax - yMin);
    svg += `<line class="chart__grid" x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}"/>`;
    svg += `<text class="chart__label" x="${padding.left - 5}" y="${y + 4}" text-anchor="end">${val.toFixed(1)}</text>`;
  }

  // Line path
  const pathData = data.map((d, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(d.y)}`).join(' ');
  svg += `<path class="chart__line" d="${pathData}"/>`;

  // Points
  data.forEach((d, i) => {
    svg += `<circle class="chart__point" cx="${xScale(i)}" cy="${yScale(d.y)}" r="4"/>`;
  });

  // X-axis labels
  data.forEach((d, i) => {
    if (d.label) {
      svg += `<text class="chart__label" x="${xScale(i)}" y="${height - 5}" text-anchor="middle">${d.label}</text>`;
    }
  });

  svg += '</svg>';
  container.innerHTML = svg;
}
