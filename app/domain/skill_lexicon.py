"""Canonical skill names and aliases shared by ATS and fact validation."""
import re


SKILL_ALIASES: dict[str, frozenset[str]] = {
    "javascript": frozenset({"javascript", "js", "ecmascript", "es6", "es2015"}),
    "typescript": frozenset({"typescript", "ts"}),
    "python": frozenset({"python", "python3", "py"}),
    "postgresql": frozenset({"postgresql", "postgres", "psql", "pgsql"}),
    "kubernetes": frozenset({"kubernetes", "k8s", "kube"}),
    "terraform": frozenset({"terraform"}),
    "restful apis": frozenset({"rest", "restful", "restful apis", "rest api", "rest apis"}),
    "ci/cd": frozenset({"ci/cd", "ci cd", "continuous integration", "continuous delivery", "continuous deployment"}),
    "machine learning": frozenset({"ml", "machine learning"}),
    "deep learning": frozenset({"dl", "deep learning"}),
    "react": frozenset({"react", "reactjs", "react.js"}),
    "vue": frozenset({"vue", "vuejs", "vue.js"}),
    "angular": frozenset({"angular", "angularjs", "angular.js"}),
    "node.js": frozenset({"node", "nodejs", "node.js"}),
    "golang": frozenset({"go", "golang"}),
    "rust": frozenset({"rust", "rustlang"}),
    "amazon web services": frozenset({"amazon web services", "amazon aws", "aws"}),
    "google cloud platform": frozenset({"gcp", "google cloud", "google cloud platform"}),
    "microsoft azure": frozenset({"azure", "microsoft azure"}),
    "devops": frozenset({"devops", "dev ops"}),
    "natural language processing": frozenset({"nlp", "natural language processing"}),
    "computer vision": frozenset({"cv", "computer vision"}),
}


def _contains_phrase(text: str, phrase: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(phrase.casefold()) + r"(?![a-z0-9])"
    return bool(re.search(pattern, text.casefold()))


def extract_skills(text: str) -> set[str]:
    """Return canonical skills mentioned in *text*, regardless of casing."""
    return {
        canonical
        for canonical, aliases in SKILL_ALIASES.items()
        if any(_contains_phrase(text, alias) for alias in aliases)
    }
