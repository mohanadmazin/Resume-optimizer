(() => {
  const MM_TO_PX = 96 / 25.4;
  const PAGE_H_MM = 297;
  // The current DOCX export template uses these exact baseline dimensions.
  // Keeping Auto Align on the same baseline prevents the browser preview from
  // drifting away from exported PDF/DOCX pagination and typography.
  const EXPORT_BASELINE = {
    fontPt: 10,
    marginMm: 18,
    horizontalMarginMm: 22,
  };
  const DEFAULTS = {
    targetPages: 'auto',
    minFontPt: EXPORT_BASELINE.fontPt,
    preferredFontPt: EXPORT_BASELINE.fontPt,
    maxFontPt: EXPORT_BASELINE.fontPt,
    minMarginMm: EXPORT_BASELINE.marginMm,
    preferredMarginMm: EXPORT_BASELINE.marginMm,
    maxMarginMm: EXPORT_BASELINE.marginMm,
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
    el.style.setProperty('--auto-font-pt', `${fontPt}pt`);
    el.style.setProperty('--auto-margin-mm', `${marginMm}mm`);
    el.style.setProperty('--auto-h-margin-mm', `${EXPORT_BASELINE.horizontalMarginMm}mm`);
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

  function score(metrics, fontPt, marginMm, settings) {
    const targetPages = settings.targetPages === 'auto' ? metrics.pages : Number(settings.targetPages);
    const pagePenalty = Math.abs(metrics.pages - targetPages) * 180;
    const readabilityPenalty = Math.max(0, settings.preferredFontPt - fontPt) * 8;
    const tinyLastPage = metrics.pages > 1 && metrics.lastFill < 0.52 ? (0.52 - metrics.lastFill) * 110 : 0;
    const oversizedLastPage = metrics.pages > 1 && metrics.lastFill > 0.96 ? (metrics.lastFill - 0.96) * 18 : 0;
    const balanceTarget = metrics.pages === 1 ? 0.88 : 0.78;
    const balancePenalty = Math.abs(balanceTarget - metrics.lastFill) * 22;
    const marginPenalty = Math.abs(settings.preferredMarginMm - marginMm) * 0.5;
    return pagePenalty + readabilityPenalty + tinyLastPage + oversizedLastPage + balancePenalty + marginPenalty;
  }

  function formatMessage(metrics, fontPt, marginMm, density) {
    const pageWord = metrics.pages === 1 ? 'page' : 'pages';
    const quality = metrics.lastFill >= 0.65 && metrics.lastFill <= 0.92 ? 'Balanced' : metrics.lastFill < 0.65 ? 'Compact final page' : 'Full final page';
    return `${metrics.pages} ${pageWord} • ${fontPt.toFixed(2)}pt text • ${marginMm}mm top/bottom • ${EXPORT_BASELINE.horizontalMarginMm}mm left/right • ${quality} • ${density} spacing`;
  }

  function collectResumeCss() {
    const rules = [];
    for (const sheet of Array.from(document.styleSheets)) {
      try {
        if (!sheet.cssRules) continue;
        for (const rule of Array.from(sheet.cssRules)) {
          const text = rule.cssText || '';
          if (text.includes('.resume-paper') || text.includes('.resume-') || text.includes('.auto-align')) {
            rules.push(text);
          }
        }
      } catch {
        // Cross-origin stylesheets are intentionally ignored.
      }
    }
    return rules.join('\n');
  }

  function exportFilename(extension) {
    const raw = String(window.resumeBuilderExportName || document.querySelector('#fullName')?.value || 'resume');
    const safe = raw.replace(/[^A-Za-z0-9._-]+/g, '-').replace(/^-+|-+$/g, '') || 'resume';
    return `${safe}.${extension}`;
  }

  async function exportAligned(format) {
    const preview = paper();
    if (!preview || !preview.classList.contains('auto-aligned')) return false;

    const buttonId = format === 'pdf' ? '#exportPdfButton' : '#exportDocxButton';
    const btn = document.querySelector(buttonId);
    const originalText = btn?.textContent || '';
    if (btn) {
      btn.disabled = true;
      btn.textContent = format === 'pdf' ? 'Exporting PDF…' : 'Exporting DOCX…';
    }

    try {
      // Inject the active Auto Align stylesheet into the HTML itself. The
      // server's PDF renderer receives the preview HTML, so this makes the
      // exported document use the same live layout rather than the dashboard's
      // default stylesheet alone.
      const html = `${preview.innerHTML}<style>${collectResumeCss()}</style>`;
      const body = {
        html,
        filename: exportFilename(format),
        // Deliberately omit `state` for DOCX. When state is supplied the server
        // takes the legacy structured exporter path, which has fixed typography
        // and margins. The HTML path uses the same layout as the live preview.
      };
      const response = await fetch(`/api/builder/export/${format}`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const detail = await response.text().catch(() => '');
        throw new Error(detail || `Export failed (${response.status})`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = exportFilename(format);
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      if (typeof window.showToast === 'function') window.showToast(`Aligned ${format.toUpperCase()} exported using the live preview layout.`);
      return true;
    } catch (error) {
      console.error(`Aligned ${format} export failed:`, error);
      if (typeof window.showToast === 'function') window.showToast(error.message || `Could not export ${format.toUpperCase()}.`);
      return true;
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = originalText;
      }
    }
  }

  function installExportParity() {
    document.addEventListener('click', async (event) => {
      const target = event.target?.closest?.('#exportPdfButton, #exportDocxButton');
      if (!target || !paper()?.classList.contains('auto-aligned')) return;

      // Capture phase runs before the existing script.js button handlers.
      event.preventDefault();
      event.stopImmediatePropagation();
      await exportAligned(target.id === 'exportPdfButton' ? 'pdf' : 'docx');
    }, true);
  }

  function autoAlign() {
    const el = paper();
    if (!el) return;
    ensureControls();
    const btn = button();
    const stat = status();
    const settings = getSettings();

    if (btn) { btn.disabled = true; btn.textContent = 'Aligning…'; }
    if (stat) stat.textContent = 'Balancing page count, typography, margins and spacing…';
    el.classList.add('auto-aligning');

    // The export-safe font and paper edges are intentionally fixed. The
    // optimizer uses spacing density to balance pages without creating a
    // browser/export mismatch.
    let best = null;
    for (const density of ['spacious', 'normal', 'compact']) {
      apply(el, EXPORT_BASELINE.fontPt, EXPORT_BASELINE.marginMm, density);
      void el.offsetHeight;
      const metrics = measure(el);
      const candidate = {
        score: score(metrics, EXPORT_BASELINE.fontPt, EXPORT_BASELINE.marginMm, { ...settings, density }),
        fontPt: EXPORT_BASELINE.fontPt,
        marginMm: EXPORT_BASELINE.marginMm,
        density,
        metrics
      };
      if (!best || candidate.score < best.score) best = candidate;
    }

    if (best) {
      apply(el, best.fontPt, best.marginMm, best.density);
      void el.offsetHeight;
      const finalMetrics = measure(el);
      const message = formatMessage(finalMetrics, best.fontPt, best.marginMm, best.density);
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
    installExportParity();
  });
})();
