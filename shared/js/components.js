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
