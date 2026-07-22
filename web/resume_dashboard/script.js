const STORAGE_KEY = "resumeForgeFullDataV1";

const defaultData = {
  year: String(new Date().getFullYear()),
  contact: {
    fullName: "",
    email: "",
    phone: "",
    linkedin: "",
    website: "",
    country: "Malaysia",
    state: "Selangor",
    city: "Petaling Jaya",
    visibility: { country: true, state: true, city: true }
  },
  experience: [],
  project: [],
  education: [],
  certifications: [],
  coursework: {
    courseworkTitle: "Relevant Coursework",
    courseworkInstitution: "",
    courseworkItems: ""
  },
  skills: [],
  summary: {
    professionalTitle: "",
    summaryText: ""
  },
  coverLetter: {
    coverJobTitle: "",
    coverCompany: "",
    coverHiringManager: "",
    coverTone: "Professional",
    jobDescription: "",
    output: ""
  }
};

let state = loadState();
let toastTimer;

const pagePanels = document.querySelectorAll("[data-page-panel]");
const pageButtons = document.querySelectorAll("[data-page]");
const tabs = document.querySelectorAll(".tab");
const sideButtons = document.querySelectorAll(".side-button[data-page]");
const actionButtons = document.querySelectorAll(".action-button[data-page]");
const toast = document.querySelector("#toast");
const toastMessage = document.querySelector("#toastMessage");
const resetModal = document.querySelector("#resetModal");

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return clone(defaultData);
    const saved = JSON.parse(raw);
    const base = clone(defaultData);
    return {
      ...base,
      ...saved,
      contact: {
        ...base.contact,
        ...(saved.contact || {}),
        visibility: {
          ...base.contact.visibility,
          ...(saved.contact?.visibility || {})
        }
      },
      experience: Array.isArray(saved.experience) ? saved.experience : [],
      project: Array.isArray(saved.project) ? saved.project : [],
      education: Array.isArray(saved.education) ? saved.education : [],
      certifications: Array.isArray(saved.certifications) ? saved.certifications : [],
      coursework: { ...base.coursework, ...(saved.coursework || {}) },
      skills: Array.isArray(saved.skills) ? saved.skills : [],
      summary: { ...base.summary, ...(saved.summary || {}) },
      coverLetter: { ...base.coverLetter, ...(saved.coverLetter || {}) }
    };
  } catch (error) {
    console.warn("Could not restore saved builder data:", error);
    return clone(defaultData);
  }
}

function persistState(message = "Changes saved.") {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    if (message) showToast(message);
  } catch (error) {
    console.error("Could not save builder data:", error);
    showToast("Could not save in this browser.");
  }
}

function showToast(message) {
  toastMessage.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove("show"), 2500);
}

function setSaveStatus(panel, message = "Saved locally") {
  const status = panel?.querySelector(".save-status");
  if (!status) return;
  status.textContent = message;
  window.setTimeout(() => {
    if (status.textContent === message) status.textContent = "";
  }, 2600);
}

function navigate(page, updateHash = true) {
  const target = document.querySelector(`[data-page-panel="${page}"]`);
  if (!target) return;

  pagePanels.forEach((panel) => panel.classList.toggle("active", panel === target));

  tabs.forEach((tab) => {
    const active = tab.dataset.page === page;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
  });

  actionButtons.forEach((button) => button.classList.toggle("active", button.dataset.page === page));
  sideButtons.forEach((button) => {
    const active = button.dataset.page === page ||
      (button.getAttribute("aria-label") === "Resume editor" && !["cover-letter", "preview"].includes(page));
    button.classList.toggle("active", active);
  });

  if (page === "preview") renderPreview();
  if (page === "cover-letter") populateCoverLetterForm();

  if (updateHash) {
    history.replaceState(null, "", `#${page}`);
  }
  window.scrollTo({ top: 0, behavior: "smooth" });
}

pageButtons.forEach((button) => {
  button.addEventListener("click", () => navigate(button.dataset.page));
});

document.querySelector(".brand-mark").addEventListener("click", (event) => {
  event.preventDefault();
  navigate("contact");
});

