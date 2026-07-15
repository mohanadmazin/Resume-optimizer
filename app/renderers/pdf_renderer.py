import fitz  # PyMuPDF
from app.schemas import ResumeData

def export_to_pdf(resume_data: ResumeData) -> bytes:
    """Export resume data to PDF format.
    
    Args:
        resume_data (ResumeData): The resume data to export.
        
    Returns:
        bytes: The PDF file content as bytes.
    """
    pdf_document = fitz.open()
    
    # Add contact information
    page = pdf_document.new_page()
    page.insert_text((50, 700), f"{resume_data.contact.name}", fontsize=24)
    page.insert_text((50, 680), f"Email: {resume_data.contact.email}", fontsize=12)
    if resume_data.contact.phone:
        page.insert_text((50, 660), f"Phone: {resume_data.contact.phone}", fontsize=12)
    if resume_data.contact.location:
        page.insert_text((50, 640), f"Location: {resume_data.contact.location}", fontsize=12)
    
    # Add summary
    if resume_data.summary:
        page = pdf_document.new_page()
        page.insert_text((50, 700), "Summary", fontsize=18)
        page.insert_text((50, 680), resume_data.summary, fontsize=12)
    
    # Add skills
    if resume_data.skills:
        page = pdf_document.new_page()
        page.insert_text((50, 700), "Skills", fontsize=18)
        for skill in resume_data.skills:
            page.insert_text((50, 680), skill, fontsize=12)
    
    # Add experience
    if resume_data.experience:
        page = pdf_document.new_page()
        page.insert_text((50, 700), "Work Experience", fontsize=18)
        for exp in resume_data.experience:
            page.insert_text((50, 680), f"{exp.title}", fontsize=14)
            page.insert_text((50, 660), f"{exp.company} ({exp.start_date} - {exp.end_date})", fontsize=12)
            if exp.location:
                page.insert_text((50, 640), exp.location, fontsize=12)
            for bullet in exp.bullets:
                page.insert_text((50, 620), bullet, fontsize=12, text_width=300)
    
    # Add education
    if resume_data.education:
        page = pdf_document.new_page()
        page.insert_text((50, 700), "Education", fontsize=18)
        for edu in resume_data.education:
            page.insert_text((50, 680), f"{edu.degree} from {edu.institution}", fontsize=14)
            if edu.year:
                page.insert_text((50, 660), f"Year: {edu.year}", fontsize=12)
    
    # Add certifications
    if resume_data.certifications:
        page = pdf_document.new_page()
        page.insert_text((50, 700), "Certifications", fontsize=18)
        for cert in resume_data.certifications:
            page.insert_text((50, 680), cert, fontsize=12)
    
    # Save the document to a bytes stream and return it
    output = io.BytesIO()
    pdf_document.save(output)
    output.seek(0)
    return output.getvalue()