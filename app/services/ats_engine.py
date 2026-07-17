"""ATS analysis engine: keyword extraction, scoring and suggestions."""
import logging
import re
from collections import Counter
from typing import List, Tuple

from app.domain.analysis import ATSResult
from app.schemas import ResumeData

logger = logging.getLogger(__name__)

# Re-export for backward compatibility.
__all__ = ["ATSResult", "analyze", "extract_keywords", "extract_required_skills"]

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "can", "could", "did", "do",
    "does", "for", "from", "had", "has", "have", "her", "his", "how", "i", "if", "in", "into",
    "is", "it", "its", "may", "more", "most", "not", "of", "on", "or", "our", "out", "over",
    "per", "so", "such", "than", "that", "the", "their", "them", "then", "there", "these",
    "they", "this", "through", "to", "under", "up", "us", "was", "we", "well", "were", "what",
    "when", "where", "which", "while", "who", "whom", "why", "will", "with", "would", "you",
    "your", "about", "across", "all", "also", "any", "both", "each", "other", "some",
    # Job-posting boilerplate
    "ability", "able", "applicant", "apply", "benefits", "candidate", "candidates", "company",
    "day", "daily", "description", "duties", "employee", "equal", "etc", "excellent",
    "experience", "experienced", "familiar", "familiarity", "good", "great", "help", "ideal",
    "including", "job", "join", "knowledge", "looking", "member", "must", "new", "opportunity",
    "plus", "position", "preferred", "proficiency", "proficient", "related", "required",
    "requirements", "responsibilities", "responsible", "role", "salary", "seeking", "skills",
    "strong", "team", "understanding", "work", "working", "years", "year", "using", "used",
    "use", "within", "like", "e.g", "eg", "ie",
    # Generic words often mistaken for skills
    "environment", "support", "business", "solution", "solutions", "tools", "tool",
    "development", "management", "operations", "performance", "quality", "standards",
    "practices", "processes", "procedures", "documentation", "communication",
    "collaboration", "integration", "delivery", "engineering", "technology",
    "technologies", "platforms", "applications", "services", "infrastructure",
    "architecture", "strategies", "initiatives", "objectives", "requirements",
}

# Known technical skill tokens — only these are extracted as skills from JDs
_KNOWN_SKILLS: set[str] = {
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang", "rust",
    "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "perl", "haskell",
    "elixir", "dart", "lua", "sql", "nosql", "html", "css", "scss", "sass",
    # Frameworks
    "django", "flask", "fastapi", "spring", "springboot", "express", "node.js", "nodejs",
    "react", "reactjs", "vue", "vuejs", "angular", "angularjs", "svelte", "next.js", "nextjs",
    "rails", "laravel", "symfony", ".net", "dotnet", "asp.net",
    # Data
    "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch", "cassandra",
    "dynamodb", "sqlite", "oracle", "neo4j", "mssql", "sqlserver",
    # Cloud & DevOps
    "aws", "gcp", "azure", "docker", "kubernetes", "k8s", "terraform", "ansible",
    "jenkins", "github actions", "gitlab ci", "ci/cd", "ci cd", "prometheus", "grafana",
    "cloudformation", "helm", "argocd", ".CircleCI", "travis",
    # AI/ML
    "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn", "pandas", "numpy",
    "spark", "hadoop", "kafka", "airflow", "mlflow", "langchain", "openai",
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "neural networks", "transformers",
    # Tools
    "git", "linux", "bash", "powershell", "vim", "vscode", "jira", "confluence",
    "slack", "docker compose", "postman", "figma", "jupyter",
    # Methodologies
    "agile", "scrum", "kanban", "devops", "mlops", "tdd", "bdd", "saas", "paas", "iaas",
    "microservices", "serverless", "rest", "restful", "graphql", "grpc", "websocket",
    "oauth", "jwt", "oauth2",
    # Testing
    "pytest", "unittest", "jest", "mocha", "cypress", "selenium", "playwright",
    "junit", "xunit", "postman",
    # Misc
    "kafka", "rabbitmq", "nginx", "apache", "tomcat", "graphql", "protobuf", "grpc",
    "blockchain", "web3", "solidity", "ethereum",
}

SHORT_KEEP = {"c#", "go", "r", "ai", "ml", "qa", "ci", "cd", "ux", "ui", "c++", "aws", "sql", "api", "git"}