function formToObject(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function populateForm(form, data) {
  Object.entries(data || {}).forEach(([key, value]) => {
    const field = form.elements.namedItem(key);
    if (!field || typeof value !== "string") return;
    if (field.tagName === "SELECT" && value && ![...field.options].some(option => option.value === value)) {
      field.add(new Option(value, value));
    }
    field.value = value;
  });
}

function normaliseLines(value) {
  return String(value || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function formatMonth(value) {
  if (!value) return "";
  const date = new Date(`${value}-01T00:00:00`);
  return new Intl.DateTimeFormat("en", { month: "short", year: "numeric" }).format(date);
}

function escapeHtml(value = "") {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  })[character]);
}

/* Contact */
const contactForm = document.querySelector("#contactForm");
populateForm(contactForm, state.contact);

document.querySelector("#resumeYear").value = state.year;
document.querySelector("#resumeYear").addEventListener("change", (event) => {
  state.year = event.target.value;
  persistState("Resume year updated.");
});

document.querySelectorAll("[data-visibility]").forEach((toggle) => {
  const key = toggle.dataset.visibility;
  const enabled = state.contact.visibility?.[key] !== false;
  toggle.classList.toggle("active", enabled);
  toggle.setAttribute("aria-pressed", String(enabled));

  toggle.addEventListener("click", () => {
    const next = toggle.getAttribute("aria-pressed") !== "true";
    toggle.classList.toggle("active", next);
    toggle.setAttribute("aria-pressed", String(next));
    state.contact.visibility[key] = next;
    persistState(`${key[0].toUpperCase()}${key.slice(1)} visibility updated.`);
  });
});

contactForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!contactForm.reportValidity()) return;
  state.contact = {
    ...state.contact,
    ...formToObject(contactForm),
    visibility: state.contact.visibility
  };
  persistState("Basic information saved.");
  setSaveStatus(contactForm);
});

/* Dynamic entries */
const entryConfigs = {
  experience: {
    template: "#experienceTemplate",
    list: "#experienceList",
    stateKey: "experience",
    titleField: "title",
    emptyTitle: "No experience added yet",
    emptyText: "Add a role, internship, freelance engagement, or volunteer position."
  },
  project: {
    template: "#projectTemplate",
    list: "#projectList",
    stateKey: "project",
    titleField: "name",
    emptyTitle: "No projects added yet",
    emptyText: "Add projects that prove your technical, analytical, or leadership ability."
  },
  education: {
    template: "#educationTemplate",
    list: "#educationList",
    stateKey: "education",
    titleField: "qualification",
    emptyTitle: "No education added yet",
    emptyText: "Add your degree, diploma, professional programme, or other qualification."
  },
  certification: {
    template: "#certificationTemplate",
    list: "#certificationList",
    stateKey: "certifications",
    titleField: "name",
    emptyTitle: "No certifications added yet",
    emptyText: "Add licences, certificates, or professional credentials."
  }
};

function renderEntryList(type) {
  const config = entryConfigs[type];
  const list = document.querySelector(config.list);
  const entries = state[config.stateKey] || [];
  list.innerHTML = "";

  if (!entries.length) {
    list.innerHTML = `
      <div class="entry-empty">
        <div><strong>${config.emptyTitle}</strong>${config.emptyText}</div>
      </div>`;
    return;
  }

  entries.forEach((entry, index) => {
    const template = document.querySelector(config.template);
    const fragment = template.content.cloneNode(true);
    const card = fragment.querySelector(".entry-card");
    card.dataset.index = index;
    card.querySelector(".entry-number").textContent = `${type} ${index + 1}`;
    card.querySelector(".entry-title").textContent = entry[config.titleField] || `New ${type}`;

    card.querySelectorAll("[data-field]").forEach((field) => {
      const key = field.dataset.field;
      field.value = entry[key] || "";
      field.addEventListener("input", () => {
        state[config.stateKey][index][key] = field.value;
        if (key === config.titleField) {
          card.querySelector(".entry-title").textContent = field.value || `New ${type}`;
        }
      });
    });

    card.querySelector(".remove-entry").addEventListener("click", () => {
      state[config.stateKey].splice(index, 1);
      renderEntryList(type);
      persistState(`${type[0].toUpperCase()}${type.slice(1)} removed.`);
    });

    list.appendChild(fragment);
  });
}

Object.keys(entryConfigs).forEach(renderEntryList);

