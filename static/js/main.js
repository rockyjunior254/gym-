/* ==========================================================================
   STRAKLY ATHLETICS & GYM MANAGEMENT SYSTEM — CLIENT INTERACTION SCRIPT
   Master Presentation: Lavender & Plum Design System, Collapsible Sidebars, Chart Color Engine
   ========================================================================== */

// 1. Coordinated Chart Color Palettes (Official Lavender/Plum Specification)
window.CHART_PALETTES = {
  lavender: {
    id: 'lavender',
    name: 'Lavender',
    colors: ['#9677CE', '#B8A2E5', '#D9CCF0', '#C2AFE8', '#E9DFF7'],
    primary: '#9677CE',
    bg: 'rgba(150, 119, 206, 0.14)'
  },
  plum: {
    id: 'plum',
    name: 'Plum',
    colors: ['#56365F', '#684A78', '#86669A', '#A78BBA', '#C9B8D8'],
    primary: '#684A78',
    bg: 'rgba(104, 74, 120, 0.14)'
  },
  orchid: {
    id: 'orchid',
    name: 'Orchid',
    colors: ['#8D62BC', '#B18BD8', '#D0B3EA', '#A98ACF', '#6E4D95'],
    primary: '#8D62BC',
    bg: 'rgba(141, 98, 188, 0.14)'
  },
  amethyst: {
    id: 'amethyst',
    name: 'Amethyst',
    colors: ['#7653B4', '#9876CF', '#B39BE2', '#D0BDEC', '#563B81'],
    primary: '#7653B4',
    bg: 'rgba(118, 83, 180, 0.14)'
  },
  soft_neutral: {
    id: 'soft_neutral',
    name: 'Soft Neutral',
    colors: ['#7F718D', '#A79BAF', '#C4B8CA', '#8D82A4', '#D9CEDF'],
    primary: '#7F718D',
    bg: 'rgba(127, 113, 141, 0.14)'
  }
};

// Global Chart Registry for Independent Palette Customization
window.ChartRegistry = {};

document.addEventListener('DOMContentLoaded', () => {
  // ------------------------------------------------------------------------
  // A. Mobile Public Navigation Toggle
  // ------------------------------------------------------------------------
  const publicNavToggle = document.getElementById('publicNavToggle');
  const navLinksWrap = document.getElementById('publicNavLinksWrap');

  if (publicNavToggle && navLinksWrap) {
    publicNavToggle.addEventListener('click', (e) => {
      e.preventDefault();
      navLinksWrap.classList.toggle('show');
    });
  }

  // ------------------------------------------------------------------------
  // B. Unified Collapsible Sidebar for All 3 Portals (Admin, Trainer, Member)
  // ------------------------------------------------------------------------
  initCollapsibleSidebar();

  // ------------------------------------------------------------------------
  // C. Auto-dismiss Flash Messages
  // ------------------------------------------------------------------------
  const flashes = document.querySelectorAll('.flash-message');
  flashes.forEach(flash => {
    setTimeout(() => {
      flash.style.opacity = '0';
      flash.style.transform = 'translateY(-10px)';
      flash.style.transition = 'all 0.3s ease-out';
      setTimeout(() => flash.remove(), 350);
    }, 4500);
  });

  // ------------------------------------------------------------------------
  // D. Global Dropdown Dismiss Listener
  // ------------------------------------------------------------------------
  document.addEventListener('click', (e) => {
    // Close chart palette popovers if clicked outside
    if (!e.target.closest('.chart-palette-btn') && !e.target.closest('.chart-palette-popover')) {
      document.querySelectorAll('.chart-palette-popover.show').forEach(pop => pop.classList.remove('show'));
    }
    // Close table dropdown menus if clicked outside
    if (!e.target.closest('.table-action-menu')) {
      document.querySelectorAll('.table-dropdown-menu.show').forEach(menu => menu.classList.remove('show'));
    }
  });

  // Re-run Lucide Icons on DOM ready
  if (window.lucide) {
    lucide.createIcons();
  }
});

/**
 * Universal Collapsible Sidebar Handler for Admin, Trainer, and Member Portals
 */