# Canonical skill name → set of known aliases (all lowercase).
# When matching, we check whether the resume contains ANY form of the skill.
SKILL_ALIASES: dict[str, set[str]] = {
    "javascript":   {"js", "javascript", "ecmascript", "es6", "es2015"},
    "typescript":   {"ts", "typescript"},
    "python":       {"python", "python3", "py"},
    "postgresql":   {"postgres", "postgresql", "psql", "pgsql"},
    "kubernetes":   {"k8s", "kubernetes", "kube"},
    "restful apis": {"rest", "restful", "restful apis", "rest api", "rest apis"},
    "ci/cd":        {"ci/cd", "ci cd", "continuous integration", "continuous delivery", "continuous deployment"},
    "machine learning": {"ml", "machine learning"},
    "deep learning": {"dl", "deep learning"},
    "react":        {"react", "reactjs", "react.js"},
    "vue":          {"vue", "vuejs", "vue.js"},
    "angular":      {"angular", "angularjs", "angular.js"},
    "node.js":      {"node", "nodejs", "node.js"},
    "golang":       {"go", "golang"},
    "rust":         {"rust", "rustlang"},
    "amazon web services": {"aws", "amazon web services", "amazon aws"},
    "google cloud platform": {"gcp", "google cloud", "google cloud platform"},
    "microsoft azure": {"azure", "microsoft azure"},
    "devops":       {"devops", "dev ops"},
    "natural language processing": {"nlp", "natural language processing"},
    "computer vision": {"cv", "computer vision"},
}

# Build reverse map: alias → canonical name
_ALIAS_TO_CANONICAL: dict[str, str] = {}
for canonical, aliases in SKILL_ALIASES.items():
    for alias in aliases:
        _ALIAS_TO_CANONICAL[alias] = canonical


# ── Section-aware extraction ────────────────────────────────────────────────

