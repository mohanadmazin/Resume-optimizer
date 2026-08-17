# Salary estimator correction

This build replaces free-form AI salary guessing with a benchmark-driven
pipeline.

## Changed files

- `app/data/salary_benchmarks.py` — versioned Malaysia benchmark dataset.
- `app/domain/salary.py` — provenance, confidence, benchmark, adjustment, and
  midpoint models with deterministic annual arithmetic.
- `app/ai/prompts.py` — AI now classifies role/relevant experience and selects
  only approved benchmark keys; it no longer invents salary figures.
- `app/services/salary_estimator.py` — local currency normalization, role
  matching, relevant-experience calculation, validated benchmark blending,
  bounded adjustments, deterministic ranges, local rounding, and safe fallback.
- `app/ui/pages/salary_estimate.py` — shows min/mid/max, confidence, source,
  basis, assumptions, and insufficient-data states.
- `tests/test_salary_estimator.py` — regression coverage for dates, arithmetic,
  role mapping, unsupported markets, management misclassification, and malformed
  model output.
- `SALARY_ESTIMATION.md` — extension and data-maintenance guide.

## Validation

- Salary-focused tests: 31 passed.
- Full test suite: 877 passed after initializing the test database schema.
- Python compilation: passed.
- The uploaded CV structure was parsed and exercised against the hybrid
  Network Engineer / Network Security / Project Engineer benchmark blend.