function initCollapsibleSidebar() {
  const sidebar = document.getElementById('appSidebar') || document.getElementById('fpSidebar') || document.querySelector('.app-sidebar') || document.querySelector('.fp-sidebar');
  const shell = document.querySelector('.app-shell') || document.querySelector('.fp-shell');
  const collapseToggle = document.getElementById('sidebarCollapseToggle');
  const mobileToggle = document.getElementById('mobileMenuToggle') || document.getElementById('fpMobileToggle');
  const backdrop = document.getElementById('sidebarBackdrop') || document.getElementById('fpMobileBackdrop') || document.querySelector('.sidebar-backdrop');

  if (!sidebar) return;

  const savedState = localStorage.getItem('gym_sidebar_collapsed');
  if (savedState === 'true') {
    sidebar.classList.add('collapsed');
    if (shell) shell.classList.add('sidebar-collapsed');
    if (collapseToggle) {
      const icon = collapseToggle.querySelector('i') || collapseToggle.querySelector('svg');
      if (icon) icon.setAttribute('data-lucide', 'chevron-right');
    }
  }

  if (collapseToggle) {
    collapseToggle.addEventListener('click', (e) => {
      e.preventDefault();
      sidebar.classList.toggle('collapsed');
      const isCollapsed = sidebar.classList.contains('collapsed');
      if (shell) shell.classList.toggle('sidebar-collapsed', isCollapsed);
      localStorage.setItem('gym_sidebar_collapsed', isCollapsed);
      
      const icon = collapseToggle.querySelector('i') || collapseToggle.querySelector('svg');
      if (icon) {
        icon.setAttribute('data-lucide', isCollapsed ? 'chevron-right' : 'chevron-left');
        if (window.lucide) lucide.createIcons();
      }
    });
  }

  // Mobile Slide-out Drawer
  if (mobileToggle) {
    mobileToggle.addEventListener('click', (e) => {
      e.preventDefault();
      sidebar.classList.toggle('mobile-open');
      sidebar.classList.toggle('open');
      if (backdrop) {
        backdrop.classList.toggle('active');
        backdrop.classList.toggle('open');
      }
    });
  }

  if (backdrop) {
    backdrop.addEventListener('click', () => {
      sidebar.classList.remove('mobile-open');
      sidebar.classList.remove('open');
      backdrop.classList.remove('active');
      backdrop.classList.remove('open');
    });
  }
}

// --------------------------------------------------------------------------
// E. Chart Color Palette Engine (Requirement #8)
// --------------------------------------------------------------------------
if (typeof Chart !== 'undefined') {
  Chart.defaults.color = '#826B7A';
  Chart.defaults.font.family = "'General Sans', 'Plus Jakarta Sans', sans-serif";
  Chart.defaults.plugins.tooltip.backgroundColor = '#3D2938';
  Chart.defaults.plugins.tooltip.titleColor = '#FFFFFF';
  Chart.defaults.plugins.tooltip.bodyColor = '#FFFFFF';
  Chart.defaults.plugins.tooltip.borderColor = '#F0DDE7';
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.cornerRadius = 8;
  Chart.defaults.plugins.legend.labels.color = '#3D2938';
  Chart.defaults.plugins.legend.labels.font = {
    family: "'General Sans', sans-serif",
    size: 11.5,
    weight: '600'
  };
  Chart.defaults.scale.grid = Chart.defaults.scale.grid || {};
  Chart.defaults.scale.grid.color = '#F9ECF3';
}

/**
 * Register a chart instance with unique identifier and apply stored or default palette
 */
function registerCustomChart(chartId, chartInstance) {
  window.ChartRegistry[chartId] = chartInstance;
  const savedPaletteKey = localStorage.getItem(`chart_palette_${chartId}`) || 'lavender';
  applyPaletteToChart(chartId, savedPaletteKey, false);
}

/**
 * Toggle the palette dropdown for a specific chart
 */
function toggleChartPalette(btn, chartId) {
  const popover = document.getElementById(`palette_popover_${chartId}`);
  if (!popover) return;
  const isCurrentlyOpen = popover.classList.contains('show');
  document.querySelectorAll('.chart-palette-popover.show').forEach(p => p.classList.remove('show'));
  if (!isCurrentlyOpen) {
    popover.classList.add('show');
  }
}

/**
 * Apply selected palette to a single chart immediately & persist preference
 */
function setChartPalette(chartId, paletteKey) {
  localStorage.setItem(`chart_palette_${chartId}`, paletteKey);
  applyPaletteToChart(chartId, paletteKey, true);
  
  // Close popover
  const popover = document.getElementById(`palette_popover_${chartId}`);
  if (popover) popover.classList.remove('show');
}

/**
 * Reset a chart to its default Rose Garden palette
 */
function resetChartPalette(chartId) {
  localStorage.removeItem(`chart_palette_${chartId}`);
  applyPaletteToChart(chartId, 'lavender', true);
  const popover = document.getElementById(`palette_popover_${chartId}`);
  if (popover) popover.classList.remove('show');
}

/**
 * Updates Chart.js dataset colors and triggers re-render
 */
function applyPaletteToChart(chartId, paletteKey, animate) {
  const chart = window.ChartRegistry[chartId];
  if (!chart) return;
  const palette = window.CHART_PALETTES[paletteKey] || window.CHART_PALETTES.lavender;

  // Update UI active indicator if present
  const popover = document.getElementById(`palette_popover_${chartId}`);
  if (popover) {
    popover.querySelectorAll('.chart-palette-option').forEach(opt => {
      opt.classList.toggle('active', opt.getAttribute('data-palette') === paletteKey);
    });
  }

  // Update button label badge if present
  const btnLabel = document.getElementById(`palette_label_${chartId}`);
  if (btnLabel) {
    btnLabel.textContent = palette.name;
  }

  const chartType = chart.config.type;
  chart.data.datasets.forEach((ds, i) => {
    if (chartType === 'doughnut' || chartType === 'pie') {
      ds.backgroundColor = palette.colors;
      ds.borderColor = '#FFFFFF';
      ds.borderWidth = 2;
    } else if (chartType === 'bar') {
      if (Array.isArray(ds.data) && ds.data.length > 1 && !ds.label) {
        ds.backgroundColor = palette.colors;
      } else {
        const color = palette.colors[i % palette.colors.length];
        ds.backgroundColor = color;
      }
      ds.borderRadius = 6;
    } else if (chartType === 'line') {
      const color = palette.colors[i % palette.colors.length];
      ds.borderColor = color;
      ds.pointBackgroundColor = color;
      ds.backgroundColor = palette.bg || 'rgba(231, 84, 156, 0.12)';
    }
  });

  chart.update(animate ? 'default' : 'none');
}

