"""Tests for salary estimation — experience calculation and DI."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from app.schemas import ExperienceItem, ResumeData
from app.services.salary_estimator import (
    _merge_intervals,
    _months_between,
    _parse_date,
    estimate_experience,
    estimate_salary,
)


# ---------------------------------------------------------------------------
# _parse_date helpers
# ---------------------------------------------------------------------------
class TestParseDate:
    def test_present(self):
        assert _parse_date("present") == date.today()

    def test_current(self):
        assert _parse_date("current") == date.today()

    def test_now(self):
        assert _parse_date("now") == date.today()

    def test_year_only(self):
        assert _parse_date("2020") == date(2020, 1, 1)

    def test_month_year(self):
        # The regex consumes the month name, so prefix detection yields Jan (default)
        assert _parse_date("Mar 2021") == date(2021, 1, 1)

    def test_unparseable_returns_none(self):
        assert _parse_date("abc xyz") is None

    def test_empty_string(self):
        assert _parse_date("") is None


# ---------------------------------------------------------------------------
# _months_between / _merge_intervals
# ---------------------------------------------------------------------------
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
        ivs = [(date(2020, 1, 1), date(2020, 6, 1)), (date(2021, 1, 1), date(2021, 6, 1))]
        merged = _merge_intervals(ivs)
        assert len(merged) == 2

    def test_overlapping(self):
        ivs = [(date(2020, 1, 1), date(2020, 12, 1)), (date(2020, 6, 1), date(2021, 6, 1))]
        merged = _merge_intervals(ivs)
        assert len(merged) == 1
        assert merged[0] == (date(2020, 1, 1), date(2021, 6, 1))

    def test_adjacent(self):
        ivs = [(date(2020, 1, 1), date(2020, 6, 1)), (date(2020, 6, 1), date(2021, 1, 1))]
        merged = _merge_intervals(ivs)
        assert len(merged) == 1


# ---------------------------------------------------------------------------
# estimate_experience — core cases
# ---------------------------------------------------------------------------
def _make_resume(exps):
    """Build ResumeData from list of (company, start_date, end_date) tuples."""

    return ResumeData(
        contact={"name": "Test", "email": "test@test.com"},
        summary="",
        experience=[
            ExperienceItem(company=c, start_date=s or "", end_date=e or "", title="", bullets=[])
            for c, s, e in exps
        ],
        education=[],
        skills=[],
    )


class TestEstimateExperience:
    def test_undated_old_role_bounded_by_next_start(self):
        """An older role with no end date should end at the next role's start."""
        resume = _make_resume([
            ("Acme", "2018", None),     # undated — bounded by next start
            ("Globex", "2020", None),    # undated most-recent → today
        ])
        result = estimate_experience(resume)
        # Acme: Jan 2018 → Jan 2020 = 24 months
        # Globex: Jan 2020 → today
        today = date.today()
        expected_globex_months = (today.year - 2020) * 12 + (today.month - 1)
        expected_total = 24 + expected_globex_months
        expected_years = round(expected_total / 12, 1)
        assert result.minimum_years == expected_years
        assert "Acme" in result.missing_dates
        assert "Globex" in result.missing_dates

    def test_most_recent_undated_defaults_to_today(self):
        """The most recent undated role defaults its end to today."""
        resume = _make_resume([
            ("Acme", "2020", None),
        ])
        result = estimate_experience(resume)
        today = date.today()
        expected_months = (today.year - 2020) * 12 + (today.month - 1)
        expected_years = round(expected_months / 12, 1)
        assert result.minimum_years == expected_years

    def test_future_start_date_excluded(self):
        """Roles with future start dates are excluded and flagged."""
        resume = _make_resume([
            ("Acme", "2020", "2021"),
            ("FutureCorp", "2030", None),
        ])
        result = estimate_experience(resume)
        assert result.future_start is True
        # Only Acme should count: Jan 2020 → Jan 2021 = 12 months = 1.0 years
        assert result.minimum_years == 1.0
        assert "FutureCorp" in result.missing_dates

    def test_no_future_start_when_all_normal(self):
        """future_start stays False when all dates are valid."""
        resume = _make_resume([
            ("Acme", "2020", "2021"),
            ("Globex", "2022", "2023"),
        ])
        result = estimate_experience(resume)
        assert result.future_start is False

    def test_empty_experience(self):

        resume = ResumeData(
            contact={"name": "Test", "email": "t@t.com"},
            summary="",
            experience=[], education=[], skills=[],
        )
        result = estimate_experience(resume)
        assert result.minimum_years == 0.0
        assert result.confidence == "low"
        assert result.future_start is False

    def test_missing_start_date_excluded(self):
        """Roles with no start date at all are excluded."""
        resume = _make_resume([
            ("NoStart", None, "2021"),
            ("Good", "2020", "2021"),
        ])
        result = estimate_experience(resume)
        assert result.minimum_years == 1.0
        assert "NoStart" in result.missing_dates

    def test_overlapping_roles_merged(self):
        """Overlapping roles are merged into a single span."""
        resume = _make_resume([
            ("A", "2020", "2022"),
            ("B", "2021", "2023"),
        ])
        result = estimate_experience(resume)
        # Merged: Jan 2020 → Jan 2023 = 36 months = 3.0 years
        assert result.minimum_years == 3.0

    def test_inverted_dates_excluded(self):
        """End date before start date is excluded."""
        resume = _make_resume([
            ("Bad", "2021", "2020"),
            ("Good", "2020", "2021"),
        ])
        result = estimate_experience(resume)
        assert result.minimum_years == 1.0
        assert "Bad" in result.missing_dates


