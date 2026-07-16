"""Salary domain models — compensation estimates with source tracking."""
from decimal import Decimal
from typing import List

from pydantic import BaseModel, Field


class SalaryEstimate(BaseModel):
    role: str = ""
    location: str = ""
    experience_years: str = ""
    salary_range: str = ""
    salary_min: Decimal = Decimal("0")
    salary_max: Decimal = Decimal("0")
    salary_monthly_min: Decimal = Decimal("0")
    salary_monthly_max: Decimal = Decimal("0")
    salary_annual_min: Decimal = Decimal("0")
    salary_annual_max: Decimal = Decimal("0")
    currency: str = "USD"
    salary_source: str = ""
    source_date: str = ""
    confidence: str = ""
    factors: List[str] = Field(default_factory=list)
    notes: str = ""
