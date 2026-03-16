import { useEffect, useState } from "react";
import {
  listProjects,
  createReport,
  listReports,
  getReport,
  exportResume,
  setPrivacyConsent,
  getResumeContext,
  getConfig,
} from "../api/client";

// ---------------------------------------------------------------------------
// Jake-style resume rendered in HTML
// ---------------------------------------------------------------------------
function ResumePreview({ ctx }) {
  if (!ctx) return null;

  const {
    name, phone, email,
    github_url, github_display,
    linkedin_url, linkedin_display,
    education = [], experience = [], projects = [], skills = {},
  } = ctx;

  return (
    <div style={styles.page}>
      {/* HEADING */}
      <div style={styles.heading}>
        <div style={styles.headingName}>{name}</div>
        <div style={styles.headingContact}>
          {phone}
          {email && <> &nbsp;|&nbsp; <a href={`mailto:${email}`} style={styles.link}>{email}</a></>}
          {linkedin_url && <> &nbsp;|&nbsp; <a href={linkedin_url} style={styles.link}>{linkedin_display}</a></>}
          {github_url && <> &nbsp;|&nbsp; <a href={github_url} style={styles.link}>{github_display}</a></>}
        </div>
      </div>

      {/* EDUCATION */}
      {education.length > 0 && (
        <section>
          <div style={styles.sectionTitle}>Education</div>
          <hr style={styles.rule} />
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
        </section>
      )}

      {/* EXPERIENCE */}
      {experience.length > 0 && (
        <section>
          <div style={styles.sectionTitle}>Experience</div>
          <hr style={styles.rule} />
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
                {(job.bullets || []).map((b, j) => (
                  <li key={j} style={styles.bulletItem}>{b}</li>
                ))}
              </ul>
            </div>
          ))}
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
                  <strong>{proj.name}</strong>
                  {proj.stack && <> &nbsp;|&nbsp; <em>{proj.stack}</em></>}
                </span>
                <span style={styles.small}>{proj.dates}</span>
              </div>
              <ul style={styles.bulletList}>
                {(proj.bullets || []).map((b, j) => (
                  <li key={j} style={styles.bulletItem}>{b}</li>
                ))}
              </ul>
            </div>
          ))}
        </section>
      )}

      {/* TECHNICAL SKILLS */}
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
// Jake resume styles — letter-page feel, tight spacing
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
  heading: {
    textAlign: "center",
    marginBottom: 8,
  },
  headingName: {
    fontSize: 22,
    fontWeight: "bold",
    fontVariant: "small-caps",
    letterSpacing: 1,
  },
  headingContact: {
    fontSize: 11,
    marginTop: 2,
  },
  link: {
    color: "#000",
    textDecoration: "underline",
  },
  sectionTitle: {
    fontSize: 13,
    fontVariant: "small-caps",
    fontWeight: "bold",
    marginTop: 10,
    marginBottom: 2,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  rule: {
    border: "none",
    borderTop: "1px solid #000",
    margin: "2px 0 6px 0",
  },
  subheading: {
    marginBottom: 6,
  },
  subheadingRow: {
    display: "flex",
    justifyContent: "space-between",
    fontSize: 11,
  },
  small: {
    fontSize: 10,
  },
  bulletList: {
    margin: "2px 0 0 0",
    paddingLeft: 20,
  },
  bulletItem: {
    fontSize: 10,
    marginBottom: 1,
  },
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

  useEffect(() => {
    loadInitialData();
  }, []);

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
      setMessage(e.message ?? "Failed to load resume page data");
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

      if (!selectedProjectIds.length) {
        setMessage("Select at least one project first.");
        return;
      }

      const created = await createReport({
        title: reportTitle,
        sort_by: "resume_score",
        notes: reportNotes,
        project_ids: selectedProjectIds,
      });

      const report = created.report ?? null;
      setSelectedReport(report);
      setMessage(`Created report "${report?.title ?? "Untitled"}"`);
      await loadInitialData();

      if (report?.id) {
        await loadPreview(report.id);
      }
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
      if (report?.id) {
        await loadPreview(report.id);
      }
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
    if (!selectedReport?.id) {
      setMessage("Select or create a report first.");
      return;
    }

    setLoading(true);
    setMessage("");
    try {
      const exp = await exportResume({
        report_id: selectedReport.id,
        template: "jake",
        output_name: "resume.pdf",
      });

      window.open(`http://localhost:8000${exp.download_url}`, "_blank");
      setMessage("Resume export started.");
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
        {loading ? "Loading..." : "Refresh Resume Page"}
      </button>

      <div style={{ display: "flex", gap: 24, marginTop: 16, alignItems: "flex-start" }}>

        {/* LEFT PANEL — controls */}
        <div style={{ minWidth: 300, maxWidth: 340 }}>

          <div style={{ padding: 12, border: "1px solid #ddd", borderRadius: 8, marginBottom: 16 }}>
            <h4 style={{ marginTop: 0 }}>Create Resume Report</h4>

            <div style={{ marginBottom: 12 }}>
              <label>Title</label><br />
              <input
                type="text"
                value={reportTitle}
                onChange={(e) => setReportTitle(e.target.value)}
                style={{ width: "100%" }}
              />
            </div>

            <div style={{ marginBottom: 12 }}>
              <label>Notes</label><br />
              <textarea
                value={reportNotes}
                onChange={(e) => setReportNotes(e.target.value)}
                rows={3}
                style={{ width: "100%" }}
              />
            </div>

            <h4>Select Projects</h4>
            {projects.length === 0 ? (
              <p>No projects found. Upload a project first.</p>
            ) : (
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
                      {p.name} (#{p.id})
                    </label>
                  </li>
                ))}
              </ul>
            )}

            <button onClick={handleCreateReport} disabled={loading}>
              {loading ? "Working..." : "Create Resume Report"}
            </button>
          </div>

          <div>
            <h4>Saved Reports</h4>
            {reports.length === 0 ? (
              <p>No reports created yet.</p>
            ) : (
              <ul style={{ paddingLeft: 16 }}>
                {reports.map((r) => (
                  <li key={r.id}>
                    <button
                      onClick={() => handleSelectReport(r.id)}
                      disabled={loading}
                      style={{
                        background: "transparent",
                        border: "none",
                        cursor: "pointer",
                        padding: 0,
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

          <div style={{ marginTop: 12 }}>
            <button onClick={handleExportResume} disabled={loading || !selectedReport?.id}>
              Export Resume PDF
            </button>
          </div>

          {message && <p style={{ marginTop: 12, fontSize: 13 }}>{message}</p>}
        </div>

        {/* RIGHT PANEL — live preview */}
        <div style={{ flex: 1, overflowX: "auto" }}>
          {previewLoading && <p>Loading preview...</p>}
          {!previewLoading && !previewCtx && (
            <p style={{ color: "#888" }}>Select or create a report to see the preview.</p>
          )}
          {!previewLoading && previewCtx && (
            <ResumePreview ctx={previewCtx} />
          )}
        </div>

      </div>
    </>
  );
}

export default ResumePage;