/**
 * Generate standard HTML Palette Dropdown component for any chart card
 */
function renderChartPaletteControl(chartId, currentPalette) {
  const currentKey = currentPalette || localStorage.getItem(`chart_palette_${chartId}`) || 'lavender';
  const curPal = window.CHART_PALETTES[currentKey] || window.CHART_PALETTES.lavender;

  let optionsHtml = '';
  Object.keys(window.CHART_PALETTES).forEach(key => {
    const pal = window.CHART_PALETTES[key];
    const dots = pal.colors.slice(0, 4).map(c => `<span class="chart-palette-dot" style="background:${c}"></span>`).join('');
    const isActive = key === currentKey ? 'active' : '';
    optionsHtml += `
      <div class="chart-palette-option ${isActive}" data-palette="${key}" onclick="setChartPalette('${chartId}', '${key}')">
        <span>${pal.name}</span>
        <div class="chart-palette-dots">${dots}</div>
      </div>
    `;
  });

  return `
    <div class="chart-palette-wrap" style="position: relative;">
      <button type="button" class="chart-palette-btn" onclick="toggleChartPalette(this, '${chartId}')" title="Customize Chart Colors">
        <i data-lucide="palette" style="width: 14px; height: 14px;"></i>
        <span id="palette_label_${chartId}">${curPal.name}</span>
      </button>
      <div class="chart-palette-popover" id="palette_popover_${chartId}">
        <div class="chart-palette-title">Select Color Palette</div>
        ${optionsHtml}
        <div class="chart-palette-reset">
          <button type="button" onclick="resetChartPalette('${chartId}')">Reset to Default</button>
        </div>
      </div>
    </div>
  `;
}

// --------------------------------------------------------------------------
// F. Table Action Dropdown & Modal Openers/Closers
// --------------------------------------------------------------------------
function toggleTableActionMenu(btn) {
  const menu = btn.nextElementSibling;
  if (!menu) return;
  const isShown = menu.classList.contains('show');
  document.querySelectorAll('.table-dropdown-menu.show').forEach(m => m.classList.remove('show'));
  if (!isShown) menu.classList.add('show');
}

function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.add('active');
    modal.classList.add('show');
    modal.style.display = 'flex';
  }
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.remove('active');
    modal.classList.remove('show');
    modal.style.display = 'none';
  }
}

// Legacy toggleSidebar mapping for existing onclick calls
function toggleSidebar() {
  const sidebar = document.getElementById('appSidebar') || document.getElementById('fpSidebar') || document.querySelector('.app-sidebar') || document.querySelector('.fp-sidebar');
  const backdrop = document.getElementById('sidebarBackdrop') || document.getElementById('fpMobileBackdrop');
  if (sidebar) {
    if (window.innerWidth <= 1024) {
      sidebar.classList.toggle('mobile-open');
      sidebar.classList.toggle('open');
      if (backdrop) {
        backdrop.classList.toggle('active');
        backdrop.classList.toggle('open');
      }
    } else {
      const collapseBtn = document.getElementById('sidebarCollapseToggle');
      if (collapseBtn) collapseBtn.click();
    }
  }
}

// Official Cash Receipt Printing
function printReceipt(receiptId) {
  const printContent = document.getElementById(receiptId);
  if (!printContent) return;
  
  const win = window.open('', '', 'height=700,width=800');
  win.document.write('<html><head><title>Official Receipt - Strakly Athletics</title>');
  win.document.write('<style>');
  win.document.write(`
    body { font-family: 'General Sans', sans-serif; background: #fff; color: #3D2938; padding: 40px; margin: 0; }
    .receipt-header { border-bottom: 2px solid #E7549C; padding-bottom: 20px; margin-bottom: 25px; text-align: center; }
    .receipt-title { font-size: 24px; font-weight: 800; color: #E7549C; text-transform: uppercase; margin: 0; }
    .receipt-sub { color: #826B7A; font-size: 13px; margin-top: 5px; }
    .receipt-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #F0DDE7; }
    .receipt-total { font-size: 20px; font-weight: bold; border-top: 2px solid #E7549C; margin-top: 20px; padding-top: 10px; color: #E7549C; }
    .stamp-box { border: 2px dashed #E7549C; padding: 15px; margin-top: 30px; text-align: center; font-weight: bold; color: #E7549C; }
  `);
  win.document.write('</style></head><body>');
  win.document.write(printContent.innerHTML);
  win.document.write('</body></html>');
  win.document.close();
  win.focus();
  setTimeout(() => {
    win.print();
    win.close();
  }, 250);
}
