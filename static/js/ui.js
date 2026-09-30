/**
 * Dublin Transit Delay Tracker - UI Behaviors
 * Strictly pure UI interactions: active button states, mobile nav toggling,
 * keyboard accessibility, and client-side table filtering.
 * No data logic, API calls, or backend dependencies.
 */

document.addEventListener('DOMContentLoaded', () => {
  initMobileNav();
  initSegmentedControls();
  initTableSearchFilter();
  initLiveFeedTickerVisual();
});

/**
 * Mobile Navigation Menu Toggle
 */
function initMobileNav() {
  const toggleBtn = document.getElementById('mobileNavToggle');
  const navCollapse = document.getElementById('navbarTransitNav');

  if (toggleBtn && navCollapse) {
    toggleBtn.addEventListener('click', () => {
      const isExpanded = toggleBtn.getAttribute('aria-expanded') === 'true';
      toggleBtn.setAttribute('aria-expanded', String(!isExpanded));
      navCollapse.classList.toggle('show');
    });
  }
}

/**
 * Segmented Control (All / Bus / Luas) Active State Toggling
 * Supports keyboard arrow navigation for full accessibility.
 */
function initSegmentedControls() {
  const segmentedGroups = document.querySelectorAll('.segmented-control');

  segmentedGroups.forEach(group => {
    const buttons = group.querySelectorAll('.btn-segment');

    buttons.forEach((btn, index) => {
      btn.addEventListener('click', () => {
        buttons.forEach(b => {
          b.classList.remove('active');
          b.setAttribute('aria-pressed', 'false');
        });
        btn.classList.add('active');
        btn.setAttribute('aria-pressed', 'true');

        // Optional UI row filter for routes table if present
        const mode = btn.getAttribute('data-mode');
        if (mode) {
          filterTableByMode(mode);
        }
      });

      // Keyboard navigation (ArrowLeft / ArrowRight)
      btn.addEventListener('keydown', (e) => {
        let targetIndex = null;
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
          targetIndex = (index + 1) % buttons.length;
        } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
          targetIndex = (index - 1 + buttons.length) % buttons.length;
        }

        if (targetIndex !== null) {
          e.preventDefault();
          buttons[targetIndex].focus();
          buttons[targetIndex].click();
        }
      });
    });
  });
}

/**
 * Client-side DOM filtering for routes tables by transit mode (Bus / Luas / All)
 */
function filterTableByMode(mode) {
  const rows = document.querySelectorAll('tbody tr[data-mode]');
  if (!rows.length) return;

  rows.forEach(row => {
    const rowMode = row.getAttribute('data-mode');
    if (mode === 'all' || rowMode === mode) {
      row.style.display = '';
    } else {
      row.style.display = 'none';
    }
  });
}

/**
 * Search input UI behavior to filter table rows by route code or destination
 */
function initTableSearchFilter() {
  const searchInput = document.getElementById('routeSearchInput');
  if (!searchInput) return;

  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.trim().toLowerCase();
    const rows = document.querySelectorAll('tbody tr[data-search]');

    rows.forEach(row => {
      const searchTarget = (row.getAttribute('data-search') || '').toLowerCase();
      if (!query || searchTarget.includes(query)) {
        row.style.display = '';
      } else {
        row.style.display = 'none';
      }
    });
  });
}

/**
 * Pure visual seconds counter for the "Feed updated X seconds ago" pill
 */
function initLiveFeedTickerVisual() {
  const feedUpdatedPill = document.querySelector('.feed-seconds-count');
  if (!feedUpdatedPill) return;

  let seconds = 38;
  setInterval(() => {
    seconds++;
    if (seconds > 60) {
      seconds = 4;
    }
    feedUpdatedPill.textContent = seconds;
  }, 1000);
}
