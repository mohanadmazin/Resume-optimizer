(() => {
  const MM_TO_PX = 96 / 25.4;
  const PAGE_H_MM = 297;
  const PAGE_W_MM = 210;
  const DEFAULTS = {
    targetPages: 'auto',
    minFontPt: 9,
    preferredFontPt: 10,
    maxFontPt: 11,
    minMarginMm: 12,
    preferredMarginMm: 18,
    maxMarginMm: 22,
    density: 'normal'
  };

  const paper = () => document.querySelector('#resumePreview');
  const button = () => document.querySelector('#autoAlignButton');
  const status = () => document.querySelector('#autoAlignStatus');

  function getSettings() {
    const target = document.querySelector('#autoAlignTargetPages');
    const density = document.querySelector('#autoAlignDensity');
    return {
      ...DEFAULTS,
      targetPages: target?.value || DEFAULTS.targetPages,
      density: density?.value || DEFAULTS.density
    };
  }

  function ensureControls() {
    const btn = button();
    if (!btn || document.querySelector('#autoAlignOptions')) return;

    const wrap = document.createElement('div');
    wrap.id = 'autoAlignOptions';
    wrap.className = 'auto-align-options';
    wrap.innerHTML = `
      <label>
        <span>Target pages</span>
        <select id="autoAlignTargetPages" aria-label="Target resume pages">
          <option value="auto">Auto</option>
          <option value="1">1 page</option>
          <option value="2">2 pages</option>
          <option value="3">3 pages</option>
        </select>
      </label>
      <label>
        <span>Spacing</span>
        <select id="autoAlignDensity" aria-label="Resume spacing density">
          <option value="spacious">Spacious</option>
          <option value="normal" selected>Normal</option>
          <option value="compact">Compact</option>
        </select>
      </label>
    `;
    btn.insertAdjacentElement('afterend', wrap);
  }

  function densityValues(density) {
    if (density === 'compact') return { line: 1.22, section: 0.86, paragraph: 0.78 };
    if (density === 'spacious') return { line: 1.42, section: 1.12, paragraph: 1.12 };
    return { line: 1.32, section: 1, paragraph: 1 };
  }

  function apply(el, fontPt, marginMm, density) {
    const d = densityValues(density);
    const horizontal = Math.min(25, Math.max(16, marginMm + 2));
    el.style.setProperty('--auto-font-pt', `${fontPt}pt`);
    el.style.setProperty('--auto-margin-mm', `${marginMm}mm`);
    el.style.setProperty('--auto-h-margin-mm', `${horizontal}mm`);
    el.style.setProperty('--auto-line-height', d.line);
    el.style.setProperty('--auto-section-scale', d.section);
    el.style.setProperty('--auto-paragraph-scale', d.paragraph);
    el.classList.add('auto-aligned');
  }

  function measure(el) {
    const cs = getComputedStyle(el);
    const pageHeight = PAGE_H_MM * MM_TO_PX;
    const paddingTop = parseFloat(cs.paddingTop) || 0;
    const paddingBottom = parseFloat(cs.paddingBottom) || 0;
    const usableHeight = Math.max(1, pageHeight - paddingTop - paddingBottom);
    const contentHeight = Math.max(1, el.scrollHeight - paddingTop - paddingBottom);
    const pages = Math.max(1, Math.ceil(contentHeight / usableHeight));
    const lastPageHeight = contentHeight - usableHeight * (pages - 1);
    const lastFill = Math.min(1, Math.max(0, lastPageHeight / usableHeight));
    const firstFill = Math.min(1, contentHeight / usableHeight);
    const overflow = Math.max(0, contentHeight - usableHeight * pages);
    return { pages, lastFill, firstFill, contentHeight, usableHeight, overflow };
  }

  function estimateTarget(metrics, target) {
    if (target !== 'auto') return Number(target);
    return metrics.pages;
  }

  function score(metrics, fontPt, marginMm, settings) {
    const targetPages = settings.targetPages === 'auto' ? metrics.pages : Number(settings.targetPages);
    const pagePenalty = Math.abs(metrics.pages - targetPages) * 180;
    const readabilityPenalty = Math.max(0, settings.preferredFontPt - fontPt) * 8;
    const tinyLastPage = metrics.pages > 1 && metrics.lastFill < 0.52 ? (0.52 - metrics.lastFill) * 110 : 0;
    const oversizedLastPage = metrics.pages > 1 && metrics.lastFill > 0.96 ? (metrics.lastFill - 0.96) * 18 : 0;
    const balanceTarget = metrics.pages === 1 ? 0.88 : 0.78;
    const balancePenalty = Math.abs(balanceTarget - metrics.lastFill) * 22;
    const marginPenalty = Math.abs(settings.preferredMarginMm - marginMm) * 0.5;
    const readabilityFloor = fontPt < settings.minFontPt ? 1000 : 0;
    const densityPenalty = settings.density === 'spacious' && metrics.pages > targetPages ? 12 : 0;
    return pagePenalty + readabilityPenalty + tinyLastPage + oversizedLastPage + balancePenalty + marginPenalty + readabilityFloor + densityPenalty;
  }

  function formatMessage(metrics, fontPt, marginMm, density) {
    const pageWord = metrics.pages === 1 ? 'page' : 'pages';
    const quality = metrics.lastFill >= 0.65 && metrics.lastFill <= 0.92 ? 'Balanced' : metrics.lastFill < 0.65 ? 'Compact final page' : 'Full final page';
    return `${metrics.pages} ${pageWord} • ${fontPt.toFixed(2)}pt text • ${marginMm}mm margins • ${quality} • ${density} spacing`;
  }

  function autoAlign() {
    const el = paper();
    if (!el) return;
    ensureControls();
    const btn = button();
    const stat = status();
    const settings = getSettings();

    if (btn) { btn.disabled = true; btn.textContent = 'Aligning…'; }
    if (stat) stat.textContent = 'Testing page count, typography, margins and spacing…';
    el.classList.add('auto-aligning');

    const fontStep = 0.25;
    let best = null;

    for (let fontPt = settings.minFontPt; fontPt <= settings.maxFontPt + 0.001; fontPt += fontStep) {
      for (let marginMm = settings.minMarginMm; marginMm <= settings.maxMarginMm; marginMm += 1) {
        apply(el, fontPt, marginMm, settings.density);
        void el.offsetHeight;
        const metrics = measure(el);
        const candidate = {
          score: score(metrics, fontPt, marginMm, settings),
          fontPt,
          marginMm,
          metrics
        };
        if (!best || candidate.score < best.score) best = candidate;
      }
    }

    if (best) {
      apply(el, best.fontPt, best.marginMm, settings.density);
      void el.offsetHeight;
      const finalMetrics = measure(el);
      const message = formatMessage(finalMetrics, best.fontPt, best.marginMm, settings.density);
      if (stat) stat.textContent = message;
      if (typeof window.showToast === 'function') window.showToast(`Resume aligned: ${message}.`);
    }

    el.classList.remove('auto-aligning');
    if (btn) { btn.disabled = false; btn.textContent = 'Auto Align Resume'; }
  }

  function resetAutoAlign() {
    const el = paper();
    if (!el) return;
    ['--auto-font-pt', '--auto-margin-mm', '--auto-h-margin-mm', '--auto-line-height', '--auto-section-scale', '--auto-paragraph-scale']
      .forEach(name => el.style.removeProperty(name));
    el.classList.remove('auto-aligned');
    if (status()) status().textContent = 'Auto Align reset — using template defaults.';
  }

  window.autoAlignResume = autoAlign;
  window.resetAutoAlignResume = resetAutoAlign;

  document.addEventListener('DOMContentLoaded', () => {
    ensureControls();
    button()?.addEventListener('click', autoAlign);
    document.querySelector('#autoAlignResetButton')?.addEventListener('click', resetAutoAlign);
  });
})();