document.querySelectorAll(".add-entry").forEach((button) => {
  button.addEventListener("click", () => {
    const type = button.dataset.entryType;
    const config = entryConfigs[type];
    const blank = {};
    document.querySelector(config.template).content.querySelectorAll("[data-field]").forEach((field) => {
      blank[field.dataset.field] = field.tagName === "SELECT" ? field.options[0].value : "";
    });
    state[config.stateKey].push(blank);
    renderEntryList(type);
    const list = document.querySelector(config.list);
    list.lastElementChild?.scrollIntoView({ behavior: "smooth", block: "center" });
  });
});

document.querySelectorAll(".save-section").forEach((button) => {
  button.addEventListener("click", () => {
    const section = button.dataset.section;
    persistState(`${section[0].toUpperCase()}${section.slice(1)} saved.`);
    setSaveStatus(button.closest(".resume-card"));
  });
});

/* Coursework */
const courseworkForm = document.querySelector("#courseworkForm");
populateForm(courseworkForm, state.coursework);
courseworkForm.addEventListener("submit", (event) => {
  event.preventDefault();
  state.coursework = formToObject(courseworkForm);
  persistState("Coursework saved.");
  setSaveStatus(courseworkForm);
});

/* Skills */
const skillName = document.querySelector("#skillName");
const skillLevel = document.querySelector("#skillLevel");
const skillsBoard = document.querySelector("#skillsBoard");

function renderSkills() {
  skillsBoard.innerHTML = "";
  if (!state.skills.length) {
    skillsBoard.innerHTML = `<div class="entry-empty"><div><strong>No skills added yet</strong>Add the skills most relevant to your target role.</div></div>`;
    return;
  }

  state.skills.forEach((skill, index) => {
    const card = document.createElement("div");
    card.className = "skill-card";
    card.innerHTML = `
      <div><strong>${escapeHtml(skill.name)}</strong><span>${escapeHtml(skill.level)}</span></div>
      <button class="skill-remove" type="button" aria-label="Remove ${escapeHtml(skill.name)}">×</button>`;
    card.querySelector("button").addEventListener("click", () => {
      state.skills.splice(index, 1);
      renderSkills();
      persistState("Skill removed.");
    });
    skillsBoard.appendChild(card);
  });
}

renderSkills();

document.querySelector("#addSkillButton").addEventListener("click", () => {
  const name = skillName.value.trim();
  if (!name) {
    skillName.focus();
    showToast("Enter a skill first.");
    return;
  }

  state.skills.push({ name, level: skillLevel.value });
  skillName.value = "";
  renderSkills();
  persistState("Skill added.");
});

skillName.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    document.querySelector("#addSkillButton").click();
  }
});

/* Summary */
const summaryForm = document.querySelector("#summaryForm");
const summaryText = document.querySelector("#summaryText");
const summaryCount = document.querySelector("#summaryCount");
populateForm(summaryForm, state.summary);

function updateSummaryCount() {
  summaryCount.textContent = summaryText.value.length;
}
summaryText.addEventListener("input", updateSummaryCount);
updateSummaryCount();

summaryForm.addEventListener("submit", (event) => {
  event.preventDefault();
  state.summary = formToObject(summaryForm);
  persistState("Professional summary saved.");
  setSaveStatus(summaryForm);
});

document.querySelector("#generateSummaryButton").addEventListener("click", () => {
  const title = document.querySelector("#professionalTitle").value.trim() || "professional";
  const strongestSkills = state.skills.slice(0, 4).map((skill) => skill.name).join(", ");
  const experiencePhrase = state.experience.length
    ? `with practical experience across ${state.experience.length} role${state.experience.length > 1 ? "s" : ""}`
    : "with a strong foundation in applied business work";
  summaryText.value = `Analytical and results-focused ${title} ${experiencePhrase}. Skilled in ${strongestSkills || "data analysis, communication, and project coordination"}, with the ability to organise information, improve workflows, and communicate clear recommendations to stakeholders. Known for accuracy, adaptability, and a consistent focus on delivering measurable value.`;
  updateSummaryCount();
  showToast("Summary draft generated. Review and edit it before saving.");
});

/* Preview */
function sectionHtml(title, content) {
  return content ? `<section class="resume-section"><h2>${escapeHtml(title)}</h2>${content}</section>` : "";
}

