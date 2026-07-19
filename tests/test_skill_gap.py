from unittest.mock import MagicMock

from app.schemas import ResumeData
from app.services.skill_gap import analyze_skill_gap


def test_skill_gap_accepts_job_description_and_target_role():
    client = MagicMock()
    client.generate_json.return_value = {
        "required_skills": ["IEC 62443"],
        "matched": [],
        "missing": [],
        "summary": "Gap found.",
    }
    result = analyze_skill_gap(
        ResumeData(skills=["Networking"]),
        "Requires IEC 62443 experience.",
        "OT Network Security",
        client=client,
    )
    prompt = client.generate_json.call_args.args[0]
    assert "Requires IEC 62443 experience." in prompt
    assert result.target_role == "OT Network Security"
