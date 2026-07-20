"""Tests for Requirement Evidence Matrix — matching, scoring, export."""
from __future__ import annotations

from app.domain.evidence import CareerFact, FactConfidence, FactType
from app.domain.job_requirements import JobRequirements, Requirement
from app.domain.requirement_matrix import (
    CoverageLevel,
    MatrixExportFormat,
    RequirementItem,
    RequirementMatrix,
    RequirementType,
)
from app.services.requirement_matrix import (
    build_matrix,
    classify_requirement,
    export_matrix,
)


def _fact(stmt: str, fid: int = 1) -> CareerFact:
    return CareerFact(
        id=fid,
        statement=stmt,
        fact_type=FactType.TECHNOLOGY,
        confidence=FactConfidence.VERIFIED,
    )


def _facts(*stmts: str) -> list[CareerFact]:
    return [_fact(s, i + 1) for i, s in enumerate(stmts)]


# ── RequirementType classification ─────────────────────────────────

class TestClassifyRequirement:
    def test_certification(self):
        assert classify_requirement("AWS certification required") == RequirementType.CERTIFICATION

    def test_education(self):
        assert classify_requirement("Bachelor's degree in CS") == RequirementType.EDUCATION

    def test_location(self):
        assert classify_requirement("Must work on-site in NYC") == RequirementType.LOCATION

    def test_authorization(self):
        assert classify_requirement("US security clearance required") == RequirementType.AUTHORIZATION

    def test_travel(self):
        assert classify_requirement("Up to 25% travel required") == RequirementType.TRAVEL

    def test_required(self):
        assert classify_requirement("Must have 5 years Python") == RequirementType.REQUIRED

    def test_preferred(self):
        assert classify_requirement("Preferred experience with React") == RequirementType.PREFERRED

    def test_responsibility(self):
        assert classify_requirement("Responsible for mentoring team") == RequirementType.RESPONSIBILITY

    def test_domain(self):
        assert classify_requirement("Experience with distributed systems") == RequirementType.DOMAIN

    def test_tool(self):
        assert classify_requirement("Proficient with Docker and Kubernetes") == RequirementType.TOOL

    def test_soft_skill(self):
        assert classify_requirement("Strong communication skills") == RequirementType.SOFT_SKILL

    def test_default_required(self):
        assert classify_requirement("Some random requirement") == RequirementType.REQUIRED


# ── Matrix building ─────────────────────────────────────────────────

