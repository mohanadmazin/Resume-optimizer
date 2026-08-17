# Salary estimation architecture

The salary feature is benchmark-driven rather than prompt-driven.

## What the language model does

- Normalizes the requested role.
- Distinguishes total, relevant, specialization, and management experience.
- Selects one to three roles from a pre-approved candidate list.
- Suggests small, evidence-based adjustment multipliers.
- Explains confidence, assumptions, and missing inputs.

## What application code does

- Normalizes country and local currency.
- Retrieves versioned benchmark records.
- Rejects unsupported markets instead of converting another country's salary.
- Validates benchmark keys and normalizes weights.
- Clamps every adjustment to documented limits.
- Computes monthly minimum, midpoint, and maximum deterministically.
- Rounds salary in local-currency increments.
- Computes annual base salary as monthly base salary multiplied by exactly 12.
- Validates ordering and maximum range width.

## Bundled market

The bundled dataset currently supports Malaysia (`MYR`). Its technology-role
figures are sourced from the **Randstad Malaysia 2025 Job Market Outlook &
Salary Guide**, where figures are basic monthly salary for permanent roles and
exclude AWS and fixed/variable bonuses.

Source:

https://www.randstad.com.my/s3fs-media/my/public/2024-12/randstad-malaysia-2025-job-market-outlook-and-salary-guide.pdf

The broad wage sanity check references the Department of Statistics Malaysia
formal-sector median monthly wage for December 2025.

Source:

https://www.dosm.gov.my/portal-main/release-content/employee-wages-statistics-formal-sector-q42025

## Adding another country

Add a reviewed `SalaryMarket` to `app/data/salary_benchmarks.py`, then register
it in `MARKETS_BY_COUNTRY_CODE`. Do not add exchange-rate conversions as a
substitute for local benchmarks.
