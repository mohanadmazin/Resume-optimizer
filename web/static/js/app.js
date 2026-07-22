/* Resume Optimizer — shared browser interactions */
(() => {
  const toast = document.getElementById('globalToast');
  let toastTimer;

  window.showGlobalToast = (message, isError = false) => {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.toggle('error', Boolean(isError));
    toast.classList.add('show');
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => toast.classList.remove('show'), 2800);
  };

  async function checkOllamaStatus() {
    const badge = document.getElementById('ollama-status');
    if (!badge) return;
    try {
      const response = await fetch('/api/ollama/status', { cache: 'no-store' });
      if (!response.ok) throw new Error('Status request failed');
      const data = await response.json();
      badge.innerHTML = data.connected
        ? '<span class="dot dot-green"></span> Ollama connected'
        : '<span class="dot dot-red"></span> Ollama offline';
      badge.title = data.connected && data.models.length
        ? `Models: ${data.models.join(', ')}`
        : data.url || '';
    } catch {
      badge.innerHTML = '<span class="dot dot-red"></span> Ollama offline';
    }
  }

  function setupSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggle = document.getElementById('sidebarToggle');
    const backdrop = document.getElementById('sidebarBackdrop');
    if (!sidebar || !toggle || !backdrop) return;

    const close = () => {
      sidebar.classList.remove('open');
      backdrop.hidden = true;
      toggle.setAttribute('aria-expanded', 'false');
    };
    const open = () => {
      sidebar.classList.add('open');
      backdrop.hidden = false;
      toggle.setAttribute('aria-expanded', 'true');
    };
    toggle.addEventListener('click', () => sidebar.classList.contains('open') ? close() : open());
    backdrop.addEventListener('click', close);
    sidebar.querySelectorAll('a').forEach(link => link.addEventListener('click', close));
    window.addEventListener('keydown', event => { if (event.key === 'Escape') close(); });
  }

  function setupConfirmationForms() {
    document.querySelectorAll('form[data-confirm]').forEach(form => {
      form.addEventListener('submit', event => {
        if (!window.confirm(form.dataset.confirm || 'Continue?')) event.preventDefault();
      });
    });
  }

  function setupProcessingForms() {
    document.querySelectorAll('form.processing-form').forEach(form => {
      form.addEventListener('submit', () => {
        const button = form.querySelector('button[type="submit"]');
        if (!button || button.disabled) return;
        button.disabled = true;
        button.dataset.originalText = button.textContent;
        button.textContent = 'Processing…';
      });
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    setupSidebar();
    setupConfirmationForms();
    setupProcessingForms();
    checkOllamaStatus();
  });
})();
