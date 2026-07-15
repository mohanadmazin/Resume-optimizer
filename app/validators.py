"""Data validation logic for resume schemas."""
from app.schemas import ResumeData


def validate_resume(resume_data: ResumeData) -> dict:
    """Validate the resume data and return a dictionary of errors.
    
    Args:
        resume_data: The ResumeData object to validate.
        
    Returns:
        A dictionary where keys are field names and values are lists of error messages.
        Returns an empty dictionary if validation passes.
    """
    errors = {}

    # Check required contact information
    if not resume_data.contact.name or not resume_data.contact.name.strip():
        errors["contact"] = errors.get("contact", []) + ["Name is required."]
    
    if not resume_data.contact.email or not resume_data.contact.email.strip():
        errors["contact"] = errors.get("contact", []) + ["Email is required."]
    elif "@" not in resume_data.contact.email:
        errors["contact"] = errors.get("contact", []) + ["Invalid email format."]

    # Check if resume has content
    if not resume_data.summary and not resume_data.experience and not resume_data.education:
        errors["resume"] = errors.get("resume", []) + ["Resume must contain at least one section (summary, experience, or education)."]

    # Validate experience bullets
    for i, exp in enumerate(resume_data.experience):
        if exp.title and not exp.bullets:
            errors[f"experience_{i}"] = errors.get(f"experience_{i}", []) + ["Experience entry has a title but no bullets."]

    return errors


def is_valid(resume_data: ResumeData) -> bool:
    """Check if the resume data passes all validation rules.
    
    Args:
        resume_data: The ResumeData object to check.
        
    Returns:
        True if valid, False otherwise.
    """
    return len(validate_resume(resume_data)) == 0
