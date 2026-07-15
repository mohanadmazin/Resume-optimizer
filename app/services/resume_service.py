from app.schemas import ResumeData
from app.renderers.docx_renderer import export_to_docx
from app.renderers.pdf_renderer import export_to_pdf
from app.renderers.markdown_renderer import export_to_markdown
from app.ats_engine import analyze

class ResumeService:
    def __init__(self, resume_data: ResumeData):
        self.resume_data = resume_data
    
    def get_ats_analysis(self) -> dict:
        """Get ATS analysis for the provided resume data."""
        return analyze(self.resume_data)
    
    def export_to_docx(self) -> bytes:
        """Export the resume to DOCX format."""
        return export_to_docx(self.resume_data)
    
    def export_to_pdf(self) -> bytes:
        """Export the resume to PDF format."""
        return export_to_pdf(self.resume_data)
    
    def export_to_markdown(self) -> str:
        """Export the resume to Markdown format."""
        return export_to_markdown(self.resume_data)

# Example usage
if __name__ == "__main__":
    # Sample resume data
    sample_resume = ResumeData(
        contact=ContactInfo(name="John Doe", email="john.doe@example.com"),
        summary="Experienced software engineer with a passion for solving complex problems.",
        skills=["Python", "Django", "RESTful APIs"],
        experience=[
            ExperienceItem(title="Software Engineer", company="ABC Corp", start_date="2018-06", end_date="Present")
        ],
        education=[
            EducationItem(degree="BSc in Computer Science", institution="XYZ University", year="2014-2018")
        ]
    )
    
    # Create a ResumeService instance
    resume_service = ResumeService(sample_resume)
    
    # Get ATS analysis
    ats_analysis = resume_service.get_ats_analysis()
    print("ATS Analysis:", ats_analysis)
    
    # Export to different formats
    docx_content = resume_service.export_to_docx()
    pdf_content = resume_service.export_to_pdf()
    markdown_content = resume_service.export_to_markdown()
    
    # Save files (for demonstration purposes)
    with open("resume.docx", "wb") as f:
        f.write(docx_content)
    
    with open("resume.pdf", "wb") as f:
        f.write(pdf_content)
    
    with open("resume.md", "w") as f:
        f.write(markdown_content)