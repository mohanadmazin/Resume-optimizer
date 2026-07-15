from app.config.config_manager import (
    load_config,
    save_config,
)


class AppState:

    def __init__(self):

        self.config = load_config()

        # Resume workflow data
        self.resume = None
        self.resume_id = None
        self.optimized = None

        self.job_text = ""
        self.job_title = ""
        self.job_company = ""
        self.job_id = None

        self.ats = None

        # Missing keywords the user has left checked (selected) for the
        # AI optimizer to try to work in. None means "not customized yet"
        # i.e. use every missing keyword found by the ATS analysis.
        self.selected_keywords = None


    @property
    def theme(self):

        return self.config.get(
            "theme",
            "light"
        )


    def set_theme(self, theme):

        self.config["theme"] = theme

        save_config(
            self.config
        )


    @property
    def model(self):

        return self.config.get(
            "model",
            "qwen-coder-dev:latest"
        )


    @property
    def ollama_url(self):

        return self.config.get(
            "ollama_url",
            "http://localhost:11434"
        )