# Patterns that indicate a high-signal requirements section in a JD
_SECTION_HEADERS: re.Pattern[str] = re.compile(
    r"^\s*"
    r"(?:"
    r"requirements?"
    r"|qualifications?"
    r"|must[\s-]*have"
    r"|required[\s-]*skills?"
    r"|technical[\s-]*skills?"
    r"|what[\s\w-]*need"
    r"|skills[\s&]+qualifications?"
    r"|nice[\s-]*to[\s-]*have"
    r"|preferred[\s-]*qualifications?"
    r"|key[\s-]*skills?"
    r"|core[\s-]*skills?"
    r"|you[\s\w-]*need"
    r")"
    r"\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Weight tiers for keyword importance
_WEIGHT_SKILL_IN_SECTION: float = 1.0
_WEIGHT_SKILL_ANYWHERE: float = 0.8
_WEIGHTInSection: float = 0.5
_WEIGHT_FREQUENCY: float = 0.2


def _extract_section_text(jd_text: str) -> str:
    """Extract text from high-signal requirements sections of a JD.

    Finds section headers (Requirements, Qualifications, Must Have, etc.)
    and returns the text from those sections combined.  If no sections are
    found, returns the full JD text so frequency-based extraction still works.
    """
    lines = jd_text.splitlines()
    section_lines: list[str] = []
    in_section = False

    for line in lines:
        stripped = line.strip()

        # Blank line ends the current section
        if in_section and not stripped:
            in_section = False
            continue

        if _SECTION_HEADERS.match(stripped):
            in_section = True
            continue
        # A new non-empty header-like line (ALL CAPS or short header with colon) ends the section
        if in_section and stripped:
            if stripped.upper() == stripped and len(stripped) > 3:
                in_section = False
                continue
            if stripped.endswith(":") and len(stripped) < 60:
                candidate = stripped.rstrip(":").strip()
                if candidate and candidate.title() == candidate:
                    in_section = False
                    continue
        if in_section and stripped:
            section_lines.append(stripped)

    return "\n".join(section_lines) if section_lines else jd_text


def _extract_weighted_keywords(jd_text: str, top_n: int = 25) -> list[Tuple[str, float]]:
    """Extract keywords from a JD with importance weights.

    Priority:
    1. Known skill in a requirements section → weight 1.0
    2. Known skill anywhere in JD → weight 0.8
    3. Any word in a requirements section → weight 0.5
    4. Frequency-only mention → weight 0.2

    Returns up to *top_n* (keyword, weight) pairs sorted by weight
    descending, then frequency descending.
    """
    section_text = _extract_section_text(jd_text)
    full_lower = jd_text.lower()
    section_lower = section_text.lower()

    # Tokenize both
    def _tokens(text: str) -> list[str]:
        return [t.strip(".-/") for t in re.findall(r"[a-z][a-z0-9+#.\-/]*", text)]

    section_words = [
        t for t in _tokens(section_lower)
        if t and t not in STOPWORDS and (len(t) > 2 or t in SHORT_KEEP)
    ]
    full_words = [
        t for t in _tokens(full_lower)
        if t and t not in STOPWORDS and (len(t) > 2 or t in SHORT_KEEP)
    ]

    # Count frequencies
    section_counts = Counter(section_words)
    full_counts = Counter(full_words)

    # Bigrams from full text (frequency >= 2)
    full_bigrams: Counter = Counter()
    for first, second in zip(full_words, full_words[1:]):
        full_bigrams[f"{first} {second}"] += 1
    section_bigrams: Counter = Counter()
    for first, second in zip(section_words, section_words[1:]):
        section_bigrams[f"{first} {second}"] += 1

    candidates: dict[str, tuple[float, int]] = {}  # keyword → (weight, freq)

    def _update(word: str, weight: float, freq: int):
        existing = candidates.get(word)
        if existing is None or weight > existing[0] or (weight == existing[0] and freq > existing[1]):
            candidates[word] = (weight, freq)

    # Score bigrams
    for bg, count in full_bigrams.most_common(30):
        if count < 2:
            continue
        is_known = bg in _KNOWN_SKILLS or _canonicalize(bg) in SKILL_ALIASES
        in_section = bg in section_bigrams
        if is_known and in_section:
            _update(bg, _WEIGHT_SKILL_IN_SECTION, count)
        elif is_known:
            _update(bg, _WEIGHT_SKILL_ANYWHERE, count)
        elif in_section:
            _update(bg, _WEIGHTInSection, count)
        else:
            _update(bg, _WEIGHT_FREQUENCY, count)

    # Score unigrams
    for word, count in full_counts.most_common(top_n * 3):
        is_known = word in _KNOWN_SKILLS or _canonicalize(word) in SKILL_ALIASES
        in_section = word in section_counts
        if is_known and in_section:
            _update(word, _WEIGHT_SKILL_IN_SECTION, count)
        elif is_known:
            _update(word, _WEIGHT_SKILL_ANYWHERE, count)
        elif in_section:
            _update(word, _WEIGHTInSection, count)
        else:
            _update(word, _WEIGHT_FREQUENCY, count)

    # Remove unigrams that appear inside a kept bigram
    kept_bigrams = {kw for kw in candidates if " " in kw}
    for bg in kept_bigrams:
        for part in bg.split():
            candidates.pop(part, None)

    # Sort by weight desc, then frequency desc
    ranked = sorted(candidates.items(), key=lambda x: (x[1][0], x[1][1]), reverse=True)
    return [(kw, w) for kw, (w, _) in ranked[:top_n]]


def _canonicalize(skill: str) -> str:
    """Return the canonical form of a skill, or the original if unknown."""
    return _ALIAS_TO_CANONICAL.get(skill, skill)


def _skill_matches(resume_text: str, skill: str) -> bool:
    """Check if resume_text contains *skill* or any of its known aliases."""
    forms = SKILL_ALIASES.get(_canonicalize(skill), {skill})
    for form in forms:
        if _contains(resume_text, form):
            return True
    return False


def extract_keywords(text: str, top_n: int = 25) -> list[str]:
    tokens = [t.strip(".-/") for t in re.findall(r"[a-z][a-z0-9+#.\-/]*", text.lower())]
    words = [
        t for t in tokens
        if t and t not in STOPWORDS and (len(t) > 2 or t in SHORT_KEEP)
    ]
    counts = Counter(words)
    bigrams: Counter = Counter()
    for first, second in zip(words, words[1:]):
        bigrams[f"{first} {second}"] += 1
    top_bigrams = [b for b, c in bigrams.most_common(10) if c >= 2]
    singles = [w for w, _ in counts.most_common(top_n * 2) if w not in " ".join(top_bigrams)]
    return (top_bigrams + singles)[:top_n]


def extract_required_skills(text: str) -> list[str]:
    """Extract skill-like terms from a job description.

    Returns unique skill terms that appear in the JD and are known
    technical skills (from the curated vocabulary).  Generic words like
    "environment", "support", or "business" are excluded.
    """
    tokens = [t.strip(".-/") for t in re.findall(r"[a-z][a-z0-9+#.\-/]*", text.lower())]
    words = [
        t for t in tokens
        if t and t not in STOPWORDS and (len(t) > 2 or t in SHORT_KEEP)
    ]

    # Collect frequent bigrams first (e.g. "machine learning", "CI/CD")
    bigram_counts: Counter = Counter()
    for first, second in zip(words, words[1:]):
        bigram_counts[f"{first} {second}"] += 1
    # Keep bigrams that appear at least twice AND match a known skill
    bigrams = [
        b for b, c in bigram_counts.most_common(20)
        if c >= 2 and _canonicalize(b) in SKILL_ALIASES or b in _KNOWN_SKILLS
    ]

    # Single-word candidates — must be known skills
    bigram_words = set()
    for b in bigrams:
        bigram_words.update(b.split())
    singles = [
        w for w, _ in Counter(words).most_common(60)
        if w not in bigram_words and (w in _KNOWN_SKILLS or _canonicalize(w) in SKILL_ALIASES)
    ]

    seen: set[str] = set()
    result: list[str] = []
    for skill in bigrams + singles:
        if skill not in seen:
            seen.add(skill)
            result.append(skill)
    return result


def _contains(text: str, keyword: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def _resume_text(resume: ResumeData) -> str:
    parts = [resume.summary, " ".join(resume.skills)]
    for exp in resume.experience:
        parts += [exp.title, exp.company, " ".join(exp.bullets)]
    parts += [f"{edu.degree} {edu.institution}" for edu in resume.education]
    parts += resume.certifications
    return " ".join(p for p in parts if p)


def analyze(resume: ResumeData, jd_text: str) -> ATSResult:
    weighted_keywords = _extract_weighted_keywords(jd_text)
    keywords = [kw for kw, _ in weighted_keywords]
    weights = {kw: w for kw, w in weighted_keywords}

    structured = _resume_text(resume).strip()
    resume_text = structured if structured else resume.raw_text
    resume_text = resume_text.lower()

    matched = [k for k in keywords if _contains(resume_text, k)]
    matched_set = set(matched)
    missing = [k for k in keywords if k not in matched_set]

    # Weighted keyword score: sum of matched weights / sum of all weights
    total_weight = sum(weights.values())
    matched_weight = sum(weights[k] for k in matched)
    keyword_pct = round(100 * matched_weight / total_weight, 1) if total_weight else 0.0

    # Skills match: extract required skills from JD, check which appear in resume
    # Uses alias-aware matching so JS/JavaScript, K8s/Kubernetes etc. are recognized.
    required_skills = extract_required_skills(jd_text)
    matched_required = [s for s in required_skills if _skill_matches(resume_text, s)]
    missing_skills = [s for s in required_skills if s not in matched_required]
    skills_pct = (
        round(100 * len(matched_required) / len(required_skills), 1)
        if required_skills else 0.0
    )

    structure = 0
    structure += 4 if resume.contact.email else 0
    structure += 4 if resume.contact.phone else 0
    structure += 4 if resume.summary else 0
    structure += 4 if resume.skills else 0
    structure += 2 if resume.experience else 0
    structure += 2 if resume.education else 0

    formatting = 10
    word_count = len(resume_text.split())
    if word_count < 200 or word_count > 1200:
        formatting -= 5
    if not any(exp.bullets for exp in resume.experience):
        formatting -= 5

    score = int(round(keyword_pct * 0.5 + skills_pct * 0.25 + structure + formatting))
    score = max(0, min(100, score))

    logger.info(
        "ATS analysis: score=%d keyword_pct=%.1f skills_pct=%.1f missing=%d",
        score, keyword_pct, skills_pct, len(missing),
    )

    return ATSResult(
        ats_score=score,
        keyword_match_pct=keyword_pct,
        skills_match_pct=skills_pct,
        matched_keywords=matched,
        missing_keywords=missing,
        missing_skills=missing_skills,
        keyword_weights=weights,
        suggestions=_suggestions(resume, missing, weights, keyword_pct, skills_pct),
    )


def _suggestions(
    resume: ResumeData,
    missing: list[str],
    weights: dict[str, float],
    keyword_pct: float,
    skills_pct: float,
) -> list[str]:
    tips: list[str] = []
    if missing:
        # Sort by weight descending so the most important missing keywords come first
        sorted_missing = sorted(missing, key=lambda k: weights.get(k, 0), reverse=True)
        tips.append(f"Add these missing keywords where truthful: {', '.join(sorted_missing[:10])}.")
    if not resume.summary:
        tips.append("Add a professional summary tailored to the job (2-3 sentences).")
    if keyword_pct < 60:
        tips.append("Mirror the job description's terminology in your summary and experience bullets.")
    if not resume.skills:
        tips.append("Add a dedicated Skills section - ATS systems rely on it heavily.")
    elif skills_pct < 50:
        tips.append("Reorder your skills section so the most job-relevant skills appear first.")
    if resume.experience and not any(exp.bullets for exp in resume.experience):
        tips.append("Use bullet points in your experience section instead of paragraphs.")
    if not any(re.search(r"\d", b) for exp in resume.experience for b in exp.bullets):
        tips.append("Quantify achievements with numbers (%, $, team size) in your bullets.")
    if not resume.contact.linkedin:
        tips.append("Include your LinkedIn profile URL in the contact section.")
    if not tips:
        tips.append("Great coverage. Run AI optimization to polish wording and grammar.")
    return tips
