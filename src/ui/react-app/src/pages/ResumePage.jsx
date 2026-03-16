import { useEffect, useRef, useState } from "react";
import {
  listProjects,
  createReport,
  listReports,
  getReport,
  exportResume,
  setPrivacyConsent,
  getResumeContext,
  patchReportProject,
  configSet,
} from "../api/client";

// ---------------------------------------------------------------------------
// Pencil button
// ---------------------------------------------------------------------------
function Pencil({ onClick }) {
  return (
    <button onClick={onClick} style={pencilBtn} title="Edit">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
      </svg>
    </button>
  );
}

const pencilBtn = {
  background: "none",
  border: "none",
  cursor: "pointer",
  fontSize: 11,
  padding: "0 3px",
  opacity: 0.55,
  lineHeight: 1,
  color: "#444",
  verticalAlign: "middle",
};

const smallBtn = {
  fontSize: 10,
  padding: "2px 8px",
  cursor: "pointer",
  border: "1px solid #ccc",
  borderRadius: 3,
  background: "transparent",
};

const inlineInput = {
  fontFamily: "inherit",
  fontSize: "inherit",
  fontWeight: "inherit",
  fontStyle: "normal",
  fontVariant: "normal",
  border: "none",
  borderBottom: "1px solid #666",
  outline: "none",
  background: "#f5f7ff",
  color: "#000",
  padding: "1px 3px",
  minWidth: 80,
};

// ---------------------------------------------------------------------------
// Inline single-line text editor
// ---------------------------------------------------------------------------
function InlineText({ value, onSave, style: extraStyle = {} }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const inputRef = useRef();

  useEffect(() => { setDraft(value); }, [value]);
  useEffect(() => { if (editing) inputRef.current?.focus(); }, [editing]);

  function commit() {
    setEditing(false);
    if (draft !== value) onSave(draft);
  }

  if (editing) {
    return (
      <input
        ref={inputRef}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") commit();
          if (e.key === "Escape") { setDraft(value); setEditing(false); }
        }}
        style={{ ...inlineInput, ...extraStyle }}
      />
    );
  }

  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 2 }}>
      <span style={extraStyle}>{value}</span>
      <Pencil onClick={() => setEditing(true)} />
    </span>
  );
}

// ---------------------------------------------------------------------------
// Bullet list editor
// ---------------------------------------------------------------------------
function BulletEditor({ bullets, onSave }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(bullets);

  useEffect(() => { setDraft(bullets); }, [bullets]);

  function commit() {
    setEditing(false);
    onSave(draft.filter((b) => b.trim()));
  }

  function cancel() { setDraft(bullets); setEditing(false); }

  if (!editing) {
    return (
      <ul style={styles.bulletList}>
        {bullets.map((b, i) => <li key={i} style={styles.bulletItem}>{b}</li>)}
        <li style={{ listStyle: "none", paddingLeft: 0, marginTop: 2 }}>
          <Pencil onClick={() => setEditing(true)} />
        </li>
      </ul>
    );
  }

  return (
    <div style={{ marginTop: 4 }}>
      {draft.map((b, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 3 }}>
          <span style={{ fontSize: 10, color: "#888" }}>•</span>
          <input
            value={b}
            onChange={(e) => setDraft((prev) => prev.map((x, idx) => idx === i ? e.target.value : x))}
            onKeyDown={(e) => { if (e.key === "Escape") cancel(); }}
            style={{ ...inlineInput, borderBottom: "1px solid #aaa", flex: 1, fontSize: 10 }}
          />
          <button
            onClick={() => setDraft((prev) => prev.filter((_, idx) => idx !== i))}
            style={{ ...pencilBtn, opacity: 0.5, fontSize: 10 }}
          >✕</button>
        </div>
      ))}
      <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
        <button onClick={() => setDraft((prev) => [...prev, ""])} style={smallBtn}>+ Add</button>
        <button onClick={commit} style={smallBtn}>Save</button>
        <button onClick={cancel} style={smallBtn}>Cancel</button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Education entry editor
