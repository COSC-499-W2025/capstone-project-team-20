const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/**
 * Basic request helper:
 * - parses JSON when available
 * - throws a useful Error message on non-2xx
 */
async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, options);

  const contentType = res.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");

  const body = isJson ? await res.json() : await res.text();

  if (!res.ok) {
    // FastAPI commonly returns {"detail": "..."} on errors
    const message =
      (isJson && body && body.detail) ? body.detail :
      (typeof body === "string" && body.trim() ? body : `HTTP ${res.status}`);
    throw new Error(message);
  }

  return body;
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
  // Your endpoint signature is: def upload_consent(consent: bool)
  // FastAPI will accept it as a query parameter:
  // POST /privacy-consent?consent=true
  return request(`/privacy-consent?consent=${consent}`, {
    method: "POST",
  });
}

// Resume / Portfolio placeholders

export function getResume(id) {
  return request(`/resume/${id}`);
}

export function generateResume() {
  return request("/resume/generate", { method: "POST" });
}

export function editResume(id) {
  return request(`/resume/${id}/edit`, { method: "POST" });
}

export function getPortfolio(id) {
  return request(`/portfolio/${id}`);
}

export function generatePortfolio() {
  return request("/portfolio/generate", { method: "POST" });
}

export function editPortfolio(id) {
  return request(`/portfolio/${id}/edit`, { method: "POST" });
}