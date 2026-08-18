(() => {
  const MM_TO_PX = 96 / 25.4;
  const PAGE_H_MM = 297;
  const BASE = { horizontalMarginMm: 22 };
  let activeConfig = null;
  let applying = false;
  let observerStarted = false;
  let lastAppliedSignature = "";

  const paper = () => document.querySelector('#resumePreview');
  const button = () => document.querySelector('#autoAlignButton');
  const status = () => document.querySelector('#autoAlignStatus');

  const densityValues = density => {
    if (density === 'compact') return { line: 1.20, section: 0.82, paragraph: 0.78 };
    if (density === 'spacious') return { line: 1.40, section: 1.12, paragraph: 1.12 };
    return { line: 1.30, section: 1.00, paragraph: 1.00 };
  };

  const signature = cfg => cfg ? `${cfg.fontPt}|${cfg.marginMm}|${cfg.density}` : '';

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

  function setImportant(node, name, value) {
    if (node?.style) node.style.setProperty(name, value, 'important');
  }

  function apply(el, cfg, force = false) {
    if (!el || !cfg) return;
    const sig = signature(cfg);
    if (!force && sig === lastAppliedSignature && el.classList.contains('auto-aligned')) return;
    const d = densityValues(cfg.density);

    el.classList.add('auto-aligning');
    setImportant(el, '--auto-font-pt', `${cfg.fontPt}pt`);
    setImportant(el, '--auto-margin-mm', `${cfg.marginMm}mm`);
    setImportant(el, '--auto-h-margin-mm', `${BASE.horizontalMarginMm}mm`);
    setImportant(el, '--auto-line-height', String(d.line));
    setImportant(el, '--auto-section-scale', String(d.section));
    setImportant(el, '--auto-paragraph-scale', String(d.paragraph));
    setImportant(el, 'padding-top', `${cfg.marginMm}mm`);
    setImportant(el, 'padding-bottom', `${cfg.marginMm}mm`);
    setImportant(el, 'padding-left', `${BASE.horizontalMarginMm}mm`);
    setImportant(el, 'padding-right', `${BASE.horizontalMarginMm}mm`);
    setImportant(el, 'font-size', `${cfg.fontPt}pt`);
    setImportant(el, 'line-height', String(d.line));

    el.querySelectorAll('.resume-summary, .resume-item-sub').forEach(n => {
      setImportant(n, 'font-size', '10pt');
      setImportant(n, 'line-height', String(d.line));
    });
    el.querySelectorAll('.resume-item-heading strong').forEach(n => setImportant(n, 'font-size', '10.5pt'));
    el.querySelectorAll('ul').forEach(n => {
      setImportant(n, 'font-size', '9.5pt');
      setImportant(n, 'line-height', String(d.line));
      setImportant(n, 'margin-top', `${5 * d.paragraph}px`);
      setImportant(n, 'margin-bottom', `${3 * d.paragraph}px`);
    });
    el.querySelectorAll('.resume-skill-list, .resume-skill-grid').forEach(n => {
      setImportant(n, 'font-size', '9pt');
      setImportant(n, 'line-height', String(d.line));
    });
    el.querySelectorAll('.resume-section').forEach(n => setImportant(n, 'margin-top', `${19 * d.section}px`));
    el.querySelectorAll('.resume-section h2').forEach(n => {
      setImportant(n, 'font-size', '11pt');
      setImportant(n, 'margin-bottom', `${8 * d.section}px`);
    });

    el.classList.remove('auto-aligning');
    el.classList.add('auto-aligned');
    lastAppliedSignature = sig;
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
    return {
      pages,
      lastFill: Math.min(1, Math.max(0, last / usable)),
      contentHeight: content,
      usableHeight: usable
    };
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

    const original = activeConfig;
    let best = null;
    try {
      for (const cfg of candidates) {
        apply(el, cfg, true);
        const m = measure(el);
        const candidate = { cfg, m, score: score(m, cfg, s.targetPages) };
        if (!best || candidate.score < best.score) best = candidate;
      }

      if (best) {
        activeConfig = { ...best.cfg };
        lastAppliedSignature = '';
        apply(el, activeConfig, true);
        const finalMetrics = measure(el);
        if (stat) stat.textContent = `Live: ${message(finalMetrics, activeConfig)}`;
        if (typeof window.showToast === 'function') window.showToast(`Resume aligned live — ${message(finalMetrics, activeConfig)}.`);
      } else if (original) {
        apply(el, original, true);
      }
    } finally {
      applying = false;
      if (btn) { btn.disabled = false; btn.textContent = 'Auto Align Resume'; }
    }
  }

  function resetAutoAlign() {
    activeConfig = null;
    lastAppliedSignature = '';
    const el = paper();
    if (!el) return;
    el.classList.remove('auto-aligned', 'auto-aligning');
    ['--auto-font-pt','--auto-margin-mm','--auto-h-margin-mm','--auto-line-height','--auto-section-scale','--auto-paragraph-scale']
      .forEach(n => el.style.removeProperty(n));
    ['padding-top','padding-bottom','padding-left','padding-right','font-size','line-height'].forEach(n => el.style.removeProperty(n));
    el.querySelectorAll('[style]').forEach(n => {
      ['font-size','line-height','margin-top','margin-bottom'].forEach(p => n.style.removeProperty(p));
    });
    if (status()) status().textContent = 'Auto Align reset — using template defaults.';
  }

  function collectCss() {
    const chunks = [];
    document.querySelectorAll('link[rel="stylesheet"]').forEach(link => {
      try {
        const sheet = Array.from(document.styleSheets).find(s => s.href === link.href);
        if (sheet?.cssRules) chunks.push(Array.from(sheet.cssRules).map(r => r.cssText).join('\n'));
      } catch (_) { /* same-origin styles only */ }
    });
    const inlineCss = document.querySelector('#resumePreviewStyle')?.textContent || '';
    return `${chunks.join('\n')}\n${inlineCss}`;
  }

  function exportHtml() {
    const el = paper();
    if (!el) throw new Error('Resume preview is unavailable.');
    if (!activeConfig) return el.innerHTML;
    const d = densityValues(activeConfig.density);
    const wrapperStyle = [
      'box-sizing:border-box',
      'width:210mm',
      `min-height:297mm`,
      `padding:${activeConfig.marginMm}mm ${BASE.horizontalMarginMm}mm`,
      `font-size:${activeConfig.fontPt}pt`,
      `line-height:${d.line}`,
      'background:#fff',
      'color:#182133',
      'font-family:Arial,sans-serif'
    ].join(';');
    return `<div class="resume-paper auto-aligned" style="${wrapperStyle}">${el.innerHTML}</div>`;
  }

  async function downloadResponse(response, extension, fallbackMessage) {
    if (!response.ok) {
      const detail = await response.text().catch(() => '');
      throw new Error(detail || fallbackMessage);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${safeFileName(window.resumeAutoAlignFileName || 'resume')}.${extension}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 5000);
  }

  function safeFileName(value) {
    return String(value || '').toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'resume';
  }

  async function exportAlignedResume(format) {
    const el = paper();
    if (!el || !el.classList.contains('auto-aligned')) return false;
    const fileName = safeFileName(document.querySelector('#fullName')?.value || 'resume');
    window.resumeAutoAlignFileName = fileName;
    const body = {
      html: exportHtml(),
      css: collectCss(),
      filename: `${fileName}.${format}`,
      autoAlign: activeConfig ? { ...activeConfig, horizontalMarginMm: BASE.horizontalMarginMm } : null
    };
    const response = await fetch(`/api/builder/export/${format}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    await downloadResponse(response, format, `${format.toUpperCase()} export failed.`);
    if (typeof window.showToast === 'function') window.showToast(`${format.toUpperCase()} exported with the live Auto Align layout.`);
    return true;
  }

  function installExportParity() {
    if (document.documentElement.dataset.autoAlignExportInstalled === '1') return;
    document.documentElement.dataset.autoAlignExportInstalled = '1';
    document.addEventListener('click', async event => {
      const target = event.target?.closest?.('#exportPdfButton, #exportDocxButton');
      const el = paper();
      if (!target || !el?.classList.contains('auto-aligned')) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      target.disabled = true;
      const originalText = target.textContent;
      target.textContent = target.id === 'exportPdfButton' ? 'Exporting PDF…' : 'Exporting DOCX…';
      try {
        await exportAlignedResume(target.id === 'exportPdfButton' ? 'pdf' : 'docx');
      } catch (error) {
        console.error('Aligned export failed:', error);
        if (typeof window.showToast === 'function') window.showToast(error.message || 'Aligned export failed.');
      } finally {
        target.disabled = false;
        target.textContent = originalText;
      }
    }, true);
  }

  window.autoAlignResume = autoAlign;
  window.resetAutoAlignResume = resetAutoAlign;
  window.isResumeAutoAligned = () => Boolean(activeConfig && paper()?.classList.contains('auto-aligned'));
  window.exportAlignedResume = exportAlignedResume;
  window.getAutoAlignConfig = () => activeConfig ? { ...activeConfig, horizontalMarginMm: BASE.horizontalMarginMm } : null;

  function watchPreview() {
    if (observerStarted) return;
    observerStarted = true;
    const observer = new MutationObserver(mutations => {
      if (!activeConfig || applying) return;
      const relevant = mutations.some(m => m.type === 'childList');
      if (!relevant) return;
      const el = paper();
      if (!el) return;
      requestAnimationFrame(() => {
        if (!applying && activeConfig && paper() === el) apply(el, activeConfig, true);
      });
    });
    // Observe DOM replacements only. Do NOT observe attributes: Auto Align itself changes
    // styles, and observing attributes creates an endless mutation/reapply loop.
    observer.observe(document.body, { childList: true, subtree: true, attributes: false });
  }

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