class TestBuildMatrix:
    def test_empty_requirements(self):
        job = JobRequirements()
        matrix = build_matrix(job, [])
        assert matrix.total_requirements == 0
        assert matrix.overall_score == 0.0

    def test_direct_evidence_match(self):
        job = JobRequirements(
            required_skills=[Requirement(name="Python", evidence="")],
        )
        facts = _facts("Built Python web application serving 10k users")
        matrix = build_matrix(job, facts)
        assert matrix.requirements[0].coverage == CoverageLevel.DIRECT_EVIDENCE
        assert matrix.requirements[0].coverage_score > 0
        assert 1 in matrix.requirements[0].evidence_fact_ids

    def test_no_evidence_gap(self):
        job = JobRequirements(
            required_skills=[Requirement(name="Rust", evidence="")],
        )
        facts = _facts("Built Python web application")
        matrix = build_matrix(job, facts)
        assert matrix.requirements[0].coverage == CoverageLevel.MISSING
        assert matrix.requirements[0].action_needed != ""
        assert matrix.gap_count == 1

    def test_preferred_lower_importance(self):
        job = JobRequirements(
            required_skills=[Requirement(name="Python", evidence="")],
            preferred_skills=[Requirement(name="Rust", evidence="")],
        )
        facts = _facts("Built Python application", "Wrote Rust CLI tools")
        matrix = build_matrix(job, facts)
        assert matrix.requirements[0].importance == 1.0
        assert matrix.requirements[1].importance == 0.7

    def test_overall_score_calculation(self):
        job = JobRequirements(
            required_skills=[
                Requirement(name="Python", evidence=""),
                Requirement(name="Java", evidence=""),
            ],
        )
        facts = _facts("Python expert with 10 years", "Java backend services")
        matrix = build_matrix(job, facts)
        assert matrix.overall_score > 0.8
        assert matrix.covered_count == 2
        assert matrix.gap_count == 0

    def test_partial_coverage(self):
        job = JobRequirements(
            required_skills=[
                Requirement(name="Python", evidence=""),
                Requirement(name="Kubernetes", evidence=""),
            ],
        )
        facts = _facts("Built Python applications")
        matrix = build_matrix(job, facts)
        assert matrix.requirements[0].coverage == CoverageLevel.DIRECT_EVIDENCE
        assert matrix.requirements[1].coverage == CoverageLevel.MISSING
        assert matrix.covered_count == 1
        assert matrix.gap_count == 1

    def test_responsibilities_included(self):
        job = JobRequirements(
            responsibilities=["Lead a team of 5 engineers"],
        )
        facts = _facts("Led team of 5 engineers for 2 years")
        matrix = build_matrix(job, facts)
        assert matrix.total_requirements == 1
        assert matrix.requirements[0].requirement_type == RequirementType.RESPONSIBILITY

    def test_education_requirements(self):
        job = JobRequirements(
            education_requirements=["BS in Computer Science"],
        )
        facts = _facts("BS in Computer Science from MIT")
        matrix = build_matrix(job, facts)
        assert matrix.requirements[0].requirement_type == RequirementType.EDUCATION

    def test_strengths_populated(self):
        job = JobRequirements(
            required_skills=[Requirement(name="Python", evidence="")],
        )
        facts = _facts("Expert Python developer")
        matrix = build_matrix(job, facts)
        assert len(matrix.strengths) == 1

    def test_multiple_facts_matched(self):
        job = JobRequirements(
            required_skills=[Requirement(name="Python", evidence="")],
        )
        facts = _facts(
            "Python web apps",
            "Python data pipelines",
            "Python testing frameworks",
        )
        matrix = build_matrix(job, facts)
        assert len(matrix.requirements[0].evidence_fact_ids) >= 2

    def test_candidate_evidence_text_populated(self):
        job = JobRequirements(
            required_skills=[Requirement(name="Python", evidence="")],
        )
        facts = _facts("Built Python data pipeline")
        matrix = build_matrix(job, facts)
        assert len(matrix.requirements[0].candidate_evidence_text) == 1

    def test_gaps_list_populated(self):
        job = JobRequirements(
            required_skills=[
                Requirement(name="Rust", evidence=""),
                Requirement(name="Haskell", evidence=""),
            ],
        )
        facts = _facts("Python developer")
        matrix = build_matrix(job, facts)
        assert len(matrix.gaps) == 2

    def test_action_needed_for_missing(self):
        job = JobRequirements(
            required_skills=[Requirement(name="Rust", evidence="")],
        )
        matrix = build_matrix(job, _facts("Python dev"))
        assert "No evidence found" in matrix.requirements[0].action_needed

    def test_action_empty_for_direct(self):
        job = JobRequirements(
            required_skills=[Requirement(name="Python", evidence="")],
        )
        matrix = build_matrix(job, _facts("Python expert"))
        assert matrix.requirements[0].action_needed == ""


# ── Export ──────────────────────────────────────────────────────────

class TestExportMatrix:
    def _matrix(self) -> RequirementMatrix:
        return RequirementMatrix(
            requirements=[
                RequirementItem(
                    text="Python experience",
                    requirement_type=RequirementType.REQUIRED,
                    importance=1.0,
                    coverage=CoverageLevel.DIRECT_EVIDENCE,
                    coverage_score=1.0,
                    evidence_fact_ids=[1, 2],
                ),
                RequirementItem(
                    text="Rust knowledge",
                    requirement_type=RequirementType.PREFERRED,
                    importance=0.7,
                    coverage=CoverageLevel.MISSING,
                    coverage_score=0.0,
                    action_needed="No evidence found for: Rust",
                ),
            ],
            overall_score=0.71,
            gaps=["No evidence found for: Rust"],
            strengths=["Python experience"],
            total_requirements=2,
            covered_count=1,
            gap_count=1,
        )

    def test_markdown_export(self):
        md = export_matrix(self._matrix(), MatrixExportFormat.MARKDOWN)
        assert "Requirement Evidence Matrix" in md
        assert "Python experience" in md
        assert "YES" in md
        assert "NO" in md
        assert "71%" in md

    def test_csv_export(self):
        csv = export_matrix(self._matrix(), MatrixExportFormat.CSV)
        lines = csv.strip().split("\n")
        assert lines[0] == "Requirement,Type,Importance,Coverage,EvidenceCount,ActionNeeded"
        assert "Python experience" in lines[1]
        assert "Rust knowledge" in lines[2]

    def test_csv_handles_quotes(self):
        mat = RequirementMatrix(
            requirements=[
                RequirementItem(
                    text='Skill with "quotes"',
                    coverage=CoverageLevel.MISSING,
                ),
            ],
            total_requirements=1,
        )
        csv = export_matrix(mat, MatrixExportFormat.CSV)
        assert '""quotes""' in csv

    def test_empty_matrix_export(self):
        mat = RequirementMatrix()
        md = export_matrix(mat, MatrixExportFormat.MARKDOWN)
        assert "0%" in md
        csv = export_matrix(mat, MatrixExportFormat.CSV)
        assert "Requirement" in csv.split("\n")[0]
