"""Pydantic models describing structured resume data."""
from typing import List

from pydantic import BaseModel, Field


class ContactInfo(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    website: str = ""


class ExperienceItem(BaseModel):
    title: str = ""
    company: str = ""
    start_date: str = ""
    end_date: str = ""
    location: str = ""
    bullets: List[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    degree: str = ""
    institution: str = ""
    year: str = ""


class ProjectItem(BaseModel):
    title: str = ""
    meta: str = ""
    start_date: str = ""
    end_date: str = ""
    description: str = ""
    bullets: List[str] = Field(default_factory=list)


class ResumeData(BaseModel):
    contact: ContactInfo = Field(default_factory=ContactInfo)

    headline: str = ""

    summary: str = ""

    skills: List[str] = Field(default_factory=list)

    experience: List[ExperienceItem] = Field(default_factory=list)

    education: List[EducationItem] = Field(default_factory=list)

    certifications: List[str] = Field(default_factory=list)

    projects: List[ProjectItem] = Field(default_factory=list)

    languages: List[str] = Field(default_factory=list)

    raw_text: str = ""