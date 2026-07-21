"""Tests for benchmark-driven salary estimation."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.schemas import ContactInfo, EducationItem, ExperienceItem, ResumeData
from app.services.salary_estimator import (
    _merge_intervals,
    _months_between,
    _parse_date,
    estimate_experience,
    estimate_salary,
)


class TestParseDate:
    def test_present(self):
        assert _parse_date("present") == date.today()

    def test_current(self):
        assert _parse_date("current") == date.today()

    def test_now(self):
        assert _parse_date("now") == date.today()

    def test_year_only(self):
        assert _parse_date("2020") == date(2020, 1, 1)

    def test_month_year_preserves_month(self):
        assert _parse_date("Mar 2021") == date(2021, 3, 1)

    def test_long_month_year(self):
        assert _parse_date("September 2024") == date(2024, 9, 1)

    def test_unparseable_returns_none(self):
        assert _parse_date("abc xyz") is None

    def test_empty_string(self):
        assert _parse_date("") is None


class TestMonthsBetween:
    def test_same_month(self):
        assert _months_between(date(2020, 1, 1), date(2020, 1, 1)) == 0

    def test_one_year(self):
        assert _months_between(date(2020, 1, 1), date(2021, 1, 1)) == 12

    def test_partial_year(self):
        assert _months_between(date(2020, 3, 1), date(2020, 12, 1)) == 9


class TestMergeIntervals:
    def test_empty(self):
        assert _merge_intervals([]) == []

    def test_non_overlapping(self):
        intervals = [
            (date(2020, 1, 1), date(2020, 6, 1)),
            (date(2021, 1, 1), date(2021, 6, 1)),
        ]
        assert len(_merge_intervals(intervals)) == 2

    def test_overlapping(self):
        intervals = [
            (date(2020, 1, 1), date(2020, 12, 1)),
            (date(2020, 6, 1), date(2021, 6, 1)),
        ]
        assert _merge_intervals(intervals) == [
            (date(2020, 1, 1), date(2021, 6, 1))
        ]

    def test_adjacent(self):
        intervals = [
            (date(2020, 1, 1), date(2020, 6, 1)),
            (date(2020, 6, 1), date(2021, 1, 1)),
        ]
        assert len(_merge_intervals(intervals)) == 1


def _make_resume(experiences):
    return ResumeData(
        contact=ContactInfo(name="Test", email="test@example.com"),
        summary="Enterprise networking and security professional.",
        headline="Network and Security Engineer",
        experience=[
            ExperienceItem(
                company=company,
                start_date=start or "",
                end_date=end or "",
                title=title,
                bullets=bullets,
            )
            for company, start, end, title, bullets in experiences
        ],
        education=[
            EducationItem(
                degree="MSc Computer Networks",
                institution="Example University",
                year="2019",
            )
        ],
        skills=[
            "Network Architecture",
            "SD-WAN",
            "Palo Alto",
            "Network Security",
            "BGP",
            "OSPF",
        ],
        certifications=["CCNP Routing & Switching 2014", "Cato SASE 2025"],
    )


class TestEstimateExperience:
    def test_undated_old_role_bounded_by_next_start(self):
        resume = _make_resume(
            [
                ("Acme", "2018", None, "Network Engineer", []),
                ("Globex", "2020", None, "Network Engineer", []),
            ]
        )
        result = estimate_experience(resume)
        today = date.today()
        expected_months = 24 + (today.year - 2020) * 12 + (today.month - 1)
        assert result.minimum_years == round(expected_months / 12, 1)
        assert "Acme" in result.missing_dates
        assert "Globex" in result.missing_dates

    def test_future_start_date_excluded(self):
        resume = _make_resume(
            [
                ("Acme", "2020", "2021", "Network Engineer", []),
                ("FutureCorp", str(date.today().year + 5), None, "Network Engineer", []),
            ]
        )
        result = estimate_experience(resume)
        assert result.future_start is True
        assert result.minimum_years == 1.0
        assert "FutureCorp" in result.missing_dates

    def test_empty_experience(self):
        resume = ResumeData(contact=ContactInfo(name="Test", email="t@t.com"))
        result = estimate_experience(resume)
        assert result.minimum_years == 0.0
        assert result.confidence == "low"

    def test_overlapping_roles_merged(self):
        resume = _make_resume(
            [
                ("A", "2020", "2022", "Network Engineer", []),
                ("B", "2021", "2023", "Security Engineer", []),
            ]
        )
        assert estimate_experience(resume).minimum_years == 3.0

    def test_inverted_dates_excluded(self):
        resume = _make_resume(
            [
                ("Bad", "2021", "2020", "Network Engineer", []),
                ("Good", "2020", "2021", "Network Engineer", []),
            ]
        )
        result = estimate_experience(resume)
        assert result.minimum_years == 1.0
        assert "Bad" in result.missing_dates


def _ai_result():
    return {
        "normalized_role": "Enterprise Network and Security Project Engineer",
        "role_family": "network_infrastructure",
        "specialization": "network security and project delivery",
        "career_track": "individual_contributor",
        "relevant_experience_years": 8.0,
        "specialization_experience_years": 6.0,
        "management_experience_years": 0.0,
        "seniority": "senior",
        "selected_benchmarks": [
            {"role_key": "network_engineer", "weight": 0.50},
            {"role_key": "network_security", "weight": 0.30},
            {"role_key": "project_engineer", "weight": 0.20},
        ],
        "adjustments": [
            {
                "factor": "scope",
                "multiplier": 1.05,
                "reason": "Enterprise delivery scope is documented.",
            }
        ],
        "confidence": {
            "score": 0.82,
            "reasons": ["Close benchmark match"],
            "missing_inputs": [],
        },
        "factors": ["Hybrid network, security, and delivery role"],
        "assumptions": [],
        "additional_compensation_notes": "Bonus and allowances are excluded.",
        "notes": "Conservative benchmark-based estimate.",
    }


class TestEstimateSalary:
    def _resume(self):
        return _make_resume(
            [
                (
                    "ViewQwest",
                    "Sep 2024",
                    "Present",
                    "Project Engineer",
                    [
                        "Lead end-to-end enterprise network delivery.",
                        "Designed SD-WAN and Palo Alto security policies.",
                    ],
                ),
                (
                    "Aircom",
                    "Oct 2019",
                    "Sep 2024",
                    "Network Technical Support Engineer",
                    ["Supported a 1,000-node telecom network."],
                ),
            ]
        )

    def test_uses_provided_client_and_calculates_arithmetic(self):
        client = MagicMock()
        client.generate_json.return_value = _ai_result()

        result = estimate_salary(
            self._resume(),
            "Project Engineer - Enterprise Network & Security",
            "Kuala Lumpur, Malaysia",
            client=client,
        )

        client.generate_json.assert_called_once()
        assert result.status == "ok"
        assert result.currency == "MYR"
        assert result.salary_monthly_min <= result.salary_monthly_mid <= result.salary_monthly_max
        assert result.salary_annual_min == result.salary_monthly_min * 12
        assert result.salary_annual_mid == result.salary_monthly_mid * 12
        assert result.salary_annual_max == result.salary_monthly_max * 12
        assert result.salary_min == result.salary_annual_min
        assert result.salary_max == result.salary_annual_max
        assert len(result.selected_benchmarks) == 3

    @patch("app.services.salary_estimator.OllamaClient", autospec=True)
    def test_creates_client_when_none(self, mock_client_class):
        mock_client_class.return_value.generate_json.return_value = _ai_result()
        result = estimate_salary(
            self._resume(),
            "Network Engineer",
            "Kuala Lumpur, Malaysia",
        )
        mock_client_class.assert_called_once()
        assert result.status == "ok"

    def test_unknown_market_does_not_invent_converted_salary(self):
        client = MagicMock()
        result = estimate_salary(
            self._resume(),
            "Network Engineer",
            "Paris, France",
            client=client,
        )
        assert result.status == "insufficient_data"
        assert result.salary_monthly_max == 0
        client.generate_json.assert_not_called()

    def test_management_title_not_inferred_from_project_engineer(self):
        client = MagicMock()
        data = _ai_result()
        data["career_track"] = "management"
        data["selected_benchmarks"] = [
            {"role_key": "technical_project_manager", "weight": 1.0}
        ]
        client.generate_json.return_value = data

        result = estimate_salary(
            self._resume(),
            "Project Engineer - Enterprise Network & Security",
            "Kuala Lumpur, Malaysia",
            client=client,
        )
        assert result.career_track == "individual_contributor"
        assert all(
            item.role_key != "technical_project_manager"
            for item in result.selected_benchmarks
        )

    def test_malformed_ai_output_falls_back_to_deterministic_selection(self):
        client = MagicMock()
        client.generate_json.return_value = {"unexpected": "payload"}
        result = estimate_salary(
            self._resume(),
            "Network Security Engineer",
            "Kuala Lumpur, Malaysia",
            client=client,
        )
        assert result.status == "ok"
        assert result.selected_benchmarks
        assert result.salary_source.startswith("Randstad Malaysia")

    def test_range_width_is_controlled(self):
        client = MagicMock()
        client.generate_json.return_value = _ai_result()
        result = estimate_salary(
            self._resume(),
            "Network Engineer",
            "Kuala Lumpur, Malaysia",
            client=client,
        )
        assert result.salary_monthly_max / result.salary_monthly_min <= Decimal("1.60")
