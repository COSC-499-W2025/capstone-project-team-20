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

export async function deleteProject(id) {
  const res = await fetch(`${BASE_URL}/projects/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
}


export function resolveContributors(project_id, resolutions) {
  return request("/projects/resolve-contributors", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id,
      resolutions,
    }),
  });
}

export function resolveContributorsBatch(pendingDuplicates, mergeSelections) {
  const projects = pendingDuplicates.map((project) => ({
    project_id: project.project_id,
    resolutions: (project.duplicate_groups ?? []).map((group) => {
      const key = `${project.project_id}::${group.suggested_canonical}`;
      return {
        canonical: mergeSelections[key] || group.suggested_canonical,
        merge: group.candidates,
      };
    }),
  }));

  return request("/projects/resolve-contributors-batch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ projects }),
  });
}

// Skills

export function listSkills() {
  // GET /skills -> { skills: [{name, project_count}, ...] }
  return request("/skills");
}

export function listSkillsUsage() {
  // GET /skills/usage -> { skills: [{name, project_count, projects: [...]}, ...] }
  return request("/skills/usage");
}

export function getBadgeProgress() {
  return request("/badges/progress");
}

export function getYearlyWrapped() {
  return request("/wrapped/yearly");
}

// Privacy Consent

export function getPrivacyConsent() {
  return request("/privacy-consent").then((data) => !!(data.consent ?? false));
}

export function setPrivacyConsent(consent) {
  return request("/privacy-consent", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ consent }),
  });
}

// Reports

export function createReport({ title = null, sort_by = "resume_score", notes = null, report_kind = "resume", project_ids = [] }) {
  return request("/reports", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, sort_by, notes, report_kind, project_ids }),
  });
}

export function listReports() {
  return request("/reports");
}

export function getReport(id) {
  return request(`/reports/${id}`);
}

export async function deleteReport(id) {
  const res = await fetch(`${BASE_URL}/reports/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
}

// Portfolio details generation (for a report)

export function generatePortfolioDetailsForReport({ report_id, project_names }) {
  return request(`/reports/${report_id}/portfolio-details/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report_id, project_names }),
  });
}

export function getPortfolio(report_id) {
  return request(`/portfolio/${report_id}`);
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

export function deleteResumeExport(export_id) {
  return request(`/resume/exports/${export_id}`, { method: "DELETE" });
}

export function getResumeContext(report_id) {
  return request(`/resume/context/${report_id}`);
}

export function patchReportProject(report_id, project_name, patch) {
  return request(`/reports/${report_id}/projects/${encodeURIComponent(project_name)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
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

export function getConfig() {
  return request("/config").then((data) => data.config);
}

export function saveConfig({ name, email, phone, github, linkedin }) {
  return request("/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, phone, github, linkedin }),
  });
}

export function updatePortfolioMode(report_id, mode) {
  return request(`/portfolio/${report_id}/mode`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode }),
  });
}

export function updatePortfolioProject(report_id, project_name, payload) {
  return request(`/portfolio/${report_id}/projects/${encodeURIComponent(project_name)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function publishPortfolio(report_id) {
  return request(`/portfolio/${report_id}/publish`, { method: "POST" });
}

export function unpublishPortfolio(report_id) {
  return request(`/portfolio/${report_id}/unpublish`, { method: "POST" });
}

export function uploadThumbnail(project_id, file) {
  const form = new FormData();
  form.append("file", file);
  return request(`/projects/${project_id}/thumbnail`, {
    method: "POST",
    body: form,
  });
}

export function thumbnailUrl(thumbnail_path) {
  if (!thumbnail_path) return null;
  const filename = thumbnail_path.split(/[\\/]/).pop();
  return `${BASE_URL}/thumbnails/${filename}`;
}

export function configSet(key, value) {
  return request("/config/set", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key, value }),
  });
}

export function setIdentity(emails, projectIds) {
  return request("/projects/set-identity", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ emails, project_ids: projectIds }),
  });
}

export function updateUsernames(emails) {
  return request("/config/usernames", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ emails }),
  });
}
