const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/**
 * Basic request helper:
 * - parses JSON when available
 * - throws an Error message on non-2xx
 */
async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, options);

  const contentType = res.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");

  const body = isJson ? await res.json() : await res.text();

  if (!res.ok) {
    const message =
      (isJson && body && body.detail) ? body.detail :
      (typeof body === "string" && body.trim() ? body : `HTTP ${res.status}`);
    throw new Error(message);
  }

  return body;
}

//upload file via absolute path
export function uploadProjectFromPath(path) {
  return request("/projects/upload-path", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
}

// Projects

export function listProjects() {
  // GET /projects -> { projects: [{id, name}, ...] }
  return request("/projects");
}

export function getProject(id) {
  // GET /projects/{id} -> { project: {...} }
  return request(`/projects/${id}`);
}

export function uploadProjectZip(file) {
  // POST /projects/upload (multipart/form-data) -> { projects: [...] }
  const form = new FormData();
  form.append("zip_file", file); // MUST match UploadFile param name in routes.py

  return request("/projects/upload", {
    method: "POST",
    body: form,
  });
}

export function clearProjects() {
  // POST /projects/clear -> { ok: true }
  return request("/projects/clear", { method: "POST" });
}

// Skills

export function listSkills() {
  // GET /skills -> { skills: [{name, project_count}, ...] }
  return request("/skills");
}

export function getBadgeProgress() {
  return request("/badges/progress");
}

export function getYearlyWrapped() {
  return request("/wrapped/yearly");
}

// Privacy Consent
export function setPrivacyConsent(consent) {
  return request("/privacy-consent", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ consent }),
  });
}

// Reports

export function createReport({ title = null, sort_by = "resume_score", notes = null, project_ids = [] }) {
  return request("/reports", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, sort_by, notes, project_ids }),
  });
}

export function listReports() {
  return request("/reports");
}

export function getReport(id) {
  return request(`/reports/${id}`);
}

// Portfolio details generation (for a report)

export function generatePortfolioDetailsForReport({ report_id, project_names }) {
  return request(`/reports/${report_id}/portfolio-details/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report_id, project_names }),
  });
}

// Exports

export function exportResume({ report_id, template = "jake", output_name = "resume.pdf" }) {
  return request("/resume/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report_id, template, output_name }),
  });
}

export function downloadResumeUrl(export_id) {
  return `${BASE_URL}/resume/exports/${export_id}/download`;
}

export function exportPortfolio({ report_id, output_name = "portfolio.pdf" }) {
  return request("/portfolio/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report_id, output_name }),
  });
}

export function downloadPortfolioUrl(export_id) {
  return `${BASE_URL}/portfolio/exports/${export_id}/download`;
}