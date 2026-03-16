import { useEffect, useState } from "react";
import {
  listProjects,
  createReport,
  listReports,
  getReport,
  exportResume,
  setPrivacyConsent,
} from "../api/client";

function ResumePage() {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [projects, setProjects] = useState([]);
  const [selectedProjectIds, setSelectedProjectIds] = useState([]);
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [reportTitle, setReportTitle] = useState("My Resume Report");
  const [reportNotes, setReportNotes] = useState("");

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
      prev.includes(id) ? prev.filter((projectId) => projectId !== id) : [...prev, id]
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

      setSelectedReport(created.report ?? null);
      setMessage(`Created report "${created.report?.title ?? "Untitled"}"`);
      await loadInitialData();
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
      setSelectedReport(data.report ?? null);
    } catch (e) {
      setMessage(e.message ?? "Failed to load report");
    } finally {
      setLoading(false);
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

      <div style={{ marginTop: 16, padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
        <h4>Create Resume Report</h4>

        <div style={{ marginBottom: 12 }}>
          <label>Title</label><br />
          <input
            type="text"
            value={reportTitle}
            onChange={(e) => setReportTitle(e.target.value)}
            style={{ width: "100%", maxWidth: 400 }}
          />
        </div>

        <div style={{ marginBottom: 12 }}>
          <label>Notes</label><br />
          <textarea
            value={reportNotes}
            onChange={(e) => setReportNotes(e.target.value)}
            rows={4}
            style={{ width: "100%", maxWidth: 400 }}
          />
        </div>

        <h4>Select Projects</h4>
        {projects.length === 0 ? (
          <p>No projects found. Upload a project first.</p>
        ) : (
          <ul style={{ listStyle: "none", paddingLeft: 0 }}>
            {projects.map((p) => (
              <li key={p.id} style={{ marginBottom: 8 }}>
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

      <div style={{ display: "flex", gap: 16, marginTop: 16 }}>
        <div style={{ minWidth: 300 }}>
          <h4>Saved Reports</h4>
          {reports.length === 0 ? (
            <p>No reports created yet.</p>
          ) : (
            <ul>
              {reports.map((r) => (
                <li key={r.id}>
                  <button
                    onClick={() => handleSelectReport(r.id)}
                    disabled={loading}
                    style={{ background: "transparent", border: "none", cursor: "pointer", padding: 0, color: "var(--text)" }}
                  >
                    {r.title ?? `Report #${r.id}`}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div style={{ flex: 1 }}>
          <h4>Selected Report</h4>
          {selectedReport ? (
            <pre>{JSON.stringify(selectedReport, null, 2)}</pre>
          ) : (
            <p>Select a report to view details.</p>
          )}
        </div>
      </div>

      <div style={{ marginTop: 12 }}>
        <button onClick={handleExportResume} disabled={loading || !selectedReport?.id}>
          Export Resume PDF
        </button>
      </div>

      {message && <p style={{ marginTop: 12 }}>{message}</p>}
    </>
  );
}

export default ResumePage;