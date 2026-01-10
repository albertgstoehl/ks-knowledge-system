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
