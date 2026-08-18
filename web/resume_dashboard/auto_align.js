(() => {
  const MM_TO_PX = 96 / 25.4;
  const PAGE_H_MM = 297;
  const MIN_FONT_PT = 9;
  const MAX_FONT_PT = 10.5;
  const MIN_MARGIN_MM = 12;
  const MAX_MARGIN_MM = 22;

  const paper = () => document.querySelector('#resumePreview');

  function apply(el, fontPt, marginMm) {
    el.style.setProperty('--auto-font-pt', `${fontPt}pt`);
    el.style.setProperty('--auto-margin-mm', `${marginMm}mm`);
    el.style.setProperty('--auto-h-margin-mm', `${Math.max(16, marginMm + 3)}mm`);
    el.classList.add('auto-aligned');
  }

  function measure(el) {
    const cs = getComputedStyle(el);
    const pageHeight = PAGE_H_MM * MM_TO_PX;
    const verticalPadding = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);
    const usableHeight = Math.max(1, pageHeight - verticalPadding);
    const contentHeight = Math.max(1, el.scrollHeight - verticalPadding);
    const pages = Math.max(1, Math.ceil(contentHeight / usableHeight));
    const lastPageHeight = contentHeight - usableHeight * (pages - 1);
    const lastFill = Math.min(1, Math.max(0, lastPageHeight / usableHeight));
    return { pages, lastFill };
  }

  function score(metrics, fontPt, marginMm) {
    const lastTarget = metrics.pages === 1 ? 0.88 : 0.84;
    const lastPenalty = Math.abs(lastTarget - metrics.lastFill) * 8;
    const readabilityPenalty = Math.abs(10 - fontPt) * 1.5;
    const marginPenalty = Math.abs(18 - marginMm) * 0.08;
    const tinyPagePenalty = metrics.pages > 1 && metrics.lastFill < 0.45 ? 20 : 0;
    return metrics.pages * 20 + lastPenalty + readabilityPenalty + marginPenalty + tinyPagePenalty;
  }

  function autoAlign() {
    const el = paper();
    if (!el) return;
    const button = document.querySelector('#autoAlignButton');
    const status = document.querySelector('#autoAlignStatus');
    if (button) { button.disabled = true; button.textContent = 'Aligning…'; }
    if (status) status.textContent = 'Testing professional page layouts…';
    el.classList.add('auto-aligning');

    let best = null;
    for (let fontPt = MIN_FONT_PT; fontPt <= MAX_FONT_PT + 0.001; fontPt += 0.25) {
      for (let marginMm = MIN_MARGIN_MM; marginMm <= MAX_MARGIN_MM; marginMm += 1) {
        apply(el, fontPt, marginMm);
        void el.offsetHeight;
        const metrics = measure(el);
        const candidate = { score: score(metrics, fontPt, marginMm), fontPt, marginMm, metrics };
        if (!best || candidate.score < best.score) best = candidate;
      }
    }

    if (best) {
      apply(el, best.fontPt, best.marginMm);
      const finalMetrics = measure(el);
      const message = `${finalMetrics.pages} page${finalMetrics.pages === 1 ? '' : 's'} • ${best.fontPt.toFixed(2)}pt text • ${best.marginMm}mm vertical margins`;
      if (status) status.textContent = message;
      if (typeof window.showToast === 'function') window.showToast(`Resume aligned: ${message}.`);
    }

    el.classList.remove('auto-aligning');
    if (button) { button.disabled = false; button.textContent = 'Auto Align Resume'; }
  }

  window.autoAlignResume = autoAlign;
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelector('#autoAlignButton')?.addEventListener('click', autoAlign);
  });
})();
