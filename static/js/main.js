/* ==========================================================================
   STRAKLY GYM MANAGEMENT SYSTEM — CLIENT INTERACTION SCRIPT
   Master Presentation: Light Theme & Responsive Sidebar Navigation
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Mobile Public Navigation Toggle
  const publicNavToggle = document.getElementById('publicNavToggle');
  const navLinks = document.querySelector('.nav-links');

  if (publicNavToggle && navLinks) {
    publicNavToggle.addEventListener('click', () => {
      const isVisible = navLinks.style.display === 'flex';
      navLinks.style.display = isVisible ? 'none' : 'flex';
      if (!isVisible) {
        navLinks.style.flexDirection = 'column';
        navLinks.style.position = 'absolute';
        navLinks.style.top = '100%';
        navLinks.style.left = '0';
        navLinks.style.width = '100%';
        navLinks.style.backgroundColor = '#FFFFFF';
        navLinks.style.padding = '1.5rem';
        navLinks.style.borderBottom = '1px solid #E9DFDB';
        navLinks.style.boxShadow = '0 10px 25px rgba(30,43,37,0.08)';
      }
    });
  }

  // 2. Fixed 232px Collapsible Sidebar Navigation
  const sidebar = document.getElementById('appSidebar') || document.querySelector('.app-sidebar');
  const collapseToggle = document.getElementById('sidebarCollapseToggle');
  const mobileMenuBtn = document.getElementById('mobileMenuToggle');
  const backdrop = document.getElementById('sidebarBackdrop') || document.querySelector('.sidebar-backdrop');

  if (sidebar && collapseToggle) {
    const savedState = localStorage.getItem('gym_sidebar_collapsed');
    if (savedState === 'true') {
      sidebar.classList.add('collapsed');
      const icon = collapseToggle.querySelector('i');
      if (icon) icon.setAttribute('data-lucide', 'chevron-right');
    }

    collapseToggle.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
      const isCollapsed = sidebar.classList.contains('collapsed');
      localStorage.setItem('gym_sidebar_collapsed', isCollapsed);
      const icon = collapseToggle.querySelector('i');
      if (icon) {
        icon.setAttribute('data-lucide', isCollapsed ? 'chevron-right' : 'chevron-left');
        if (window.lucide) lucide.createIcons();
      }
    });
  }

  // Mobile Slide-out Drawer
  if (sidebar && mobileMenuBtn) {
    mobileMenuBtn.addEventListener('click', () => {
      sidebar.classList.add('mobile-open');
      if (backdrop) backdrop.classList.add('active');
    });
  }

  if (backdrop && sidebar) {
    backdrop.addEventListener('click', () => {
      sidebar.classList.remove('mobile-open');
      backdrop.classList.remove('active');
    });
  }

  // 3. Auto-dismiss Flash Messages
  const flashes = document.querySelectorAll('.flash-message');
  flashes.forEach(flash => {
    setTimeout(() => {
      flash.style.opacity = '0';
      flash.style.transform = 'translateY(-10px)';
      flash.style.transition = 'all 0.3s ease-out';
      setTimeout(() => flash.remove(), 350);
    }, 4500);
  });

  // Re-run Lucide on load
  if (window.lucide) {
    lucide.createIcons();
  }
});

// Configure Global Chart.js Light Palette Defaults (Order 1-6)
if (typeof Chart !== 'undefined') {
  Chart.defaults.color = '#566860';
  Chart.defaults.font.family = "'Inter', sans-serif";
  Chart.defaults.plugins.tooltip.backgroundColor = '#1E2B25';
  Chart.defaults.plugins.tooltip.titleColor = '#FFFFFF';
  Chart.defaults.plugins.tooltip.bodyColor = '#FFFFFF';
  Chart.defaults.plugins.tooltip.borderColor = '#E9DFDB';
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.legend.labels.color = '#1E2B25';
  Chart.defaults.scale.grid.color = '#E9DFDB';
}

// Global Modal Dialog Openers & Closers
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.add('active');
    modal.style.display = 'flex';
  }
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.remove('active');
    modal.style.display = 'none';
  }
}

// Receipt Print Helper (Pearl/Cloud Light Layout)
function printReceipt(receiptId) {
  const printContent = document.getElementById(receiptId);
  if (!printContent) return;
  
  const win = window.open('', '', 'height=700,width=800');
  win.document.write('<html><head><title>Official Receipt - Strakly Gym</title>');
  win.document.write('<style>');
  win.document.write(`
    body { font-family: 'Inter', sans-serif; background: #fff; color: #1E2B25; padding: 40px; margin: 0; }
    .receipt-header { border-bottom: 2px solid #2F6B4F; padding-bottom: 20px; margin-bottom: 25px; text-align: center; }
    .receipt-title { font-family: 'Archivo', sans-serif; font-size: 24px; font-weight: 800; color: #2F6B4F; text-transform: uppercase; margin: 0; }
    .receipt-sub { color: #566860; font-size: 13px; margin-top: 5px; }
    .receipt-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #E9DFDB; }
    .receipt-total { font-size: 20px; font-weight: bold; border-top: 2px solid #2F6B4F; margin-top: 20px; padding-top: 10px; color: #2F6B4F; }
    .stamp-box { border: 2px dashed #2F6B4F; padding: 15px; margin-top: 30px; text-align: center; font-weight: bold; color: #2F6B4F; }
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
