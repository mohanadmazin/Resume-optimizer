"""ATS analysis engine: keyword extraction, scoring and suggestions."""
import logging
import re
from collections import Counter
from typing import Tuple

from app.domain.analysis import ATSResult
from app.domain.skill_lexicon import SKILL_ALIASES
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
    "fortran", "cobol", "assembly", "vba", "objective-c", "groovy", "julia",
    "typescript", "javascript",
    # Frameworks
    "django", "flask", "fastapi", "spring", "springboot", "express", "node.js", "nodejs",
    "react", "reactjs", "vue", "vuejs", "angular", "angularjs", "svelte", "next.js", "nextjs",
    "rails", "laravel", "symfony", ".net", "dotnet", "asp.net",
    "blazor", "flutter", "react native", "ionic", "xamarin", "telerik",
    "graphql", "apollo", "tailwind", "bootstrap", "jquery",
    # Databases
    "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch", "cassandra",
    "dynamodb", "sqlite", "oracle", "neo4j", "mssql", "sqlserver",
    "snowflake", "databricks", "bigquery", "redshift", "clickhouse", "cockroachdb",
    "mariadb", "couchdb", "firebase", "supabase", "memcached", "etcd", "riak",
    "db2", "teradata", "informix",
    # Cloud & DevOps
    "aws", "gcp", "azure", "docker", "kubernetes", "k8s", "terraform", "ansible",
    "jenkins", "github actions", "gitlab ci", "ci/cd", "ci cd", "prometheus", "grafana",
    "cloudformation", "helm", "argocd", "circleci", "travis",
    "azure devops", "azure pipelines", "bitbucket pipelines", "spinnaker",
    "puppet", "chef", "saltstack", "vagrant", "packer", "vagrant",
    "cloudflare", "fastly", "akamai", "s3", "ec2", "lambda", "cloudfront",
    "gke", "aks", "eks", "openshift", "istio", "envoy", "consul", "vault",
    "pulumi", "crossplane", "argocd", "flux",
    # Data & Analytics
    "spark", "hadoop", "kafka", "airflow", "mlflow", "dbt", "snowflake",
    "tableau", "power bi", "looker", "superset", "metabase", "qlik",
    "pentaho", "talend", "informatica", "ssis", "ssas", "ssrs",
    "excel", "google sheets", "pandas", "numpy", "scipy",
    # AI/ML
    "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn",
    "langchain", "openai", "llamaindex", "huggingface", "transformers",
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "neural networks", "transformers",
    "stable diffusion", "midjourney", "dall-e", "chatgpt", "gpt-4", "llm",
    "xgboost", "lightgbm", "catboost", "prophet", "scikit",
    "opencv", "yolo", "bert", "gpt", "llama", "mistral", "gemini",
    "mlops", "feature store", "model deployment", "vector database",
    "pinecone", "weaviate", "milvus", "chromadb", "faiss",
    # Tools
    "git", "linux", "bash", "powershell", "vim", "vscode", "jira", "confluence",
    "slack", "docker compose", "postman", "figma", "jupyter",
    "notion", "airtable", "salesforce", "hubspot", "zendesk", "intercom",
    "splunk", "datadog", "new relic", "dynatrace", "appdynamics",
    "sonarqube", "checkmarx", "veracode", "fortify",
    # Methodologies
    "agile", "scrum", "kanban", "devops", "mlops", "tdd", "bdd", "saas", "paas", "iaas",
    "microservices", "serverless", "rest", "restful", "graphql", "grpc", "websocket",
    "oauth", "jwt", "oauth2", "saml", "ldap",
    "domain-driven design", "event-driven", "cqrs", "event sourcing",
    "12-factor", "clean architecture", "hexagonal architecture",
    # Testing
    "pytest", "unittest", "jest", "mocha", "cypress", "selenium", "playwright",
    "junit", "xunit", "postman",
    "k6", "gatling", "jmeter", "loadrunner", "artillery",
    "robot framework", "cucumber", "specflow", "testng", "phpunit",
    "sonarqube", "codecov", "coveralls",
    # Networking & Security
    "tcp/ip", "dns", "load balancing", "firewall", "vpn", "ssl/tls",
    "owasp", "burp suite", "nessus", "wireshark", "nmap",
    "penetration testing", "vulnerability assessment", "siem",
    "iso 27001", "soc 2", "gdpr", "hipaa", "pci-dss",
    # Engineering / Hardware
    "autocad", "solidworks", "catia", "revit", "plc", "scada",
    "matlab", "simulink", "labview", "embedded systems", "rtos",
    "pcb design", "altium", "eagle", "fpga", "vhdl", "verilog",
    "ros", "industrial automation",
    # Misc
    "rabbitmq", "nginx", "apache", "tomcat", "protobuf", "avro",
    "blockchain", "web3", "solidity", "ethereum",
    "erp", "sap", "oracle erp", "workday", "successfactors",
    "project management", "stakeholder management", "risk management",
    "budget management", "vendor management", "change management",
    "business analysis", "requirements gathering", "process improvement",
    "six sigma", "lean", "itil", "cobit",
}

