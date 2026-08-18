(() => {
  const MM_TO_PX = 96 / 25.4;
  const PAGE_H_MM = 297;
  const BASE = { horizontalMarginMm: 22 };
  let activeConfig = null;
  let applying = false;

  const paper = () => document.querySelector('#resumePreview');
  const button = () => document.querySelector('#autoAlignButton');
  const status = () => document.querySelector('#autoAlignStatus');

  const densityValues = density => {
    if (density === 'compact') return { line: 1.20, section: 0.82, paragraph: 0.78 };
    if (density === 'spacious') return { line: 1.40, section: 1.12, paragraph: 1.12 };
    return { line: 1.30, section: 1.00, paragraph: 1.00 };
  };

  function ensureControls() {
    const btn = button();
    if (!btn || document.querySelector('#autoAlignOptions')) return;
    const wrap = document.createElement('div');
    wrap.id = 'autoAlignOptions';
    wrap.className = 'auto-align-options';
    wrap.innerHTML = `
      <label><span>Target pages</span><select id="autoAlignTargetPages" aria-label="Target resume pages">
        <option value="auto">Auto</option><option value="1">1 page</option><option value="2">2 pages</option><option value="3">3 pages</option>
      </select></label>
      <label><span>Spacing</span><select id="autoAlignDensity" aria-label="Resume spacing density">
        <option value="spacious">Spacious</option><option value="normal" selected>Normal</option><option value="compact">Compact</option>
      </select></label>`;
    btn.insertAdjacentElement('afterend', wrap);
  }

  function settings() {
    return {
      targetPages: document.querySelector('#autoAlignTargetPages')?.value || 'auto',
      density: document.querySelector('#autoAlignDensity')?.value || 'normal'
    };
  }

  function apply(el, cfg) {
    if (!el) return;
    const d = densityValues(cfg.density);
    const set = (node, name, value) => node?.style?.setProperty(name, value, 'important');

    set(el, '--auto-font-pt', `${cfg.fontPt}pt`);
    set(el, '--auto-margin-mm', `${cfg.marginMm}mm`);
    set(el, '--auto-h-margin-mm', `${BASE.horizontalMarginMm}mm`);
    set(el, '--auto-line-height', String(d.line));
    set(el, '--auto-section-scale', String(d.section));
    set(el, '--auto-paragraph-scale', String(d.paragraph));
    el.classList.add('auto-aligned');

    set(el, 'padding-top', `${cfg.marginMm}mm`);
    set(el, 'padding-bottom', `${cfg.marginMm}mm`);
    set(el, 'padding-left', `${BASE.horizontalMarginMm}mm`);
    set(el, 'padding-right', `${BASE.horizontalMarginMm}mm`);
    set(el, 'font-size', `${cfg.fontPt}pt`);
    set(el, 'line-height', String(d.line));

    el.querySelectorAll('.resume-summary, .resume-item-sub').forEach(n => {
      set(n, 'font-size', '10pt'); set(n, 'line-height', String(d.line));
    });
    el.querySelectorAll('.resume-item-heading strong').forEach(n => set(n, 'font-size', '10.5pt'));
    el.querySelectorAll('ul').forEach(n => {
      set(n, 'font-size', '9.5pt'); set(n, 'line-height', String(d.line));
      set(n, 'margin-top', `${5 * d.paragraph}px`);
    });
    el.querySelectorAll('.resume-skill-list, .resume-skill-grid').forEach(n => {
      set(n, 'font-size', '9pt'); set(n, 'line-height', String(d.line));
    });
    el.querySelectorAll('.resume-section').forEach(n => set(n, 'margin-top', `${19 * d.section}px`));
    el.querySelectorAll('.resume-section h2').forEach(n => {
      set(n, 'font-size', '11pt'); set(n, 'margin-bottom', `${8 * d.section}px`);
    });
    void el.offsetHeight;
  }

  function measure(el) {
    const cs = getComputedStyle(el);
    const pageHeight = PAGE_H_MM * MM_TO_PX;
    const pt = parseFloat(cs.paddingTop) || 0;
    const pb = parseFloat(cs.paddingBottom) || 0;
    const usable = Math.max(1, pageHeight - pt - pb);
    const content = Math.max(1, el.scrollHeight - pt - pb);
    const pages = Math.max(1, Math.ceil(content / usable));
    const last = content - usable * (pages - 1);
    return { pages, lastFill: Math.min(1, Math.max(0, last / usable)), contentHeight: content, usableHeight: usable };
  }

  function score(m, cfg, target) {
    const wanted = target === 'auto' ? m.pages : Number(target);
    const pagePenalty = Math.abs(m.pages - wanted) * 250;
    const tiny = m.pages > 1 && m.lastFill < 0.58 ? (0.58 - m.lastFill) * 150 : 0;
    const huge = m.pages > 1 && m.lastFill > 0.96 ? (m.lastFill - 0.96) * 80 : 0;
    const readability = Math.max(0, 10 - cfg.fontPt) * 10;
    const marginPreference = Math.abs(18 - cfg.marginMm) * 2;
    const balance = m.pages > 1 ? Math.abs(0.78 - m.lastFill) * 25 : Math.abs(0.88 - m.lastFill) * 15;
    return pagePenalty + tiny + huge + readability + marginPreference + balance;
  }

  function message(m, cfg) {
    const pages = `${m.pages} ${m.pages === 1 ? 'page' : 'pages'}`;
    const quality = m.lastFill < 0.58 ? 'needs more content on final page' : m.lastFill <= 0.92 ? 'balanced' : 'very full';
    return `${pages} • ${cfg.fontPt.toFixed(1)}pt • ${cfg.marginMm}mm top/bottom • ${BASE.horizontalMarginMm}mm left/right • ${cfg.density} spacing • ${quality}`;
  }

  function autoAlign() {
    if (applying) return;
    const el = paper();
    if (!el) return;
    ensureControls();
    const btn = button();
    const stat = status();
    const s = settings();
    applying = true;
    if (btn) { btn.disabled = true; btn.textContent = 'Aligning…'; }
    if (stat) stat.textContent = 'Testing page count, margins, typography and spacing live…';

    const candidates = [];
    for (const fontPt of [9.6, 9.8, 10.0, 10.2, 10.4]) {
      for (const marginMm of [18, 19, 20]) {
        for (const density of ['spacious', 'normal', 'compact']) candidates.push({ fontPt, marginMm, density });
      }
    }

    let best = null;
    for (const cfg of candidates) {
      apply(el, cfg);
      const m = measure(el);
      const candidate = { cfg, m, score: score(m, cfg, s.targetPages) };
      if (!best || candidate.score < best.score) best = candidate;
    }

    if (best) {
      activeConfig = best.cfg;
      apply(el, activeConfig);
      const finalMetrics = measure(el);
      if (stat) stat.textContent = `Live: ${message(finalMetrics, activeConfig)}`;
      if (typeof window.showToast === 'function') window.showToast(`Resume aligned live — ${message(finalMetrics, activeConfig)}.`);
    }

    applying = false;
    if (btn) { btn.disabled = false; btn.textContent = 'Auto Align Resume'; }
  }

  function resetAutoAlign() {
    activeConfig = null;
    const el = paper();
    if (!el) return;
    el.classList.remove('auto-aligned');
    ['--auto-font-pt','--auto-margin-mm','--auto-h-margin-mm','--auto-line-height','--auto-section-scale','--auto-paragraph-scale']
      .forEach(n => el.style.removeProperty(n));
    ['padding-top','padding-bottom','padding-left','padding-right','font-size','line-height'].forEach(n => el.style.removeProperty(n));
    el.querySelectorAll('[style]').forEach(n => {
      ['font-size','line-height','margin-top','margin-bottom'].forEach(p => n.style.removeProperty(p));
    });
    if (status()) status().textContent = 'Auto Align reset — using template defaults.';
  }

  function watchPreview() {
    const observer = new MutationObserver(() => {
      if (!activeConfig || applying) return;
      const el = paper();
      if (!el || el.dataset.autoAlignObserved === '1') return;
      el.dataset.autoAlignObserved = '1';
      requestAnimationFrame(() => apply(el, activeConfig));
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  // Do not replace the application's normal PDF/DOCX handlers. If a separate
  // parity exporter is installed, it can opt in through this hook; otherwise
  // the existing builder export code remains untouched.
  function installExportParity() {
    if (typeof window.exportAlignedResume !== 'function') return;
    document.addEventListener('click', async event => {
      const target = event.target?.closest?.('#exportPdfButton, #exportDocxButton');
      const el = paper();
      if (!target || !el?.classList.contains('auto-aligned')) return;
      event.preventDefault(); event.stopImmediatePropagation();
      await window.exportAlignedResume(target.id === 'exportPdfButton' ? 'pdf' : 'docx');
    }, true);
  }

  window.autoAlignResume = autoAlign;
  window.resetAutoAlignResume = resetAutoAlign;

  function init() {
    ensureControls();
    document.addEventListener('click', event => {
      if (event.target?.closest?.('#autoAlignButton')) autoAlign();
      if (event.target?.closest?.('#autoAlignResetButton')) resetAutoAlign();
    });
    watchPreview();
    installExportParity();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
