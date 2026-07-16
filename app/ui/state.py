from app.core.settings import load_settings, save_settings


class AppState:

    def __init__(self):

        self._settings = load_settings()

        # Resume workflow data
        self.resume = None
        self.resume_id = None
        self.optimized = None

        self.job_text = ""
        self.job_title = ""
        self.job_company = ""
        self.job_location = ""
        self.job_id = None

        self.ats = None

        # Missing keywords the user has left checked (selected) for the
        # AI optimizer to try to work in. None means "not customized yet"
        # i.e. use every missing keyword found by the ATS analysis.
        self.selected_keywords = None

        # Skill gap and salary analysis results
        self.skill_gap = None
        self.salary_estimate = None


    @property
    def theme(self):

        return self._settings.appearance.theme


    def set_theme(self, theme):

        self._settings.appearance.theme = theme

        save_settings(
            self._settings
        )


    @property
    def model(self):

        return self._settings.ai.model


    @property
    def ollama_url(self):

        return self._settings.ai.ollama_url