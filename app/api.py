from fastapi import FastAPI, File, UploadFile
from app.schemas import ResumeData
from app.services.resume_service import ResumeService

app = FastAPI()

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    """Upload a resume file and process it."""
    # Read the uploaded file content
    content = await file.read()
    
    # Parse the resume data (this is a placeholder; you may need to implement actual parsing logic)
    resume_data = ResumeData(
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
    resume_service = ResumeService(resume_data)
    
    # Get ATS analysis
    ats_analysis = resume_service.get_ats_analysis()
    
    # Export to different formats
    docx_content = resume_service.export_to_docx()
    pdf_content = resume_service.export_to_pdf()
    markdown_content = resume_service.export_to_markdown()
    
    return {
        "ats_analysis": ats_analysis,
        "exports": {
            "docx": {"filename": file.filename, "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "content": docx_content},
            "pdf": {"filename": file.filename.replace(".pdf", ".pdf"), "content_type": "application/pdf", "content": pdf_content},
            "markdown": {"filename": file.filename.replace(".md", ".md"), "content_type": "text/markdown", "content": markdown_content}
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)