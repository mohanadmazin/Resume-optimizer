# ResumeAI Real-Data Validation Report

## Test inputs

- Resume: DOCX network security and infrastructure engineering resume supplied for testing.
- Target vacancy: Deployment Network Engineer, Accenture Southeast Asia, Cyberjaya, Selangor.
- Vacancy source: https://www.linkedin.com/jobs/view/4368255878
- Test date: 22 July 2026.

Personal contact details from the supplied resume are not reproduced in this report or committed to the project source.

## Workflow result

The following flows passed with the real DOCX and vacancy description:

1. Every main web page rendered successfully.
2. DOCX upload and text extraction completed.
3. The shared Resume Builder loaded the same persisted resume record.
4. Rich vacancy metadata and the source URL were saved.
5. ATS analysis completed and persisted.
6. Markdown, TXT, JSON, DOCX and PDF resume exports were valid.
7. An application-tracker record was created and rendered.
8. The workflow session restored correctly after the in-memory cache was cleared.

AI optimization reached the expected controlled error path because no Ollama server was running at the configured localhost endpoint. The optimizer route, review/apply flow and exports remain covered by automated integration tests using a deterministic AI substitute.

## Parser result after corrections

- Contact information: detected.
- Summary: detected.
- Skills: 48 structured skills.
- Employment: 3 correct roles.
- Selected projects: 2 correct projects.
- Education: 2 correct degrees with institution, location, CGPA and dates.
- Certifications and professional development: 8 entries.
- Languages: detected.
- Parse warnings: 0.

## Application-generated ATS result

- Target-match score: 64/100.
- Keyword coverage: 48.6%.
- Required-skill coverage: 47.1%.
- Resume-quality rule score: 98/100.

The target-match score and resume-quality score measure different things. The first measures alignment with this specific vacancy; the second checks document quality, structure and general readiness.

### Detected strengths

- LAN and SD-WAN.
- BGP and OSPF.
- Palo Alto and network security.
- Python and Ansible.
- Enterprise implementation, migration, troubleshooting and technical leadership.

### Vacancy terms not explicitly supported in the resume

- AWS, Azure and GCP cloud networking.
- Terraform.
- TCP/IP as an explicit keyword.
- Splunk.
- DevOps collaboration as an explicit term.
- GDPR and HIPAA.

The vacancy also asks for MPLS, QoS, load balancers, proxy servers, compliance frameworks, vulnerability management and several monitoring/certification options. These should be added only when they accurately reflect the candidate's experience.

## Defects found and fixed through this test

1. Long section headings such as “Selected Security & Infrastructure Projects” were rejected by an overly short heading-length limit.
2. Two-line role layouts were split into fake city-based experience entries.
3. Project date lines were not attached to the correct project.
4. “Certifications & Professional Development” was not recognized as a certification section.
5. Scheduled and year-range certification dates were split into separate records.
6. Education institutions, locations and dates were misassigned in pipe-separated layouts.
7. Keyword evidence did not normalize punctuation consistently, so SD-WAN and Palo Alto could appear matched in one area but missing in another.
8. The ATS page wording implied that the resume-quality categories calculated the target-match score; the labels now distinguish the two measures.

## Regression verification

- Real-data integration workflow: passed.
- Dedicated real-world parser and keyword-evidence regression tests: passed.
- Non-desktop automated suite: 687 tests passed.
- Python compilation: passed.
- Jinja template compilation: passed.
- JavaScript syntax validation: passed.

Desktop-only tests require the optional PySide6 dependency. The live Ollama generation step requires a running Ollama server and installed model.
