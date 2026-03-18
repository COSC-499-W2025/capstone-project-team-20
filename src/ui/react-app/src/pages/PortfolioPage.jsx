import { useEffect, useState } from "react";
import {
  listProjects,
  createReport,
  listReports,
  getReport,
  exportPortfolio,
  generatePortfolioDetailsForReport,
  getPortfolio,
  setPrivacyConsent,
} from "../api/client";

function PortfolioPage() {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [projects, setProjects] = useState([]);
  const [selectedProjectIds, setSelectedProjectIds] = useState([]);
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [reportTitle, setReportTitle] = useState("My Portfolio Report");
  const [reportNotes, setReportNotes] = useState("");
  const [portfolio, setPortfolio] = useState(null);
  const [openProjects, setOpenProjects] = useState({});

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
      const filteredReports = (reportData.reports ?? []).filter((r) => (r.report_kind ?? "resume") === "portfolio");
      setReports(filteredReports);

      if (selectedReport?.id) {
        const refreshed = filteredReports.find((r) => r.id === selectedReport.id);
        setSelectedReport(refreshed ?? selectedReport);
      }
    } catch (e) {
      setMessage(e.message ?? "Failed to load portfolio page data");
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
        report_kind: "portfolio",
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
    setPortfolio(null);
    setOpenProjects({});
    try {
      const data = await getReport(id);
      setSelectedReport(data.report ?? null);
    } catch (e) {
      setMessage(e.message ?? "Failed to load report");
    } finally {
      setLoading(false);
    }
  }

  async function handleExportPortfolioPdf() {
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

  async function handleGenerateWebPortfolio() {
    if (!selectedReport?.id) {
      setMessage("Select or create a report first.");
      return;
    }

    setLoading(true);
    setMessage("");
    setPortfolio(null);
    setOpenProjects({});

    try {
      await setPrivacyConsent(true);

      const names = projects
        .filter((p) => selectedProjectIds.includes(p.id))
        .map((p) => p.name)
        .filter(Boolean);

      if (!names.length) {
        setMessage("Select at least one project first.");
        return;
      }

      await generatePortfolioDetailsForReport({
        report_id: selectedReport.id,
        project_names: names,
      });

      const response = await getPortfolio(selectedReport.id);
      const nextPortfolio = response?.portfolio ?? null;
      setPortfolio(nextPortfolio);

      const initialOpen = {};
      (nextPortfolio?.projects ?? []).forEach((p, idx) => {
        initialOpen[`${p?.project_name ?? "project"}-${idx}`] = idx === 0;
      });
      setOpenProjects(initialOpen);

      setMessage("Web portfolio generated.");
    } catch (e) {
      setMessage(e.message ?? "Failed to generate web portfolio");
    } finally {
      setLoading(false);
    }
  }

  function togglePortfolioProject(key) {
    setOpenProjects((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  const portfolioProjects = portfolio?.projects ?? [];
  const resumeBulletCount = portfolioProjects.reduce((acc, p) => acc + (p?.bullets?.length ?? 0), 0);
  const teamProjectCount = portfolioProjects.filter((p) => {
    const contributors = p?.portfolio_details?.contributor_roles ?? [];
    return contributors.length > 1 || p?.collaboration_status === "collaborative";
  }).length;

  return (
    <>
      <h3>Portfolio</h3>

      <button onClick={loadInitialData} disabled={loading}>
        {loading ? "Loading..." : "Refresh Portfolio Page"}
      </button>

      <div style={{ marginTop: 16, padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
        <h4>Create Portfolio Report</h4>

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
          {loading ? "Working..." : "Create Portfolio Report"}
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
        <button onClick={handleExportPortfolioPdf} disabled={loading || !selectedReport?.id}>
          Export Portfolio PDF
        </button>
        <button
          onClick={handleGenerateWebPortfolio}
          disabled={loading || !selectedReport?.id}
          style={{ marginLeft: 8 }}
        >
          {loading ? "Working..." : "Generate Web Portfolio"}
        </button>
      </div>

      {portfolio ? (
        <section className="portfolio-panel">
          <div className="portfolio-summary-strip">
            <div className="summary-pill">
              <span className="summary-label">Projects</span>
              <strong>{portfolioProjects.length}</strong>
            </div>
            <div className="summary-pill">
              <span className="summary-label">Resume bullets</span>
              <strong>{resumeBulletCount}</strong>
            </div>
            <div className="summary-pill">
              <span className="summary-label">Team projects</span>
              <strong>{teamProjectCount}</strong>
            </div>
          </div>

          <h4>{portfolio.title || "Portfolio"}</h4>

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {portfolioProjects.map((project, idx) => {
              const details = project?.portfolio_details ?? {};
              const key = `${project?.project_name ?? "project"}-${idx}`;
              const isOpen = !!openProjects[key];
              const bullets = (project?.bullets ?? []).slice(0, 3);
              const contributorRoles = details?.contributor_roles ?? [];
              const summaryText =
                project?.summary?.trim() || details?.overview || "No project summary available.";

              return (
                <article className="portfolio-card" key={key}>
                  <button
                    onClick={() => togglePortfolioProject(key)}
                    style={{
                      width: "100%",
                      display: "flex",
                      justifyContent: "space-between",
                      background: "transparent",
                      border: "none",
                      color: "inherit",
                      cursor: "pointer",
                      padding: 0,
                    }}
                  >
                    <span><strong>{project?.project_name ?? "Untitled Project"}</strong></span>
                    <span>{isOpen ? "▾ Collapse" : "▸ Expand"}</span>
                  </button>

                  {isOpen ? (
                    <div style={{ marginTop: 10 }}>
                      <p className="portfolio-meta">
                        <strong>{details?.role || "Contributor"}</strong> •{" "}
                        {details?.timeline || "Timeline unavailable"}
                      </p>
                      <p className="portfolio-overview">{summaryText}</p>

                      {bullets.length ? (
                        <>
                          <strong>Key contributions</strong>
                          <ul>{bullets.map((b, i) => <li key={`b-${i}`}>{b}</li>)}</ul>
                        </>
                      ) : null}

                      {contributorRoles.length ? (
                        <>
                          <strong>Contributors</strong>
                          <ul className="contrib-list">
                            {contributorRoles.map((c, i) => (
                              <li key={`cr-${i}`}>
                                <span>{c.name}</span>
                                <span className="confidence-chip">{c.role}</span>
                              </li>
                            ))}
                          </ul>
                        </>
                      ) : null}
                    </div>
                  ) : null}
                </article>
              );
            })}
          </div>
        </section>
      ) : null}

      {message && <p style={{ marginTop: 12 }}>{message}</p>}
    </>
  );
}

export default PortfolioPage;