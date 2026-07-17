"""ATS analysis engine: keyword extraction, scoring and suggestions."""
import logging
import re
from collections import Counter
from typing import List

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
    keywords = extract_keywords(jd_text)
    structured = _resume_text(resume).strip()
    resume_text = structured if structured else resume.raw_text
    resume_text = resume_text.lower()

    matched = [k for k in keywords if _contains(resume_text, k)]
    missing = [k for k in keywords if k not in matched]
    keyword_pct = round(100 * len(matched) / len(keywords), 1) if keywords else 0.0

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

    score = int(round(keyword_pct * 0.5 + skills_pct * 0.2 + structure + formatting))
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
        suggestions=_suggestions(resume, missing, keyword_pct, skills_pct),
    )


def _suggestions(resume: ResumeData, missing: list[str], keyword_pct: float, skills_pct: float) -> list[str]:
    tips: list[str] = []
    if missing:
        tips.append(f"Add these missing keywords where truthful: {', '.join(missing[:10])}.")
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
