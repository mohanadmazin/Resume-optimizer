/* ResumeAI — shared browser interactions */
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
        : (data.error || data.url || '');
    } catch {
      badge.innerHTML = '<span class="dot dot-red"></span> Ollama offline';
    }
  }

  function setupSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggle = document.getElementById('sidebarToggle');
    const backdrop = document.getElementById('sidebarBackdrop');
    if (!sidebar || !toggle || !backdrop) return;
    const close = () => { sidebar.classList.remove('open'); backdrop.hidden = true; toggle.setAttribute('aria-expanded', 'false'); };
    const open = () => { sidebar.classList.add('open'); backdrop.hidden = false; toggle.setAttribute('aria-expanded', 'true'); };
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

  function processingCopy(form) {
    if (form.dataset.processingTitle) return [form.dataset.processingTitle, form.dataset.processingMessage || 'Working locally…'];
    const action = form.action || '';
    if (action.includes('/optimize/')) return ['Optimizing resume', 'Generating suggestions, checking facts, and preparing the review…'];
    if (action.includes('/cover-letter/')) return ['Generating cover letter', 'Matching your verified resume details to the target role…'];
    if (action.includes('/ats/')) return ['Analyzing ATS match', 'Comparing requirements, skills, keywords, structure, and formatting…'];
    if (action.includes('/upload')) return ['Importing resume', 'Reading the document and structuring its sections…'];
    return ['Processing request', 'ResumeAI is completing the requested action…'];
  }

  function setupProcessingForms() {
    const overlay = document.getElementById('processingOverlay');
    const title = document.getElementById('processingTitle');
    const message = document.getElementById('processingMessage');
    const cancel = document.getElementById('cancelProcessing');
    if (!overlay || !title || !message || !cancel) return;

    document.querySelectorAll('form.processing-form').forEach(form => {
      form.addEventListener('submit', async event => {
        if (event.defaultPrevented) return;
        const button = form.querySelector('button[type="submit"], button:not([type])');
        if (!button || button.disabled) return;
        event.preventDefault();

        const controller = new AbortController();
        const [heading, initialMessage] = processingCopy(form);
        const stages = [
          initialMessage,
          'Reviewing the selected resume and target job…',
          'Checking the result for consistency…',
          'Saving the completed output locally…'
        ];
        let stage = 0;
        title.textContent = heading;
        message.textContent = stages[stage];
        overlay.hidden = false;
        document.body.classList.add('processing-open');
        button.disabled = true;
        const originalText = button.textContent;
        button.textContent = 'Processing…';
        const stageTimer = window.setInterval(() => {
          stage = Math.min(stage + 1, stages.length - 1);
          message.textContent = stages[stage];
        }, 4500);
        const timeout = window.setTimeout(() => controller.abort('timeout'), 5 * 60 * 1000);

        const abortRequest = () => controller.abort('user');
        cancel.addEventListener('click', abortRequest, { once: true });
        try {
          const response = await fetch(form.action, {
            method: (form.method || 'POST').toUpperCase(),
            body: new FormData(form),
            credentials: 'same-origin',
            signal: controller.signal,
          });
          if (!response.ok && !response.redirected) {
            throw new Error(`Request failed (${response.status})`);
          }
          window.location.assign(response.url || window.location.href);
        } catch (error) {
          if (error.name === 'AbortError') {
            window.showGlobalToast('Request cancelled in the browser.', false);
          } else {
            console.error(error);
            window.showGlobalToast(error.message || 'The request could not be completed.', true);
          }
          overlay.hidden = true;
          document.body.classList.remove('processing-open');
          button.disabled = false;
          button.textContent = originalText;
        } finally {
          window.clearInterval(stageTimer);
          window.clearTimeout(timeout);
          cancel.removeEventListener('click', abortRequest);
        }
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
