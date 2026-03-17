import { useEffect, useRef, useState } from "react";
import {
  listProjects,
  createReport,
  listReports,
  getReport,
  deleteReport,
  exportResume,
  setPrivacyConsent,
  getResumeContext,
  patchReportProject,
  configSet,
} from "../api/client";

// ---------------------------------------------------------------------------
// Pencil + Trash icon buttons
// ---------------------------------------------------------------------------
function Pencil({ onClick }) {
  return (
    <button onClick={onClick} style={pencilBtn} title="Edit">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
  padding: "0 3px",
  opacity: 0.5,
  lineHeight: 1,
  color: "currentColor",
  verticalAlign: "middle",
};

function Trash({ onClick }) {
  return (
    <button onClick={onClick} style={{ ...pencilBtn, opacity: 0.45 }} title="Delete report">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="3 6 5 6 21 6"/>
        <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
        <path d="M10 11v6M14 11v6"/>
        <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
      </svg>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Confirm modal — same visual language as Projects.jsx
// ---------------------------------------------------------------------------
function ConfirmModal({ title, message, confirmLabel = "Delete", onConfirm, onCancel }) {
  return (
    <>
      <style>{MODAL_CSS}</style>
      <div className="rs-overlay">
        <div className="rs-modal">
          <div className="rs-bar" aria-hidden="true" />
          <div className="rs-confirm-body">
            <div className="rs-confirm-icon">⚠️</div>
            <h2 className="rs-confirm-title">{title}</h2>
            <p className="rs-confirm-sub">{message}</p>
          </div>
          <div className="rs-modal-footer">
            <button className="rs-btn rs-btn--ghost" onClick={onCancel}>← Go back</button>
            <button className="rs-btn rs-btn--danger" onClick={onConfirm}>{confirmLabel}</button>
          </div>
        </div>
      </div>
    </>
  );
}


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
// Inline single-line text editor — width tracks content length
// ---------------------------------------------------------------------------
function InlineText({ value, onSave, style: extraStyle = {} }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const inputRef = useRef();
  const sizerRef = useRef();

  useEffect(() => { setDraft(value); }, [value]);
  useEffect(() => { if (editing) inputRef.current?.focus(); }, [editing]);

  // Measure text width via a hidden sizer span so input grows with content
  const [inputWidth, setInputWidth] = useState(80);
  useEffect(() => {
    if (sizerRef.current) {
      const w = sizerRef.current.offsetWidth;
      setInputWidth(Math.max(80, w + 16));
    }
  }, [draft]);

  function commit() {
    setEditing(false);
    if (draft !== value) onSave(draft);
  }

  if (editing) {
    return (
      <>
        {/* Hidden sizer — mirrors input text to measure natural width */}
        <span
          ref={sizerRef}
          aria-hidden
          style={{
            ...inlineInput,
            ...extraStyle,
            position: "absolute",
            visibility: "hidden",
            whiteSpace: "pre",
            pointerEvents: "none",
          }}
        >{draft || " "}</span>
        <input
          ref={inputRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === "Enter") commit();
            if (e.key === "Escape") { setDraft(value); setEditing(false); }
          }}
          style={{ ...inlineInput, ...extraStyle, width: inputWidth }}
        />
      </>
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
function ResumePreview({ ctx, reportId, reportNotes, onContextChange }) {
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
const formLabel = {
  display: "block",
  fontSize: 11,
  fontWeight: 600,
  color: "#555",
  marginBottom: 4,
  textTransform: "uppercase",
  letterSpacing: 0.4,
};

const formInput = {
  width: "100%",
  boxSizing: "border-box",
  fontSize: 13,
  padding: "6px 8px",
  border: "1px solid #d0d0d0",
  borderRadius: 5,
  outline: "none",
  background: "var(--bg, #fff)",
  color: "var(--text, #000)",
  fontFamily: "inherit",
};

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
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);

  useEffect(() => { loadInitialData(); }, []);

  async function loadInitialData() {
    setLoading(true);
    setMessage("");
    try {
      const [projectData, reportData] = await Promise.all([listProjects(), listReports()]);
      const allProjects = projectData.projects ?? [];
      setProjects(allProjects);
      setSelectedProjectIds(allProjects.map((p) => p.id));
      const filteredReports = (reportData.reports ?? []).filter((r) => (r.report_kind ?? "resume") === "resume");
      setReports(filteredReports);

      if (selectedReport?.id) {
        const refreshed = filteredReports.find((r) => r.id === selectedReport.id);
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
        notes: reportNotes, report_kind: "resume",
        project_ids: selectedProjectIds,
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

  async function handleDeleteReport(id) {
    try {
      await deleteReport(id);
    } catch (e) {
      // 204 No Content comes back as empty string from request() — not a real error
      if (e.message && e.message !== "") {
        setMessage(e.message);
        return;
      }
    }
    // Always run cleanup regardless — deletion succeeded even if response parsing threw
    setConfirmDeleteId(null);
    setReports((prev) => prev.filter((r) => r.id !== id));
    if (selectedReport?.id === id) {
      setSelectedReport(null);
      setPreviewCtx(null);
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
              <label style={formLabel}>Title</label>
              <input
                type="text"
                value={reportTitle}
                onChange={(e) => setReportTitle(e.target.value)}
                style={formInput}
              />
            </div>
            <div style={{ marginBottom: 10 }}>
              <label style={formLabel}>Notes</label>
              <textarea
                value={reportNotes}
                onChange={(e) => setReportNotes(e.target.value)}
                rows={3}
                placeholder="e.g. Use for software engineering roles"
                style={{ ...formInput, resize: "vertical", lineHeight: 1.4 }}
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
              <ul style={{ paddingLeft: 0, listStyle: "none" }}>
                {reports.map((r) => (
                  <li key={r.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                    <button
                      onClick={() => handleSelectReport(r.id)}
                      disabled={loading}
                      style={{
                        background: "transparent", border: "none", cursor: "pointer", padding: 0,
                        color: selectedReport?.id === r.id ? "var(--accent, #0066cc)" : "var(--text)",
                        fontWeight: selectedReport?.id === r.id ? "bold" : "normal",
                        textAlign: "left", flex: 1,
                      }}
                    >
                      {r.title ?? `Report #${r.id}`}
                    </button>
                    <Trash onClick={() => setConfirmDeleteId(r.id)} />
                  </li>
                ))}
              </ul>
            )}
            {selectedReport?.notes && (
              <p style={{ fontSize: 12, color: "#666", fontStyle: "italic", marginTop: 6, borderLeft: "2px solid #ddd", paddingLeft: 8 }}>
                {selectedReport.notes}
              </p>
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
              reportNotes={selectedReport?.notes}
              onContextChange={setPreviewCtx}
            />
          )}
        </div>

      </div>

      {confirmDeleteId && (
        <ConfirmModal
          title="Delete report?"
          message="This will permanently delete the report. Your projects won't be affected."
          confirmLabel="Yes, delete"
          onConfirm={() => handleDeleteReport(confirmDeleteId)}
          onCancel={() => setConfirmDeleteId(null)}
        />
      )}
    </>
  );
}

export default ResumePage;

// ---------------------------------------------------------------------------
// Modal CSS — mirrors Projects.jsx pj-* pattern under rs-* namespace
// ---------------------------------------------------------------------------
const MODAL_CSS = `
.rs-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center;
}
.rs-modal {
  --accent:  #58a6ff;
  --accent2: #f78166;
  --bg:      #0d1117;
  --surface: #161b22;
  --border:  #30363d;
  --text:    #e6edf3;
  --muted:   #8b949e;
  --r:       10px;
  width: min(420px, 90vw);
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 16px; overflow: hidden;
  display: flex; flex-direction: column;
  box-shadow: 0 24px 64px rgba(0,0,0,.6), 0 0 0 1px rgba(88,166,255,.06);
  font-family: 'DM Sans', 'Segoe UI', system-ui, sans-serif;
  animation: rs-fadein .2s ease both;
}
@keyframes rs-fadein {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.rs-bar {
  height: 3px; flex-shrink: 0;
  background: linear-gradient(90deg, var(--accent), var(--accent2), var(--accent));
  background-size: 200% 100%;
  animation: rs-shimmer 3s linear infinite;
}
@keyframes rs-shimmer {
  0%   { background-position: 200% center; }
  100% { background-position: -200% center; }
}
.rs-confirm-body {
  flex: 1;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 36px 32px 24px;
  text-align: center;
}
.rs-confirm-icon { font-size: 32px; margin-bottom: 12px; }
.rs-confirm-title {
  font-size: 18px; font-weight: 700; color: var(--text);
  margin: 0 0 10px;
}
.rs-confirm-sub {
  font-size: 13px; color: var(--muted); line-height: 1.6;
  max-width: 320px; margin: 0;
}
.rs-modal-footer {
  padding: 12px 24px; flex-shrink: 0;
  border-top: 1px solid var(--border);
  display: flex; justify-content: flex-end; align-items: center; gap: 8px;
}
.rs-btn {
  display: inline-flex; align-items: center; justify-content: center;
  height: 36px; padding: 0 16px; border-radius: var(--r);
  font-size: 13px; font-weight: 600; cursor: pointer;
  border: 1.5px solid transparent; font-family: inherit;
  transition: all .15s;
}
.rs-btn--ghost {
  background: transparent; color: var(--muted); border-color: var(--border);
}
.rs-btn--ghost:hover { border-color: var(--muted); color: var(--text); }
.rs-btn--danger {
  background: transparent; color: #f85149; border-color: #f85149;
}
.rs-btn--danger:hover { border-color: #ff7b72; color: #ff7b72; }
`;