function bulletList(text) {
  const lines = normaliseLines(text);
  return lines.length ? `<ul>${lines.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>` : "";
}

function dateRange(start, end) {
  const left = formatMonth(start);
  const right = end ? formatMonth(end) : "Present";
  return [left, right].filter(Boolean).join(" – ");
}

function renderPreview() {
  syncAllFormsToState();

  const contact = state.contact;
  const location = [
    contact.visibility?.city !== false ? contact.city : "",
    contact.visibility?.state !== false ? contact.state : "",
    contact.visibility?.country !== false ? contact.country : ""
  ].filter(Boolean).join(", ");

  const contactItems = [contact.email, contact.phone, location, contact.linkedin, contact.website]
    .filter(Boolean)
    .map((item) => `<span>${escapeHtml(item)}</span>`)
    .join("");

  const experienceHtml = state.experience.map((item) => `
    <div class="resume-item">
      <div class="resume-item-heading">
        <strong>${escapeHtml(item.title || "Position")}</strong>
        <span>${escapeHtml(dateRange(item.start, item.end))}</span>
      </div>
      <div class="resume-item-sub">${escapeHtml([item.company, item.location].filter(Boolean).join(" · "))}</div>
      ${bulletList(item.description)}
    </div>`).join("");

  const projectHtml = state.project.map((item) => `
    <div class="resume-item">
      <div class="resume-item-heading">
        <strong>${escapeHtml(item.name || "Project")}</strong>
        <span>${escapeHtml(dateRange(item.start, item.end))}</span>
      </div>
      <div class="resume-item-sub">${escapeHtml([item.role, item.tools].filter(Boolean).join(" · "))}</div>
      ${bulletList(item.description)}
    </div>`).join("");

  const educationHtml = state.education.map((item) => `
    <div class="resume-item">
      <div class="resume-item-heading">
        <strong>${escapeHtml(item.qualification || "Qualification")}</strong>
        <span>${escapeHtml(dateRange(item.start, item.end))}</span>
      </div>
      <div class="resume-item-sub">${escapeHtml([item.institution, item.field, item.location].filter(Boolean).join(" · "))}</div>
      ${item.grade || item.honours ? `<div class="resume-item-sub">${escapeHtml([item.grade, item.honours].filter(Boolean).join(" · "))}</div>` : ""}
      ${bulletList(item.description)}
    </div>`).join("");

  const certificationHtml = state.certifications.map((item) => `
    <div class="resume-item">
      <div class="resume-item-heading">
        <strong>${escapeHtml(item.name || "Certification")}</strong>
        <span>${escapeHtml(formatMonth(item.issue))}</span>
      </div>
      <div class="resume-item-sub">${escapeHtml([item.issuer, item.credentialId].filter(Boolean).join(" · "))}</div>
    </div>`).join("");

  const courseworkLines = normaliseLines(state.coursework.courseworkItems);
  const courseworkHtml = courseworkLines.length
    ? `<div class="resume-skill-list">${courseworkLines.map((item) => `<span>${escapeHtml(item)}</span>`).join("<span>•</span>")}</div>`
    : "";

  const skillsHtml = state.skills.length
    ? `<div class="resume-skill-list">${state.skills.map((skill) => `<span><strong>${escapeHtml(skill.name)}</strong> (${escapeHtml(skill.level)})</span>`).join("")}</div>`
    : "";

  document.querySelector("#resumePreview").innerHTML = `
    <header>
      <h1>${escapeHtml(contact.fullName || "YOUR NAME")}</h1>
      <div class="resume-title">${escapeHtml(state.summary.professionalTitle || "")}</div>
      <div class="resume-contact">${contactItems}</div>
    </header>
    ${sectionHtml("Professional Summary", `<div class="resume-summary">${escapeHtml(state.summary.summaryText || "")}</div>`)}
    ${sectionHtml("Experience", experienceHtml)}
    ${sectionHtml("Projects", projectHtml)}
    ${sectionHtml("Education", educationHtml)}
    ${sectionHtml("Certifications", certificationHtml)}
    ${sectionHtml(state.coursework.courseworkTitle || "Relevant Coursework", courseworkHtml)}
    ${sectionHtml("Skills", skillsHtml)}
  `;

  updateCompletion();
}

