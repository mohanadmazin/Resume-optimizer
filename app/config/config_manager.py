import json
from pathlib import Path


CONFIG_FILE = Path(__file__).parent / "config.json"


DEFAULT_CONFIG = {
    "theme": "light",
    "ollama_url": "http://localhost:11434",
    "model": "qwen3",
    "available_models": [
        "qwen3",
        "llama3.1"
    ],
    "temperature": 0.3,
}


def load_config():

    if not CONFIG_FILE.exists():

        save_config(
            DEFAULT_CONFIG
        )

        return DEFAULT_CONFIG.copy()


    try:

        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)


        config = DEFAULT_CONFIG.copy()

        config.update(
            data
        )

        return config


    except Exception:

        return DEFAULT_CONFIG.copy()



def save_config(config):

    with open(
        CONFIG_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            config,
            f,
            indent=4
        )



def update_config(key, value):

    config = load_config()

    config[key] = value

    save_config(
        config
    )