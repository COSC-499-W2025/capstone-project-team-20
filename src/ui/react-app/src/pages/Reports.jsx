import { useEffect, useState } from "react";
import {
  listProjects,
  createReport,
  listReports,
  getReport,
  exportResume,
  exportPortfolio,
  generatePortfolioDetailsForReport,
  setPrivacyConsent,
} from "../api/client";

function Reports() {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const [projects, setProjects] = useState([]);
  const [selectedProjectIds, setSelectedProjectIds] = useState([]);

  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);

  const [reportTitle, setReportTitle] = useState("My Report");
  const [reportNotes, setReportNotes] = useState("");

  useEffect(() => {
    loadInitialData();
  }, []);

  async function loadInitialData() {
    setLoading(true);
    setMessage("");

    try {
      const [projectData, reportData] = await Promise.all([
        listProjects(),
        listReports(),
      ]);

      const allProjects = projectData.projects ?? [];
      const allReports = reportData.reports ?? [];

      setProjects(allProjects);
      setSelectedProjectIds(allProjects.map((p) => p.id));
      setReports(allReports);
    } catch (e) {
      setMessage(e.message ?? "Failed to load reports page data");
    } finally {
      setLoading(false);
    }
  }

  function toggleProject(id) {
    setSelectedProjectIds((prev) =>
      prev.includes(id)
        ? prev.filter((projectId) => projectId !== id)
        : [...prev, id]
    );
  }

  async function handleCreateReport() {
    setLoading(true);
    setMessage("");

    try {
      await setPrivacyConsent(true);

      if (selectedProjectIds.length === 0) {
        setMessage("Select at least one project first.");
        return;
      }

      const created = await createReport({
        title: reportTitle,
        sort_by: "resume_score",
        notes: reportNotes,
        project_ids: selectedProjectIds,
      });

      const newReport = created.report;
      setSelectedReport(newReport);
      setMessage(`Created report "${newReport.title}"`);

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

  async function handleGeneratePortfolioDetails() {
    if (!selectedReport?.id) {
      setMessage("Select or create a report first.");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const reportProjects = selectedReport.projects ?? [];
      const projectNames = reportProjects.map((p) => p.project_name).filter(Boolean);

      await generatePortfolioDetailsForReport({
        report_id: selectedReport.id,
        project_names: projectNames,
      });

      const refreshed = await getReport(selectedReport.id);
      setSelectedReport(refreshed.report ?? null);

      setMessage("Portfolio details generated.");
    } catch (e) {
      setMessage(e.message ?? "Failed to generate portfolio details");
    } finally {
      setLoading(false);
    }
  }

  async function handleExportPortfolio() {
    if (!selectedReport?.id) {
      setMessage("Select or create a report first.");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const exp = await exportPortfolio({
        report_id: selectedReport.id,
        output_name: "portfolio.pdf",
      });

      window.open(`http://localhost:8000${exp.download_url}`, "_blank");
      setMessage("Portfolio export started.");
    } catch (e) {
      setMessage(e.message ?? "Failed to export portfolio");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <h3>Reports</h3>

      <button onClick={loadInitialData} disabled={loading}>
        {loading ? "Loading..." : "Refresh Reports Page"}
      </button>

      <div style={{ marginTop: 16, padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
        <h4>Create Report</h4>

        <div style={{ marginBottom: 12 }}>
          <label>Title</label>
          <br />
          <input
            type="text"
            value={reportTitle}
            onChange={(e) => setReportTitle(e.target.value)}
            style={{ width: "100%", maxWidth: 400 }}
          />
        </div>

        <div style={{ marginBottom: 12 }}>
          <label>Notes</label>
          <br />
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
          {loading ? "Working..." : "Create Report"}
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
                    style={{ background: "transparent", border: "none", cursor: "pointer", padding: 0 }}
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
            <>
              <pre>{JSON.stringify(selectedReport, null, 2)}</pre>

              <div style={{ marginTop: 12 }}>
                <button onClick={handleExportResume} disabled={loading}>
                  Export Resume PDF
                </button>

                <button
                  onClick={handleGeneratePortfolioDetails}
                  disabled={loading}
                  style={{ marginLeft: 8 }}
                >
                  Generate Portfolio Details
                </button>

                <button
                  onClick={handleExportPortfolio}
                  disabled={loading}
                  style={{ marginLeft: 8 }}
                >
                  Export Portfolio PDF
                </button>
              </div>
            </>
          ) : (
            <p>Select a report to view details.</p>
          )}
        </div>
      </div>

      {message && <p style={{ marginTop: 12 }}>{message}</p>}
    </>
  );
}

export default Reports;