function updateCompletion() {
  const checks = [
    Boolean(state.contact.fullName && state.contact.email),
    Boolean(state.summary.summaryText),
    state.experience.length > 0,
    state.project.length > 0,
    state.education.length > 0,
    state.certifications.length > 0,
    normaliseLines(state.coursework.courseworkItems).length > 0,
    state.skills.length >= 3
  ];
  const completion = Math.round((checks.filter(Boolean).length / checks.length) * 100);
  document.querySelector("#completionValue").textContent = `${completion}%`;
  document.querySelector("#completionBar").style.width = `${completion}%`;
}

document.querySelector("#printResumeButton").addEventListener("click", () => {
  renderPreview();
  window.print();
});

document.querySelector("#downloadTextButton").addEventListener("click", () => {
  renderPreview();
  const text = document.querySelector("#resumePreview").innerText;
  downloadFile(`${safeFileName(state.contact.fullName || "resume")}.txt`, text, "text/plain");
});

/* Cover letter */
const coverLetterForm = document.querySelector("#coverLetterForm");
const coverLetterOutput = document.querySelector("#coverLetterOutput");

function populateCoverLetterForm() {
  populateForm(coverLetterForm, state.coverLetter);
  coverLetterOutput.value = state.coverLetter.output || "";
}

populateCoverLetterForm();

function deriveRequirementPhrase(jobDescription) {
  const text = jobDescription.toLowerCase();
  const matches = [];
  if (text.includes("power bi")) matches.push("Power BI");
  if (text.includes("excel")) matches.push("Excel");
  if (text.includes("sql")) matches.push("SQL");
  if (text.includes("communication")) matches.push("stakeholder communication");
  if (text.includes("project")) matches.push("project coordination");
  if (text.includes("analysis") || text.includes("analytical")) matches.push("analytical problem-solving");
  return [...new Set(matches)].slice(0, 4);
}

coverLetterForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!coverLetterForm.reportValidity()) return;

  const formData = formToObject(coverLetterForm);
  const contact = state.contact;
  const requirements = deriveRequirementPhrase(formData.jobDescription);
  const skills = requirements.length
    ? requirements.join(", ")
    : state.skills.slice(0, 4).map((skill) => skill.name).join(", ");

  const manager = formData.coverHiringManager.trim() || "Hiring Manager";
  const company = formData.coverCompany.trim();
  const role = formData.coverJobTitle.trim();
  const summarySentence = state.summary.summaryText || "I offer a strong combination of analytical, organisational, and communication skills.";
  const firstExperience = state.experience[0];
  const evidence = firstExperience
    ? `In my recent role as ${firstExperience.title || "a professional"}, I contributed to ${normaliseLines(firstExperience.description)[0]?.replace(/\.$/, "") || "improving reporting and business processes"}.`
    : "Through academic and project work, I have developed a practical approach to solving problems and communicating clear findings.";

  const toneOpening = {
    Professional: "I am writing to express my interest",
    Confident: "I am excited to apply and confident that my background aligns well",
    Warm: "I am pleased to submit my application",
    Concise: "I am applying"
  }[formData.coverTone] || "I am writing to express my interest";

  const letter = `${contact.fullName || "Your Name"}
${[contact.city, contact.state, contact.country].filter(Boolean).join(", ")}
${contact.email || ""}
${contact.phone || ""}

${new Intl.DateTimeFormat("en", { day: "numeric", month: "long", year: "numeric" }).format(new Date())}

${manager}
${company}

Dear ${manager},

${toneOpening} for the ${role} position at ${company}. ${summarySentence}

My background has strengthened my capabilities in ${skills || "data analysis, project coordination, and communication"}. ${evidence} This experience taught me to work carefully with information, collaborate with different stakeholders, and translate requirements into practical outcomes.

I am particularly interested in ${company} because the role offers an opportunity to apply these strengths in a professional environment while continuing to develop. I would bring a dependable work ethic, strong attention to detail, and a genuine commitment to producing accurate, useful work.

Thank you for considering my application. I would welcome the opportunity to discuss how my experience and skills can support the ${role} team at ${company}.

Sincerely,

${contact.fullName || "Your Name"}`;

  coverLetterOutput.value = letter;
  state.coverLetter = { ...formData, output: letter };
  persistState("Cover letter generated.");
});

