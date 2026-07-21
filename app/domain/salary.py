"""Salary domain models — validated compensation estimates and provenance."""
from __future__ import annotations

from decimal import Decimal
from typing import List, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class SalaryLocation(BaseModel):
    city: str = ""
    region: str = ""
    country: str = ""
    country_code: str = ""
    currency: str = ""


class SalaryBenchmarkSelection(BaseModel):
    role_key: str = ""
    role: str = ""
    weight: Decimal = Decimal("0")
    low: Decimal = Decimal("0")
    median: Decimal = Decimal("0")
    high: Decimal = Decimal("0")


class SalaryAdjustment(BaseModel):
    factor: str = ""
    multiplier: Decimal = Decimal("1")
    reason: str = ""


class SalaryConfidence(BaseModel):
    score: Decimal = Decimal("0")
    level: Literal["low", "medium", "high"] = "low"
    reasons: List[str] = Field(default_factory=list)
    missing_inputs: List[str] = Field(default_factory=list)

    @field_validator("score", mode="before")
    @classmethod
    def _bound_score(cls, value):
        try:
            score = Decimal(str(value))
        except Exception:
            return Decimal("0")
        return max(Decimal("0"), min(Decimal("1"), score))


class SalaryEstimate(BaseModel):
    """A deterministic salary estimate with legacy UI compatibility fields."""

    status: Literal["ok", "insufficient_data"] = "ok"

    role: str = ""
    normalized_role: str = ""
    role_family: str = ""
    specialization: str = ""
    career_track: Literal["individual_contributor", "management"] = (
        "individual_contributor"
    )

    location: str = ""
    location_details: SalaryLocation = Field(default_factory=SalaryLocation)

    experience_years: str = ""
    total_experience_years: Decimal = Decimal("0")
    relevant_experience_years: Decimal = Decimal("0")
    specialization_experience_years: Decimal = Decimal("0")
    management_experience_years: Decimal = Decimal("0")
    seniority: str = "unknown"

    # Legacy fields kept because existing pages and persisted state use them.
    salary_range: str = ""
    salary_min: Decimal = Decimal("0")
    salary_max: Decimal = Decimal("0")
    salary_monthly_min: Decimal = Decimal("0")
    salary_monthly_mid: Decimal = Decimal("0")
    salary_monthly_max: Decimal = Decimal("0")
    salary_annual_min: Decimal = Decimal("0")
    salary_annual_mid: Decimal = Decimal("0")
    salary_annual_max: Decimal = Decimal("0")
    currency: str = ""

    salary_source: str = ""
    source_date: str = ""
    compensation_basis: str = "basic_base_salary"
    confidence: str = "low"
    confidence_details: SalaryConfidence = Field(default_factory=SalaryConfidence)

    selected_benchmarks: List[SalaryBenchmarkSelection] = Field(default_factory=list)
    adjustments: List[SalaryAdjustment] = Field(default_factory=list)
    combined_multiplier: Decimal = Decimal("1")

    factors: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    additional_compensation_notes: str = ""
    notes: str = ""

    @model_validator(mode="after")
    def _validate_salary_arithmetic(self):
        if self.status != "ok":
            return self

        monthly = (
            self.salary_monthly_min,
            self.salary_monthly_mid,
            self.salary_monthly_max,
        )
        if not monthly[0] <= monthly[1] <= monthly[2]:
            raise ValueError("Monthly salary range must be ordered min <= mid <= max")

        # Annual salary is always deterministic base salary x 12.
        self.salary_annual_min = self.salary_monthly_min * Decimal("12")
        self.salary_annual_mid = self.salary_monthly_mid * Decimal("12")
        self.salary_annual_max = self.salary_monthly_max * Decimal("12")
        self.salary_min = self.salary_annual_min
        self.salary_max = self.salary_annual_max

        if self.salary_monthly_min > 0:
            width = self.salary_monthly_max / self.salary_monthly_min
            if width > Decimal("1.60"):
                raise ValueError("Salary range is wider than the allowed 1.60 ratio")

        return self
