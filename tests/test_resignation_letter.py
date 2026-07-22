from app.services.resignation_letter import (
    ResignationLetterInput,
    generate_resignation_letter,
    validate_resignation_input,
)


def _input(**changes):
    values = {
        "employee_name": "Alex Tan",
        "company_name": "Example Sdn Bhd",
        "position": "Operations Manager",
        "letter_date": "2026-07-22",
        "last_working_day": "2026-09-22",
        "manager_name": "Ms Lee",
        "notice_period": "two months'",
    }
    values.update(changes)
    return ResignationLetterInput(**values)


def test_generates_formal_letter_with_supplied_facts_only():
    letter = generate_resignation_letter(_input())
    assert "22 July 2026" in letter
    assert "22 September 2026" in letter
    assert "Operations Manager" in letter
    assert "Example Sdn Bhd" in letter
    assert "two months' notice" in letter
    assert "Dear Ms Lee," in letter
    assert "smooth transition" in letter


def test_optional_reason_and_transition_can_be_omitted():
    letter = generate_resignation_letter(
        _input(tone="concise", reason="none", transition_support=False)
    )
    assert "personal reasons" not in letter
    assert "smooth transition" not in letter
    assert "I wish the company continued success." in letter


def test_custom_reason_is_used_without_inventing_details():
    letter = generate_resignation_letter(
        _input(reason="other", reason_details="I am moving to another state")
    )
    assert "I am moving to another state." in letter


def test_rejects_last_working_day_before_letter_date():
    errors = validate_resignation_input(_input(last_working_day="2026-07-01"))
    assert "Last working day cannot be earlier than the letter date." in errors


def test_custom_reason_requires_wording():
    errors = validate_resignation_input(_input(reason="other", reason_details=""))
    assert "Enter custom reason wording or choose another reason option." in errors
