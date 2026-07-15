from app.schemas import ResumeData

def export_to_markdown(resume_data: ResumeData) -> str:
    """Export resume data to Markdown format.
    
    Args:
        resume_data (ResumeData): The resume data to export.
        
    Returns:
        str: The Markdown content as a string.
    """
    markdown_content = f"# {resume_data.contact.name}\n\n"
    markdown_content += f"**Email:** {resume_data.contact.email}\n"
    if resume_data.contact.phone:
        markdown_content += f"**Phone:** {resume_data.contact.phone}\n"
    if resume_data.contact.location:
        markdown_content += f"**Location:** {resume_data.contact.location}\n\n"

    # Add summary
    if resume_data.summary:
        markdown_content += "## Summary\n\n"
        markdown_content += f"{resume_data.summary}\n\n"

    # Add skills
    if resume_data.skills:
        markdown_content += "## Skills\n\n"
        for skill in resume_data.skills:
            markdown_content += f"- {skill}\n"

    # Add experience
    if resume_data.experience:
        markdown_content += "## Work Experience\n\n"
        for exp in resume_data.experience:
            markdown_content += f"### {exp.title}\n"
            markdown_content += f"{exp.company} ({exp.start_date} - {exp.end_date})\n"
            if exp.location:
                markdown_content += f"{exp.location}\n\n"
            for bullet in exp.bullets:
                markdown_content += f"- {bullet}\n"

    # Add education
    if resume_data.education:
        markdown_content += "## Education\n\n"
        for edu in resume_data.education:
            markdown_content += f"### {edu.degree} from {edu.institution}\n"
            if edu.year:
                markdown_content += f"Year: {edu.year}\n\n"

    # Add certifications
    if resume_data.certifications:
        markdown_content += "## Certifications\n\n"
        for cert in resume_data.certifications:
            markdown_content += f"- {cert}\n"

    return markdown_content