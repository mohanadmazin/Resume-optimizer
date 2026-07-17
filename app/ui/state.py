from app.core.settings import settings_service


class AppState:
    """Lightweight application state.

    Stores only identifiers and UI-only flags.  Actual domain objects
    are loaded on demand through application services when a page opens.
    """

    def __init__(self):
        self._svc = settings_service

        # ── Resume ──────────────────────────────────────────────────
        self.active_resume_id: int | None = None
        self._resume_cache = None

        # ── Job ─────────────────────────────────────────────────────
        self.active_job_id: int | None = None
        self._job_text_cache = ""
        self._job_title_cache = ""
        self._job_company_cache = ""
        self._job_location_cache = ""

        # ── Analysis ────────────────────────────────────────────────
        self.active_analysis_id: int | None = None
        self._ats_cache = None

        # ── Optimization ────────────────────────────────────────────
        self.active_optimization_id: int | None = None
        self._optimized_cache = None
        self._fact_guard_cache = None
        self._cover_letter_cache = ""

        # ── Skill gap / salary (ephemeral, not persisted by ID) ────
        self.skill_gap = None
        self.salary_estimate = None

        # ── Pipeline ────────────────────────────────────────────────
        self.pipeline_running = False
        self.pipeline_result = None

        # ── Selections ──────────────────────────────────────────────
        self.selected_keywords = None

    # ── Resume accessors ───────────────────────────────────────────

    @property
    def resume(self):
        return self._resume_cache

    @resume.setter
    def resume(self, value):
        self._resume_cache = value
        if value is not None and self.active_resume_id is None:
            self.active_resume_id = None  # caller must set separately

    @property
    def resume_id(self):
        return self.active_resume_id

    @resume_id.setter
    def resume_id(self, value):
        self.active_resume_id = value

    # ── Job accessors ──────────────────────────────────────────────

    @property
    def job_text(self):
        return self._job_text_cache

    @job_text.setter
    def job_text(self, value):
        self._job_text_cache = value

    @property
    def job_title(self):
        return self._job_title_cache

    @job_title.setter
    def job_title(self, value):
        self._job_title_cache = value

    @property
    def job_company(self):
        return self._job_company_cache

    @job_company.setter
    def job_company(self, value):
        self._job_company_cache = value

    @property
    def job_location(self):
        return self._job_location_cache

    @job_location.setter
    def job_location(self, value):
        self._job_location_cache = value

    @property
    def job_id(self):
        return self.active_job_id

    @job_id.setter
    def job_id(self, value):
        self.active_job_id = value

    # ── ATS / Analysis accessors ───────────────────────────────────

    @property
    def ats(self):
        return self._ats_cache

    @ats.setter
    def ats(self, value):
        self._ats_cache = value

    # ── Optimization accessors ─────────────────────────────────────

    @property
    def optimized(self):
        return self._optimized_cache

    @optimized.setter
    def optimized(self, value):
        self._optimized_cache = value

    @property
    def fact_guard(self):
        return self._fact_guard_cache

    @fact_guard.setter
    def fact_guard(self, value):
        self._fact_guard_cache = value

    @property
    def cover_letter_text(self):
        return self._cover_letter_cache

    @cover_letter_text.setter
    def cover_letter_text(self, value):
        self._cover_letter_cache = value

    # ── Settings shortcuts ─────────────────────────────────────────

    @property
    def theme(self):
        return self._svc.theme

    def set_theme(self, theme):
        patched = self._svc.settings.model_copy(deep=True)
        patched.appearance.theme = theme
        self._svc.save(patched)

    def reload_settings(self) -> None:
        """Reload settings from the SettingsService to pick up external changes."""
        self._svc = settings_service

    @property
    def model(self):
        return self._svc.model

    @property
    def ollama_url(self):
        return self._svc.ollama_url