document.querySelector("#copyLetterButton").addEventListener("click", async () => {
  const text = coverLetterOutput.value.trim();
  if (!text) return showToast("Generate a cover letter first.");
  try {
    await navigator.clipboard.writeText(text);
    showToast("Cover letter copied.");
  } catch {
    coverLetterOutput.select();
    document.execCommand("copy");
    showToast("Cover letter copied.");
  }
});

document.querySelector("#downloadLetterButton").addEventListener("click", () => {
  const text = coverLetterOutput.value.trim();
  if (!text) return showToast("Generate a cover letter first.");
  const company = coverLetterForm.elements.coverCompany.value || "company";
  downloadFile(`cover-letter-${safeFileName(company)}.txt`, text, "text/plain");
});

/* Global save/export/reset */
function syncAllFormsToState() {
  state.contact = {
    ...state.contact,
    ...formToObject(contactForm),
    visibility: state.contact.visibility
  };
  state.coursework = formToObject(courseworkForm);
  state.summary = formToObject(summaryForm);
  state.coverLetter = {
    ...state.coverLetter,
    ...formToObject(coverLetterForm),
    output: coverLetterOutput.value
  };
}

document.querySelector("#saveAllButton").addEventListener("click", () => {
  syncAllFormsToState();
  persistState("All resume sections saved.");
});

document.querySelector("#exportDataButton").addEventListener("click", () => {
  syncAllFormsToState();
  downloadFile(`${safeFileName(state.contact.fullName || "resume")}-data.json`, JSON.stringify(state, null, 2), "application/json");
  showToast("Resume data exported.");
});

function safeFileName(value) {
  return String(value).toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "resume";
}

function downloadFile(name, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function openResetModal() {
  resetModal.classList.add("show");
  resetModal.setAttribute("aria-hidden", "false");
  document.querySelector("#cancelResetButton").focus();
}

document.querySelector("#newResumeButton").addEventListener("click", openResetModal);

document.querySelector("#cancelResetButton").addEventListener("click", closeResetModal);
resetModal.addEventListener("click", (event) => {
  if (event.target === resetModal) closeResetModal();
});

function closeResetModal() {
  resetModal.classList.remove("show");
  resetModal.setAttribute("aria-hidden", "true");
}

document.querySelector("#confirmResetButton").addEventListener("click", () => {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    console.warn("Could not clear saved builder data:", error);
  }
  state = clone(defaultData);
  populateForm(contactForm, state.contact);
  document.querySelector("#resumeYear").value = state.year;
  renderEntryList("experience");
  renderEntryList("project");
  renderEntryList("education");
  renderEntryList("certification");
  populateForm(courseworkForm, state.coursework);
  renderSkills();
  populateForm(summaryForm, state.summary);
  updateSummaryCount();
  populateCoverLetterForm();
  closeResetModal();
  navigate("contact");
  persistState("Blank resume created.");
});

/* Upload resume file */
const uploadModal = document.querySelector("#uploadModal");
const uploadDropZone = document.querySelector("#uploadDropZone");
const uploadFileName = document.querySelector("#uploadFileName");
const confirmUploadButton = document.querySelector("#confirmUploadButton");
const uploadResumeInput = document.querySelector("#uploadResumeInput");
let selectedUploadFile = null;

function openUploadModal(file) {
  selectedUploadFile = file || null;
  uploadFileName.textContent = file ? file.name : "";
  confirmUploadButton.disabled = !file;
  uploadDropZone.classList.remove("drag-over");
  uploadModal.classList.add("show");
  uploadModal.setAttribute("aria-hidden", "false");
}

function closeUploadModal() {
  uploadModal.classList.remove("show");
  uploadModal.setAttribute("aria-hidden", "true");
  selectedUploadFile = null;
}

uploadResumeInput.addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (!file) return;
  uploadResumeInput.value = "";
  openUploadModal(file);
});

uploadDropZone.addEventListener("click", () => {
  uploadResumeInput.click();
});

uploadDropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  uploadDropZone.classList.add("drag-over");
});

uploadDropZone.addEventListener("dragleave", () => {
  uploadDropZone.classList.remove("drag-over");
});

uploadDropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  uploadDropZone.classList.remove("drag-over");
  const file = event.dataTransfer.files[0];
  if (file) openUploadModal(file);
});