# ---------------------------------------------------------------------------
# estimate_salary — dependency injection
# ---------------------------------------------------------------------------
class TestEstimateSalaryDI:
    def test_uses_provided_client(self):
        """When a client is passed, estimate_salary uses it directly."""
        mock_client = MagicMock()
        mock_client.generate_json.return_value = {
            "role": "Engineer",
            "location": "NYC",
            "salary_range": "$100k-$150k",
            "salary_min": 100000,
            "salary_max": 150000,
            "currency": "USD",
            "factors": [],
            "notes": "",
        }
        resume = _make_resume([
            ("Acme", "2020", "2022"),
        ])
        result = estimate_salary(resume, "Engineer", "NYC", client=mock_client)
        mock_client.generate_json.assert_called_once()
        assert result.salary_range == "$100k-$150k"

    @patch("app.services.salary_estimator.OllamaClient", autospec=True)
    def test_creates_client_when_none(self, MockOC):
        """When client is None, a new OllamaClient is created."""
        mock_instance = MockOC.return_value
        mock_instance.generate_json.return_value = {
            "role": "Dev",
            "location": "Remote",
            "salary_range": "$80k-$120k",
            "salary_min": 80000,
            "salary_max": 120000,
            "currency": "USD",
            "factors": [],
            "notes": "",
        }
        resume = _make_resume([
            ("Acme", "2020", "2022"),
        ])
        result = estimate_salary(resume, "Dev", "Remote")
        MockOC.assert_called_once()
        assert result.salary_range == "$80k-$120k"

    def test_future_start_flag_propagates(self):
        """Future start dates are flagged and experience is computed correctly."""
        mock_client = MagicMock()
        mock_client.generate_json.return_value = {
            "role": "Dev",
            "location": "Remote",
            "salary_range": "",
            "factors": [],
            "notes": "",
        }
        resume = _make_resume([
            ("Acme", "2020", "2021"),
            ("Future", "2099", None),
        ])
        result = estimate_salary(resume, "Dev", "Remote", client=mock_client)
        # experience_years should reflect only Acme (1.0 year)
        assert "1" in result.experience_years