_BASE_KNOWN_SKILLS = frozenset(_KNOWN_SKILLS)


def get_known_skills() -> set[str]:
    """Return the immutable base vocabulary plus current user settings."""
    try:
        from app.core.settings import load_settings
        custom = {
            value.strip().casefold()
            for value in load_settings().ai.custom_skills
            if value.strip()
        }
    except Exception:
        logger.debug("Could not load custom skills", exc_info=True)
        custom = set()
    return set(_BASE_KNOWN_SKILLS) | custom

SHORT_KEEP = {"c#", "go", "r", "ai", "ml", "qa", "ci", "cd", "ux", "ui", "c++", "aws", "sql", "api", "git"}

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
    known_skills = get_known_skills()
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
        is_known = bg in known_skills or _canonicalize(bg) in SKILL_ALIASES
        if count < 2 and not is_known:
            continue
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
    # Remove unigrams that are part of a kept bigram
    bigram_parts: set[str] = set()
    for bg in top_bigrams:
        bigram_parts.update(bg.split())
    singles = [
        w for w, _ in counts.most_common(top_n * 2)
        if w not in bigram_parts
    ]
    return (top_bigrams + singles)[:top_n]


def extract_required_skills(text: str) -> list[str]:
    """Extract skill-like terms from a job description.

    Returns unique skill terms that appear in the JD and are known
    technical skills (from the curated vocabulary).  Generic words like
    "environment", "support", or "business" are excluded.
    """
    known_skills = get_known_skills()
    tokens = [t.strip(".-/") for t in re.findall(r"[a-z][a-z0-9+#.\-/]*", text.lower())]
    words = [
        t for t in tokens
        if t and t not in STOPWORDS and (len(t) > 2 or t in SHORT_KEEP)
    ]

    # Collect frequent bigrams first (e.g. "machine learning", "CI/CD")
    bigram_counts: Counter = Counter()
    for first, second in zip(words, words[1:]):
        bigram_counts[f"{first} {second}"] += 1
    # Keep bigrams that are known skills (even if mentioned once) or frequent
    bigrams = [
        b for b, c in bigram_counts.most_common(20)
        if (_canonicalize(b) in SKILL_ALIASES or b in known_skills) or c >= 2
    ]

    # Single-word candidates — must be known skills
    bigram_words = set()
    for b in bigrams:
        bigram_words.update(b.split())
    singles = [
        w for w, _ in Counter(words).most_common(60)
        if w not in bigram_words and (w in known_skills or _canonicalize(w) in SKILL_ALIASES)
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


def _keyword_matches(resume_text: str, keyword: str) -> bool:
    canonical = _canonicalize(keyword)
    if canonical in SKILL_ALIASES:
        return _skill_matches(resume_text, canonical)
    return _contains(resume_text, keyword)


def _resume_text(resume: ResumeData) -> str:
    parts = [resume.headline, resume.summary, " ".join(resume.skills), " ".join(resume.languages)]
    for exp in resume.experience:
        parts += [exp.title, exp.company, " ".join(exp.bullets)]
    for proj in resume.projects:
        parts += [proj.title, proj.meta, proj.description, " ".join(proj.bullets)]
    for edu in resume.education:
        parts.append(f"{edu.degree} {edu.institution}")
    parts += resume.certifications
    parts.append(resume.raw_text)
    return " ".join(p for p in parts if p)


def analyze(resume: ResumeData, jd_text: str) -> ATSResult:
    weighted_keywords = _extract_weighted_keywords(jd_text)
    keywords = [kw for kw, _ in weighted_keywords]
    weights = {kw: w for kw, w in weighted_keywords}

    structured = _resume_text(resume).strip()
    resume_text = structured if structured else resume.raw_text
    resume_text = resume_text.lower()

    matched = [k for k in keywords if _keyword_matches(resume_text, k)]
    matched_set = set(matched)
    missing = [k for k in keywords if k not in matched_set]

    # Weighted keyword score: sum of matched weights / sum of all weights
    total_weight = sum(weights.values())
    matched_weight = sum(weights[k] for k in matched)
    keyword_pct = round(100 * matched_weight / total_weight, 1) if total_weight else 0.0

    # Skills match: extract required skills from JD, check which appear in resume
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

    # Normalize all components to 0-100 scale, then apply weights
    keyword_score = keyword_pct  # already 0-100
    structure_score = structure / 20 * 100  # max raw = 20 → 100
    formatting_score = formatting / 10 * 100  # max raw = 10 → 100

    components = [
        (keyword_score, 0.50),
        (structure_score, 0.20),
        (formatting_score, 0.10),
    ]
    if required_skills:
        components.append((skills_pct, 0.20))

    total_weight = sum(w for _, w in components)
    score = round(sum(v * w for v, w in components) / total_weight)
    score = max(0, min(100, score))

    # Build the versioned rule-engine score report
    from app.services.scoring_engine import build_score_report
    from app.domain.scoring import LayoutMetrics

    has_bullets = any(exp.bullets for exp in resume.experience)
    resume_words = _resume_text(resume)
    layout = LayoutMetrics(
        word_count=len(resume_words.split()),
        has_bullets=has_bullets,
        line_count=resume_words.count("\n") + 1,
    )
    score_report = build_score_report(resume, jd_text, layout)

    logger.info(
        "ATS analysis: score=%d keyword_pct=%.1f skills_pct=%.1f missing=%d rulescore=%d",
        score, keyword_pct, skills_pct, len(missing), score_report.overall_score,
    )

    # --- Keyword Targeting new workflow ---
    from app.services.keyword_targeting import match_requirement
    from app.domain.keyword_targeting import JobRequirement, ResumeTextIndex
    job_requirements = [JobRequirement(
        name=kw,
        aliases=[],
        importance=weights.get(kw, 0.5),
        frequency=max(1, int(weights.get(kw, 0.5) * 2)),
        source_phrases=[kw],
    ) for kw in keywords]
    # Build resume text index
    parts = []
    parts.append(("headline", resume.headline.lower() if resume.headline else ""))
    parts.append(("summary", resume.summary.lower() if resume.summary else ""))
    for i, skill in enumerate(resume.skills):
        parts.append((f"skills[{i}]", skill.lower()))
    for i, exp in enumerate(resume.experience):
        if exp.title:
            parts.append((f"experience[{i}].title", exp.title.lower()))
        if exp.company:
            parts.append((f"experience[{i}].company", exp.company.lower()))
        for j, b in enumerate(exp.bullets):
            parts.append((f"experience[{i}].bullets[{j}]", b.lower()))
    for i, proj in enumerate(resume.projects):
        if proj.title:
            parts.append((f"projects[{i}].title", proj.title.lower()))
        if proj.description:
            parts.append((f"projects[{i}].description", proj.description.lower()))
        for j, b in enumerate(proj.bullets):
            parts.append((f"projects[{i}].bullets[{j}]", b.lower()))
    resume_index = ResumeTextIndex(path_text=parts)
    keyword_targets = [match_requirement(req, resume_index) for req in job_requirements]

    return ATSResult(
        ats_score=score,
        keyword_match_pct=keyword_pct,
        skills_match_pct=skills_pct,
        matched_keywords=matched,
        missing_keywords=missing,
        missing_skills=missing_skills,
        keyword_weights=weights,
        suggestions=_suggestions(resume, missing, weights, keyword_pct, skills_pct),
        score_report=score_report,
        keyword_targets=keyword_targets,
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