document.querySelector("#cancelUploadButton").addEventListener("click", closeUploadModal);
uploadModal.addEventListener("click", (event) => {
  if (event.target === uploadModal) closeUploadModal();
});

confirmUploadButton.addEventListener("click", async () => {
  if (!selectedUploadFile) return;
  confirmUploadButton.disabled = true;
  confirmUploadButton.textContent = "Importing...";

  const formData = new FormData();
  formData.append("file", selectedUploadFile);

  try {
    const response = await fetch("/api/upload-resume", { method: "POST", body: formData });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `Upload failed (${response.status})`);
    closeUploadModal();
    importParsedResume(data);
    persistState("Resume uploaded and imported.");
    navigate("contact");
  } catch (err) {
    console.error("Upload error:", err);
    showToast(err.message || "Upload failed. Please try again.");
  } finally {
    confirmUploadButton.disabled = false;
    confirmUploadButton.textContent = "Import Resume";
  }
});

function importParsedResume(data) {
  const contact = data.contact || {};
  state.contact.fullName = contact.name || "";
  state.contact.email = contact.email || "";
  state.contact.phone = contact.phone || "";
  state.contact.linkedin = contact.linkedin || "";
  state.contact.website = contact.website || "";
  if (contact.location) {
    const parts = contact.location.split(",").map(s => s.trim());
    state.contact.city = parts[0] || "";
    state.contact.state = parts[1] || "";
    state.contact.country = parts[2] || parts[1] || parts[0] || "";
  }

  state.summary.professionalTitle = data.headline || "";
  state.summary.summaryText = data.summary || "";

  state.skills = (data.skills || []).map(name => ({ name, level: "Intermediate" }));

  state.experience = (data.experience || []).map(item => ({
    title: item.title || "",
    company: item.company || "",
    location: item.location || "",
    type: "Full-time",
    start: item.start_date || "",
    end: item.end_date || "",
    description: (item.bullets || []).join("\n")
  }));

  state.project = (data.projects || []).map(item => ({
    name: item.title || "",
    role: "",
    link: "",
    tools: item.meta || "",
    start: item.start_date || "",
    end: item.end_date || "",
    description: (item.bullets || []).join("\n") || item.description || ""
  }));

  state.education = (data.education || []).map(item => ({
    qualification: item.degree || "",
    institution: item.institution || "",
    field: "",
    location: item.location || "",
    start: "",
    end: item.year || "",
    grade: item.cgpa || "",
    honours: "",
    description: ""
  }));

  state.certifications = (data.certifications || []).map(item => ({
    name: typeof item === "string" ? item : (item.name || item.title || ""),
    issuer: typeof item === "object" ? (item.issuer || "") : "",
    issue: typeof item === "object" ? (item.issue || item.issue_date || "") : "",
    expiry: typeof item === "object" ? (item.expiry || item.expiry_date || "") : "",
    credentialId: typeof item === "object" ? (item.credentialId || item.credential_id || "") : "",
    url: typeof item === "object" ? (item.url || "") : ""
  }));

  state.coursework.courseworkItems = "";
  state.coursework.courseworkTitle = "Relevant Coursework";

  /* Refresh all UI */
  populateForm(contactForm, state.contact);
  renderEntryList("experience");
  renderEntryList("project");
  renderEntryList("education");
  renderEntryList("certification");
  renderSkills();
  populateForm(summaryForm, state.summary);
  updateSummaryCount();
  showToast("Resume imported. Review each section and save.");
}

let autosaveTimer;
document.addEventListener("input", (event) => {
  if (!event.target.closest("form")) return;
  window.clearTimeout(autosaveTimer);
  autosaveTimer = window.setTimeout(() => {
    syncAllFormsToState();
    persistState("");
  }, 700);
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  closeResetModal();
  closeUploadModal();
});

/* Initialise */
const initialPage = window.location.hash.replace("#", "");
navigate(document.querySelector(`[data-page-panel="${initialPage}"]`) ? initialPage : "contact", false);

window.addEventListener("hashchange", () => {
  const page = window.location.hash.replace("#", "");
  if (document.querySelector(`[data-page-panel="${page}"]`)) navigate(page, false);
});

window.addEventListener("beforeunload", () => {
  syncAllFormsToState();
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
});