// Fields: school, location, degree, dates
// ---------------------------------------------------------------------------
function EducationEditor({ education, onSave }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(education);

  useEffect(() => { setDraft(education); }, [education]);

  function updateField(i, field, val) {
    setDraft((prev) => prev.map((e, idx) => idx === i ? { ...e, [field]: val } : e));
  }

  function addEntry() {
    setDraft((prev) => [...prev, { school: "", location: "", degree: "", dates: "" }]);
  }

  function removeEntry(i) {
    setDraft((prev) => prev.filter((_, idx) => idx !== i));
  }

  function commit() {
    setEditing(false);
    onSave(draft.filter((e) => e.school || e.degree));
  }

  function cancel() { setDraft(education); setEditing(false); }

  if (!editing) {
    return (
      <>
        {education.map((edu, i) => (
          <div key={i} style={styles.subheading}>
            <div style={styles.subheadingRow}>
              <strong>{edu.school}</strong>
              <span>{edu.location}</span>
            </div>
            <div style={styles.subheadingRow}>
              <em style={styles.small}>{edu.degree}</em>
              <em style={styles.small}>{edu.dates}</em>
            </div>
          </div>
        ))}
        <Pencil onClick={() => setEditing(true)} />
      </>
    );
  }

  return (
    <div>
      {draft.map((edu, i) => (
        <div key={i} style={{ marginBottom: 10, paddingBottom: 8, borderBottom: "1px dashed #ddd" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, marginBottom: 4 }}>
            {[["school", "School"], ["location", "Location"], ["degree", "Degree"], ["dates", "Dates"]].map(([field, label]) => (
              <div key={field}>
                <div style={{ fontSize: 9, color: "#888", marginBottom: 1 }}>{label}</div>
                <input
                  value={edu[field] || ""}
                  onChange={(e) => updateField(i, field, e.target.value)}
                  style={{ ...inlineInput, borderBottom: "1px solid #aaa", width: "100%", fontSize: 10 }}
                />
              </div>
            ))}
          </div>
          <button onClick={() => removeEntry(i)} style={{ ...smallBtn, color: "#c00" }}>Remove</button>
        </div>
      ))}
      <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
        <button onClick={addEntry} style={smallBtn}>+ Add Entry</button>
        <button onClick={commit} style={smallBtn}>Save</button>
        <button onClick={cancel} style={smallBtn}>Cancel</button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Experience entry editor
// Fields: title, company, location, dates, bullets
// ---------------------------------------------------------------------------
function ExperienceEditor({ experience, onSave }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(experience);

  useEffect(() => { setDraft(experience); }, [experience]);

  function updateField(i, field, val) {
    setDraft((prev) => prev.map((e, idx) => idx === i ? { ...e, [field]: val } : e));
  }

  function updateBullet(i, j, val) {
    setDraft((prev) => prev.map((e, idx) =>
      idx === i ? { ...e, bullets: e.bullets.map((b, bIdx) => bIdx === j ? val : b) } : e
    ));
  }

  function addBullet(i) {
    setDraft((prev) => prev.map((e, idx) =>
      idx === i ? { ...e, bullets: [...(e.bullets || []), ""] } : e
    ));
  }

  function removeBullet(i, j) {
    setDraft((prev) => prev.map((e, idx) =>
      idx === i ? { ...e, bullets: e.bullets.filter((_, bIdx) => bIdx !== j) } : e
    ));
  }

  function addEntry() {
    setDraft((prev) => [...prev, { title: "", company: "", location: "", dates: "", bullets: [] }]);
  }

  function removeEntry(i) {
    setDraft((prev) => prev.filter((_, idx) => idx !== i));
  }

  function commit() {
    setEditing(false);
    onSave(draft.filter((e) => e.title || e.company));
  }

  function cancel() { setDraft(experience); setEditing(false); }

  if (!editing) {
    return (
      <>
        {experience.map((job, i) => (
          <div key={i} style={styles.subheading}>
            <div style={styles.subheadingRow}>
              <strong>{job.title}</strong>
              <span>{job.dates}</span>
            </div>
            <div style={styles.subheadingRow}>
              <em style={styles.small}>{job.company}</em>
              <em style={styles.small}>{job.location}</em>
            </div>
            <ul style={styles.bulletList}>
              {(job.bullets || []).map((b, j) => <li key={j} style={styles.bulletItem}>{b}</li>)}
            </ul>
          </div>
        ))}
        <Pencil onClick={() => setEditing(true)} />
      </>
    );
  }

  return (
    <div>
      {draft.map((job, i) => (
        <div key={i} style={{ marginBottom: 12, paddingBottom: 10, borderBottom: "1px dashed #ddd" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, marginBottom: 6 }}>
            {[["title", "Title"], ["company", "Company"], ["location", "Location"], ["dates", "Dates"]].map(([field, label]) => (
              <div key={field}>
                <div style={{ fontSize: 9, color: "#888", marginBottom: 1 }}>{label}</div>
                <input
                  value={job[field] || ""}
                  onChange={(e) => updateField(i, field, e.target.value)}
                  style={{ ...inlineInput, borderBottom: "1px solid #aaa", width: "100%", fontSize: 10 }}
                />
              </div>
            ))}
          </div>
          <div style={{ fontSize: 9, color: "#888", marginBottom: 4 }}>Bullets</div>
          {(job.bullets || []).map((b, j) => (
            <div key={j} style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 3 }}>
              <span style={{ fontSize: 10, color: "#888" }}>•</span>
              <input
                value={b}
                onChange={(e) => updateBullet(i, j, e.target.value)}
                style={{ ...inlineInput, borderBottom: "1px solid #aaa", flex: 1, fontSize: 10 }}
              />
              <button onClick={() => removeBullet(i, j)} style={{ ...pencilBtn, opacity: 0.5, fontSize: 10 }}>✕</button>
            </div>
          ))}
          <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
            <button onClick={() => addBullet(i)} style={smallBtn}>+ Bullet</button>
            <button onClick={() => removeEntry(i)} style={{ ...smallBtn, color: "#c00" }}>Remove Entry</button>
          </div>
        </div>
      ))}
      <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
        <button onClick={addEntry} style={smallBtn}>+ Add Entry</button>
        <button onClick={commit} style={smallBtn}>Save</button>
        <button onClick={cancel} style={smallBtn}>Cancel</button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Resume preview with full inline editing
// ---------------------------------------------------------------------------
function ResumePreview({ ctx, reportId, onContextChange }) {
  if (!ctx) return null;

  const {
    name, phone, email,
    github_url, github_display,
    linkedin_url, linkedin_display,
    education = [], experience = [], projects = [], skills = {},
  } = ctx;

  async function saveConfigField(field, value) {
    try {
      await configSet(field, value);
      onContextChange({ ...ctx, [field]: value });
    } catch (e) {
      console.error("Failed to save config field:", e);
    }
  }

  async function saveProjectField(projectName, patch) {
    try {
      await patchReportProject(reportId, projectName, patch);
      const updatedProjects = ctx.projects.map((p) => {
        if (p.name !== projectName) return p;
        const next = { ...p };
        if (patch.bullets !== undefined) next.bullets = patch.bullets;
        if (patch.project_name !== undefined) next.name = patch.project_name;
        if (patch.stack_languages !== undefined || patch.stack_frameworks !== undefined) {
          next.stack = [
            ...(patch.stack_languages ?? []),
            ...(patch.stack_frameworks ?? []),
          ].join(", ");
        }
        return next;
      });
      onContextChange({ ...ctx, projects: updatedProjects });
    } catch (e) {
      console.error("Failed to save project field:", e);
    }
  }

  return (
    <div style={styles.page}>

      {/* HEADING */}
      <div style={styles.heading}>
        <div style={styles.headingName}>
          <InlineText
            value={name}
            onSave={(v) => saveConfigField("name", v)}
            style={{ fontSize: 22, fontWeight: "bold", fontVariant: "small-caps", letterSpacing: 1 }}
          />
        </div>
        <div style={styles.headingContact}>
          <InlineText value={phone} onSave={(v) => saveConfigField("phone", v)} />
          {" | "}
          <InlineText value={email} onSave={(v) => saveConfigField("email", v)} />
          {linkedin_url && <>{" | "}<a href={linkedin_url} style={styles.link}>{linkedin_display}</a></>}
          {github_url && <>{" | "}<a href={github_url} style={styles.link}>{github_display}</a></>}
        </div>
      </div>

      {/* EDUCATION */}
      {(education.length > 0) && (
        <section>
          <div style={styles.sectionTitle}>Education</div>
          <hr style={styles.rule} />
          <EducationEditor
            education={education}
            onSave={(updated) => saveConfigField("education", updated)}
          />
        </section>
      )}

      {/* EXPERIENCE */}
      {(experience.length > 0) && (
        <section>
          <div style={styles.sectionTitle}>Experience</div>
          <hr style={styles.rule} />
          <ExperienceEditor
            experience={experience}
            onSave={(updated) => saveConfigField("experience", updated)}
          />
        </section>
      )}

      {/* PROJECTS */}
      {projects.length > 0 && (
        <section>
          <div style={styles.sectionTitle}>Projects</div>
          <hr style={styles.rule} />
          {projects.map((proj, i) => (
            <div key={i} style={styles.subheading}>
              <div style={styles.subheadingRow}>
                <span>
                  <InlineText
                    value={proj.name}
                    onSave={(v) => saveProjectField(proj.name, { project_name: v })}
                    style={{ fontWeight: "bold" }}
                  />
                  {proj.stack && (
                    <>
                      {" | "}
                      <InlineText
                        value={proj.stack}
                        onSave={(v) => saveProjectField(proj.name, {
                          stack_languages: v.split(",").map((s) => s.trim()).filter(Boolean),
                          stack_frameworks: [],
                        })}
                        style={{ fontStyle: "italic" }}
                      />
                    </>
                  )}
                </span>
                <span style={styles.small}>{proj.dates}</span>
              </div>
              <BulletEditor
                bullets={proj.bullets || []}
                onSave={(bullets) => saveProjectField(proj.name, { bullets })}
              />
            </div>
          ))}
        </section>
      )}

      {/* TECHNICAL SKILLS — derived, read-only */}
      {Object.keys(skills).length > 0 && (
        <section>
          <div style={styles.sectionTitle}>Technical Skills</div>
          <hr style={styles.rule} />
          <ul style={{ ...styles.bulletList, marginTop: 4 }}>
            {Object.entries(skills).map(([cat, items]) => (
              <li key={cat} style={{ ...styles.bulletItem, listStyle: "none", paddingLeft: 0 }}>
                <strong>{cat}:</strong> {Array.isArray(items) ? items.join(", ") : items}
              </li>
            ))}
          </ul>
        </section>
      )}

    </div>
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------
const styles = {
  page: {
    fontFamily: "'Times New Roman', Times, serif",
    fontSize: 11,
    color: "#000",
    background: "#fff",
    width: 740,
    minHeight: 960,
    padding: "36px 48px",
    boxSizing: "border-box",
    boxShadow: "0 2px 12px rgba(0,0,0,0.15)",
    margin: "0 auto",
  },
  heading: { textAlign: "center", marginBottom: 8 },
  headingName: { fontSize: 22, fontWeight: "bold", fontVariant: "small-caps", letterSpacing: 1 },
  headingContact: { fontSize: 11, marginTop: 2 },
  link: { color: "#000", textDecoration: "underline" },
  sectionTitle: {
    fontSize: 13, fontVariant: "small-caps", fontWeight: "bold",
    marginTop: 10, marginBottom: 2, letterSpacing: 0.5,
  },
  rule: { border: "none", borderTop: "1px solid #000", margin: "2px 0 6px 0" },
  subheading: { marginBottom: 6 },
  subheadingRow: { display: "flex", justifyContent: "space-between", fontSize: 11 },
  small: { fontSize: 10 },
  bulletList: { margin: "2px 0 0 0", paddingLeft: 20 },
  bulletItem: { fontSize: 10, marginBottom: 1 },
};

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
function ResumePage() {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [projects, setProjects] = useState([]);
  const [selectedProjectIds, setSelectedProjectIds] = useState([]);
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [reportTitle, setReportTitle] = useState("My Resume Report");
  const [reportNotes, setReportNotes] = useState("");
  const [previewCtx, setPreviewCtx] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => { loadInitialData(); }, []);

  async function loadInitialData() {
    setLoading(true);
    setMessage("");
    try {
      const [projectData, reportData] = await Promise.all([listProjects(), listReports()]);
      const allProjects = projectData.projects ?? [];
      setProjects(allProjects);
      setSelectedProjectIds(allProjects.map((p) => p.id));
      setReports(reportData.reports ?? []);
      if (selectedReport?.id) {
        const refreshed = (reportData.reports ?? []).find((r) => r.id === selectedReport.id);
        setSelectedReport(refreshed ?? selectedReport);
      }
    } catch (e) {
      setMessage(e.message ?? "Failed to load data");
    } finally {
      setLoading(false);
    }
  }

  function toggleProject(id) {
    setSelectedProjectIds((prev) =>
      prev.includes(id) ? prev.filter((pid) => pid !== id) : [...prev, id]
    );
  }

  async function handleCreateReport() {
    setLoading(true);
    setMessage("");
    try {
      await setPrivacyConsent(true);
      if (!selectedProjectIds.length) { setMessage("Select at least one project first."); return; }
      const created = await createReport({
        title: reportTitle, sort_by: "resume_score",
        notes: reportNotes, project_ids: selectedProjectIds,
      });
      const report = created.report ?? null;
      setSelectedReport(report);
      setMessage(`Created report "${report?.title ?? "Untitled"}"`);
      await loadInitialData();
      if (report?.id) await loadPreview(report.id);
    } catch (e) {
      setMessage(e.message ?? "Failed to create report");
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectReport(id) {
    setLoading(true);
    setMessage("");
    try {
      const data = await getReport(id);
      const report = data.report ?? null;
      setSelectedReport(report);
      if (report?.id) await loadPreview(report.id);
    } catch (e) {
      setMessage(e.message ?? "Failed to load report");
    } finally {
      setLoading(false);
    }
  }

  async function loadPreview(reportId) {
    setPreviewLoading(true);
    setPreviewCtx(null);
    try {
      const ctx = await getResumeContext(reportId);
      setPreviewCtx(ctx);
    } catch (e) {
      setMessage(e.message ?? "Failed to load preview");
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handleExportResume() {
    if (!selectedReport?.id) { setMessage("Select or create a report first."); return; }
    setLoading(true);
    setMessage("");
    try {
      const exp = await exportResume({ report_id: selectedReport.id, template: "jake", output_name: "resume.pdf" });
      window.open(`http://localhost:8000${exp.download_url}`, "_blank");
      setMessage("Resume exported.");
    } catch (e) {
      setMessage(e.message ?? "Failed to export resume");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <h3>Resume</h3>

      <button onClick={loadInitialData} disabled={loading}>
        {loading ? "Loading..." : "Refresh"}
      </button>

      <div style={{ display: "flex", gap: 24, marginTop: 16, alignItems: "flex-start" }}>

        {/* LEFT — controls */}
        <div style={{ minWidth: 280, maxWidth: 320 }}>
          <div style={{ padding: 12, border: "1px solid #ddd", borderRadius: 8, marginBottom: 16 }}>
            <h4 style={{ marginTop: 0 }}>Create Report</h4>
            <div style={{ marginBottom: 10 }}>
              <label>Title</label><br />
              <input
                type="text"
                value={reportTitle}
                onChange={(e) => setReportTitle(e.target.value)}
                style={{ width: "100%" }}
              />
            </div>
            <div style={{ marginBottom: 10 }}>
              <label>Notes</label><br />
              <textarea
                value={reportNotes}
                onChange={(e) => setReportNotes(e.target.value)}
                rows={3}
                style={{ width: "100%" }}
              />
            </div>
            <h4>Projects</h4>
            {projects.length === 0 ? <p>No projects found.</p> : (
              <ul style={{ listStyle: "none", paddingLeft: 0 }}>
                {projects.map((p) => (
                  <li key={p.id} style={{ marginBottom: 6 }}>
                    <label>
                      <input
                        type="checkbox"
                        checked={selectedProjectIds.includes(p.id)}
                        onChange={() => toggleProject(p.id)}
                        style={{ marginRight: 8 }}
                      />
                      {p.name}
                    </label>
                  </li>
                ))}
              </ul>
            )}
            <button onClick={handleCreateReport} disabled={loading}>
              {loading ? "Working..." : "Create Report"}
            </button>
          </div>

          <div>
            <h4>Saved Reports</h4>
            {reports.length === 0 ? <p>No reports yet.</p> : (
              <ul style={{ paddingLeft: 16 }}>
                {reports.map((r) => (
                  <li key={r.id}>
                    <button
                      onClick={() => handleSelectReport(r.id)}
                      disabled={loading}
                      style={{
                        background: "transparent", border: "none", cursor: "pointer", padding: 0,
                        color: selectedReport?.id === r.id ? "var(--accent, #0066cc)" : "var(--text)",
                        fontWeight: selectedReport?.id === r.id ? "bold" : "normal",
                      }}
                    >
                      {r.title ?? `Report #${r.id}`}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div style={{ marginTop: 16 }}>
            <button onClick={handleExportResume} disabled={loading || !selectedReport?.id}>
              Export PDF
            </button>
          </div>

          {message && <p style={{ marginTop: 10, fontSize: 13 }}>{message}</p>}
        </div>

        {/* RIGHT — live preview */}
        <div style={{ flex: 1, overflowX: "auto" }}>
          {previewLoading && <p>Loading preview...</p>}
          {!previewLoading && !previewCtx && (
            <p style={{ color: "#888" }}>Select or create a report to preview.</p>
          )}
          {!previewLoading && previewCtx && (
            <ResumePreview
              ctx={previewCtx}
              reportId={selectedReport?.id}
              onContextChange={setPreviewCtx}
            />
          )}
        </div>

      </div>
    </>
  );
}

export default ResumePage;
