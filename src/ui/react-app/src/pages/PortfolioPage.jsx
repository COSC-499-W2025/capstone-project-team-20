import { useEffect, useState } from "react";
import { formLabel, formInput } from "../formStyles";
import {
  listProjects,
  createReport,
  listReports,
  getReport,
  deleteReport,
  exportPortfolio,
  generatePortfolioDetailsForReport,
  getPortfolio,
  setPrivacyConsent,
  publishPortfolio,
  unpublishPortfolio,
  updatePortfolioProject,
  getBadgeProgress,
} from "../api/client";

const OP_STATE = {
  IDLE: "idle",
  LOADING: "loading",
  GENERATING: "generating",
  EXPORTING: "exporting",
  SAVING: "saving",
  TOGGLING_MODE: "toggling_mode",
};

// ---------------------------------------------------------------------------
// Trash icon button — mirrors ResumePage
// ---------------------------------------------------------------------------
function Trash({ onClick }) {
  return (
    <button onClick={onClick} style={trashBtn} title="Delete report">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="3 6 5 6 21 6"/>
        <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
        <path d="M10 11v6M14 11v6"/>
        <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
      </svg>
    </button>
  );
}

const trashBtn = {
  background: "none",
  border: "none",
  cursor: "pointer",
  padding: "0 3px",
  opacity: 0.45,
  lineHeight: 1,
  color: "currentColor",
  verticalAlign: "middle",
};

// ---------------------------------------------------------------------------
// Confirm modal — same visual language as ResumePage
// ---------------------------------------------------------------------------
function ConfirmModal({ title, message, confirmLabel = "Delete", onConfirm, onCancel }) {
  return (
    <>
      <style>{MODAL_CSS}</style>
      <div className="pf-overlay">
        <div className="pf-modal">
          <div className="pf-bar" aria-hidden="true" />
          <div className="pf-confirm-body">
            <div className="pf-confirm-icon">⚠️</div>
            <h2 className="pf-confirm-title">{title}</h2>
            <p className="pf-confirm-sub">{message}</p>
          </div>
          <div className="pf-modal-footer">
            <button className="pf-btn pf-btn--ghost" onClick={onCancel}>← Go back</button>
            <button className="pf-btn pf-btn--danger" onClick={onConfirm}>{confirmLabel}</button>
          </div>
        </div>
      </div>
    </>
  );
}


// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function formatBadgeLabel(badgeId = "") {
  return badgeId.split("_").map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1)).join(" ");
}

function badgeEarnedForProject(badge, projectName) {
  const tracked = badge?.project?.name;
  if (!tracked || !projectName) return false;
  return `${tracked}`.trim().toLowerCase() === `${projectName}`.trim().toLowerCase() && !!badge.earned;
}

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function PortfolioPage() {
  const [loading, setLoading] = useState(false);
  const [opState, setOpState] = useState(OP_STATE.IDLE);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("info");
  const [projects, setProjects] = useState([]);
  const [selectedProjectIds, setSelectedProjectIds] = useState([]);
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [reportTitle, setReportTitle] = useState("My Portfolio Report");
  const [reportNotes, setReportNotes] = useState("");
  const [portfolio, setPortfolio] = useState(null);
  const [openProjects, setOpenProjects] = useState({});
  const [projectDrafts, setProjectDrafts] = useState({});
  const [searchText, setSearchText] = useState("");
  const [languageFilter, setLanguageFilter] = useState("all");
  const [collabFilter, setCollabFilter] = useState("all");
  const [badgeProgress, setBadgeProgress] = useState([]);
  const [copyToastVisible, setCopyToastVisible] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);

  useEffect(() => { loadInitialData(); }, []);

  function setStatus(nextMessage, nextType = "info") {
    setMessage(nextMessage);
    setMessageType(nextType);
  }

  function showCopyToast() {
    setCopyToastVisible(true);
    window.clearTimeout(window.__portfolioCopyToastTimer);
    window.__portfolioCopyToastTimer = window.setTimeout(() => setCopyToastVisible(false), 2200);
  }

  async function loadInitialData() {
    setLoading(true);
    setOpState(OP_STATE.LOADING);
    setStatus("");
    try {
      const [projectData, reportData, badgeData] = await Promise.all([listProjects(), listReports(), getBadgeProgress()]);
      const allProjects = projectData.projects ?? [];
      setProjects(allProjects);
      setBadgeProgress(badgeData?.badges ?? []);
      setSelectedProjectIds(allProjects.map((p) => p.id));

      const filteredReports = (reportData.reports ?? []).filter((r) => (r.report_kind ?? "resume") === "portfolio");
      setReports(filteredReports);

      if (selectedReport?.id) {
        const refreshed = filteredReports.find((r) => r.id === selectedReport.id);
        setSelectedReport(refreshed ?? selectedReport);
      }
    } catch (e) {
      setStatus(e.message ?? "Failed to load portfolio page data", "error");
    } finally {
      setLoading(false);
      setOpState(OP_STATE.IDLE);
    }
  }

  function toggleProject(id) {
    setSelectedProjectIds((prev) => prev.includes(id) ? prev.filter((projectId) => projectId !== id) : [...prev, id]);
  }

  function togglePortfolioProject(key) {
    setOpenProjects((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  function buildDraftFromProject(project) {
    const custom = project?.portfolio_customizations ?? {};
    const details = project?.portfolio_details ?? {};
    return {
      custom_title: (custom.custom_title ?? "").trim(),
      custom_overview: (custom.custom_overview ?? details.overview ?? project?.summary ?? "").trim(),
      custom_achievements: Array.isArray(custom.custom_achievements)
        ? custom.custom_achievements.join("\n")
        : Array.isArray(details.achievements)
        ? details.achievements.join("\n")
        : (project?.bullets ?? []).join("\n"),
      is_hidden: !!custom.is_hidden,
    };
  }

  function hydrateDrafts(nextPortfolio) {
    const drafts = {};
    (nextPortfolio?.projects ?? []).forEach((p) => { drafts[p.project_name] = buildDraftFromProject(p); });
    setProjectDrafts(drafts);
  }

  function handleDraftChange(projectName, field, value) {
    setProjectDrafts((prev) => ({ ...prev, [projectName]: { ...(prev[projectName] ?? {}), [field]: value } }));
  }

  function getDraft(projectName) {
    return projectDrafts[projectName] ?? {
      custom_title: "",
      custom_overview: "",
      custom_achievements: "",
      is_hidden: false,
    };
  }

  function getRenderedTitle(project) {
    const draft = getDraft(project.project_name);
    const v = (draft.custom_title ?? "").trim();
    return v || project?.project_name || "Untitled Project";
  }

  function getRenderedOverview(project) {
    const draft = getDraft(project.project_name);
    const draftVal = (draft.custom_overview ?? "").trim();
    if (draftVal) return draftVal;
    const customVal = (project?.portfolio_customizations?.custom_overview ?? "").trim();
    if (customVal) return customVal;
    const detailsVal = (project?.portfolio_details?.overview ?? "").trim();
    if (detailsVal) return detailsVal;
    return (project?.summary ?? "No project summary available.").trim();
  }

  function getRenderedAchievements(project) {
    const draft = getDraft(project.project_name);
    const fromDraft = (draft.custom_achievements ?? "").split("\n").map((x) => x.trim()).filter(Boolean);
    if (fromDraft.length) return fromDraft;
    const custom = project?.portfolio_customizations?.custom_achievements;
    const fromCustom = Array.isArray(custom) ? custom.map((x) => `${x}`.trim()).filter(Boolean) : [];
    if (fromCustom.length) return fromCustom;
    const fromDetails = Array.isArray(project?.portfolio_details?.achievements) ? project.portfolio_details.achievements : [];
    if (fromDetails.length) return fromDetails;
    return (project?.bullets ?? []).filter(Boolean);
  }

  function buildPortfolioHtml(projectList) {
    const title = escapeHtml(portfolio?.title || "Portfolio");
    const cards = projectList.map((project) => {
      const details = project?.portfolio_details ?? {};
      const renderedTitle = escapeHtml(getRenderedTitle(project));
      const renderedOverview = escapeHtml(getRenderedOverview(project));
      const renderedAchievements = getRenderedAchievements(project).map((x) => `<li>${escapeHtml(x)}</li>`).join("");
      const contributorRoles = details?.contributor_roles ?? [];
      const contributorsHtml = contributorRoles.length
        ? `<h4>Contributors</h4><ul>${contributorRoles.map((c) => `<li>${escapeHtml(c.name)}${c.role ? ` — ${escapeHtml(c.role)}` : ""}</li>`).join("")}</ul>`
        : "";
      const roleLine = `${escapeHtml(details?.role || "Contributor")} • ${escapeHtml(details?.timeline || "Timeline unavailable")}`;

      return `
<section class="portfolio-card">
  <h3>${renderedTitle}</h3>
  <p class="meta">${roleLine}</p>
  <p>${renderedOverview}</p>
  ${renderedAchievements ? `<h4>Key contributions</h4><ul>${renderedAchievements}</ul>` : ""}
  ${contributorsHtml}
</section>`.trim();
    }).join("\n");

    return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>${title}</title>
<style>
  body{font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:920px;margin:32px auto;padding:0 16px;line-height:1.55;color:#111;}
  h1{font-size:2rem;margin:0 0 20px;}
  .portfolio-card{border:1px solid #ddd;border-radius:10px;padding:16px 18px;margin-bottom:14px;background:#fff;}
  .meta{color:#555;font-size:.95rem;margin-top:-4px;}
  h3{margin:0 0 8px;}
  h4{margin:12px 0 6px;font-size:1rem;}
  ul{margin:6px 0 0 20px;}
</style>
</head>
<body>
  <h1>${title}</h1>
  ${cards}
</body>
</html>`;
  }

  async function handleCopyPortfolioHtml() {
    if (!portfolio) {
      setStatus("Generate a portfolio first.", "error");
      return;
    }
    try {
      const html = buildPortfolioHtml(visiblePortfolioProjects);
      await navigator.clipboard.writeText(html);
      showCopyToast();
      setStatus("Portfolio HTML copied to clipboard.", "success");
    } catch (e) {
      setStatus("Clipboard copy failed. Your browser may block clipboard access.", "error");
    }
  }

  async function handleCreateReport() {
    setLoading(true);
    setOpState(OP_STATE.LOADING);
    setStatus("");
    try {
      await setPrivacyConsent(true);
      if (!selectedProjectIds.length) {
        setStatus("Select at least one project first.", "error");
        return;
      }
      const created = await createReport({
        title: reportTitle,
        sort_by: "resume_score",
        notes: reportNotes,
        report_kind: "portfolio",
        project_ids: selectedProjectIds,
      });
      const createdReport = created.report ?? null;
      setSelectedReport(createdReport);
      setStatus(`Created report "${createdReport?.title ?? "Untitled"}"`, "success");
      await loadInitialData();
      if (createdReport?.id) {
        await handleSelectReport(createdReport.id);
        const response = await getPortfolio(createdReport.id);
        const currentMode = (response?.portfolio?.portfolio_mode ?? "").toLowerCase();
        if (currentMode !== "public") {
          await publishPortfolio(createdReport.id);
        }
      }
    } catch (e) {
      setStatus(e.message ?? "Failed to create report", "error");
    } finally {
      setLoading(false);
      setOpState(OP_STATE.IDLE);
    }
  }

  async function handleSelectReport(id) {
    setLoading(true);
    setOpState(OP_STATE.LOADING);
    setStatus("");
    setPortfolio(null);
    setOpenProjects({});
    setProjectDrafts({});
    try {
      const data = await getReport(id);
      setSelectedReport(data.report ?? null);
      setStatus("Report selected. Generate web portfolio to view sections.", "info");
    } catch (e) {
      setStatus(e.message ?? "Failed to load report", "error");
    } finally {
      setLoading(false);
      setOpState(OP_STATE.IDLE);
    }
  }

  async function triggerDownload(url, fileName) {
    const res = await fetch(url);
    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(objectUrl);
  }

  async function handleExportPortfolioPdf() {
    if (!selectedReport?.id) { setStatus("Select or create a report first.", "error"); return; }
    setLoading(true);
    setMessage("");
    try{
      const exp=await exportPortfolio({report_id:selectedReport.id,output_name:"portfolio.pdf"});
      const fileName=`${selectedReport.title??`report-${selectedReport.id}`}.pdf`;
      const res=await fetch(`http://localhost:8000${exp.download_url}`);
      const blob=await res.blob();
      const objectUrl=URL.createObjectURL(blob);
      const a=document.createElement("a");
      a.href=objectUrl;
      a.download=fileName;
      a.click();
      URL.revokeObjectURL(objectUrl);
      setMessage("Portfolio export started.");
    }catch(e){
      setMessage(e.message??"Failed to export portfolio");
    }finally{
      setLoading(false);
      setOpState(OP_STATE.IDLE);
    }
  }

  async function handleGenerateWebPortfolio() {
    if (!selectedReport?.id) { setStatus("Select or create a report first.", "error"); return; }
    setLoading(true);
    setOpState(OP_STATE.GENERATING);
    setStatus("Generating web portfolio sections...", "info");
    setPortfolio(null);
    setOpenProjects({});
    setProjectDrafts({});
    try {
      await setPrivacyConsent(true);
      const names = projects.filter((p) => selectedProjectIds.includes(p.id)).map((p) => p.name).filter(Boolean);
      if (!names.length) { setStatus("Select at least one project first.", "error"); return; }
      await generatePortfolioDetailsForReport({ report_id: selectedReport.id, project_names: names });
      const response = await getPortfolio(selectedReport.id);
      const nextPortfolio = response?.portfolio ?? null;
      setPortfolio(nextPortfolio);
      hydrateDrafts(nextPortfolio);
      const initialOpen = {};
      (nextPortfolio?.projects ?? []).forEach((p, idx) => { initialOpen[`${p?.project_name ?? "project"}-${idx}`] = idx === 0; });
      setOpenProjects(initialOpen);
      setStatus("Web portfolio generated successfully.", "success");
    } catch (e) {
      setStatus(e.message ?? "Failed to generate web portfolio", "error");
    } finally {
      setLoading(false);
      setOpState(OP_STATE.IDLE);
    }
  }

  async function handleSaveProjectCustomization(projectName) {
    if (!selectedReport?.id) { setStatus("Select a report first.", "error"); return; }
    const draft = getDraft(projectName);
    const payload = {
      custom_title: (draft.custom_title ?? "").trim(),
      custom_overview: (draft.custom_overview ?? "").trim(),
      custom_achievements: (draft.custom_achievements ?? "").split("\n").map((x) => x.trim()).filter(Boolean),
      is_hidden: !!draft.is_hidden,
    };
    setLoading(true);
    setOpState(OP_STATE.SAVING);
    setStatus("Saving project customizations...", "info");
    try {
      const res = await updatePortfolioProject(selectedReport.id, projectName, payload);
      const nextPortfolio = res?.portfolio ?? null;
      setPortfolio(nextPortfolio);
      hydrateDrafts(nextPortfolio);
      setStatus(`Saved customization for ${projectName}.`, "success");
    } catch (e) {
      setStatus(e.message ?? "Failed to save project customization", "error");
    } finally {
      setLoading(false);
      setOpState(OP_STATE.IDLE);
    }
  }

  async function handleToggleMode() {
    if (!selectedReport?.id) { setStatus("Select a report first.", "error"); return; }
    const current = (portfolio?.portfolio_mode ?? "public").toLowerCase();
    const goPrivate = current !== "private";
    setLoading(true);
    setOpState(OP_STATE.TOGGLING_MODE);
    setStatus("Updating portfolio mode...", "info");
    try {
      const res = goPrivate ? await unpublishPortfolio(selectedReport.id) : await publishPortfolio(selectedReport.id);
      setPortfolio(res?.portfolio ?? portfolio);
      setStatus(goPrivate ? "Private mode enabled." : "Public mode enabled.", "success");
    } catch (e) {
      setStatus(e.message ?? "Failed to change mode", "error");
    } finally {
      setLoading(false);
      setOpState(OP_STATE.IDLE);
    }
  }

  async function handleDeleteReport(id) {
    try {
      await deleteReport(id);
    } catch (e) {
      if (e.message && e.message !== "") {
        setStatus(e.message, "error");
        return;
      }
    }
    setConfirmDeleteId(null);
    setReports((prev) => prev.filter((r) => r.id !== id));
    if (selectedReport?.id === id) {
      setSelectedReport(null);
      setPortfolio(null);
    }
  }

  const portfolioProjects = portfolio?.projects ?? [];
  const portfolioMode = (portfolio?.portfolio_mode ?? "public").toLowerCase();
  const isPrivateMode = portfolioMode === "private";
  const isPublicMode = !isPrivateMode;

  const resumeBulletCount = portfolioProjects.reduce((acc, p) => acc + (p?.bullets?.length ?? 0), 0);
  const teamProjectCount = portfolioProjects.filter((p) => {
    const contributors = p?.portfolio_details?.contributor_roles ?? [];
    return contributors.length > 1 || p?.collaboration_status === "collaborative";
  }).length;

  const availableLanguages = Array.from(new Set(portfolioProjects.flatMap((p) => p?.languages ?? []))).sort((a, b) => a.localeCompare(b));

  const visiblePortfolioProjects = portfolioProjects
    .filter((p) => {
      const d = getDraft(p.project_name);
      if (isPublicMode && d.is_hidden) return false;
      return true;
    })
    .filter((p) => {
      if (!isPublicMode) return true;
      const name = getRenderedTitle(p).toLowerCase();
      const matchesSearch = !searchText.trim() || name.includes(searchText.trim().toLowerCase());
      const matchesLanguage = languageFilter === "all" || (p?.languages ?? []).includes(languageFilter);
      const matchesCollab = collabFilter === "all" || (p?.collaboration_status ?? "individual") === collabFilter;
      return matchesSearch && matchesLanguage && matchesCollab;
    });

  const earnedBadgesByProject = (projectName) => (badgeProgress ?? []).filter((b) => badgeEarnedForProject(b, projectName));

  return (
    <>
      <h3>Portfolio</h3>


      <div className={`portfolio-status portfolio-status--${messageType}`} aria-live="polite" data-testid="portfolio-status-banner">
        {message || "Select or create a report to preview your portfolio."}
      </div>

      <div style={{ display: "flex", gap: 24, marginTop: 16, alignItems: "flex-start" }}>

        {/* LEFT — controls */}
        <div style={{ minWidth: 280, maxWidth: 320 }}>
          <div style={{ padding: 12, border: "1px solid #ddd", borderRadius: 8, marginBottom: 16 }}>
            <h4 style={{ marginTop: 0 }}>Create Portfolio Report</h4>
            <div style={{ marginBottom: 10 }}>
              <label style={formLabel}>Title</label>
              <input type="text" value={reportTitle} onChange={(e) => setReportTitle(e.target.value)} style={formInput} />
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
            {projects.length === 0 ? <p>No projects found. Upload a project first.</p> : (
              <ul style={{ listStyle: "none", paddingLeft: 0 }}>
                {projects.map((p) => (
                  <li key={p.id} style={{ marginBottom: 6 }}>
                    <label>
                      <input type="checkbox" checked={selectedProjectIds.includes(p.id)} onChange={() => toggleProject(p.id)} style={{ marginRight: 8 }} />
                      {p.name}
                    </label>
                  </li>
                ))}
              </ul>
            )}
            <button onClick={handleCreateReport} disabled={loading}>{loading ? "Working..." : "Create Portfolio Report"}</button>
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
              <p style={{ fontSize: 12, color: "#e6edf3", marginTop: 6, borderLeft: "2px solid #ddd", paddingLeft: 8 }}>
                {selectedReport.notes}
              </p>
            )}
          </div>

          <div style={{ marginTop: 16 }}>
            <button onClick={handleExportPortfolioPdf} disabled={loading || !selectedReport?.id}>
              {opState === OP_STATE.EXPORTING ? "Exporting PDF..." : "Export Portfolio PDF"}
            </button>
          </div>
        </div>

        {/* RIGHT — portfolio content */}
        <div style={{ flex: 1 }}>

          <div style={{ marginBottom: 12 }}>
            <button onClick={handleGenerateWebPortfolio} disabled={loading || !selectedReport?.id}>
              {opState === OP_STATE.GENERATING ? "Generating..." : "Generate Web Portfolio"}
            </button>
            <button onClick={handleCopyPortfolioHtml} disabled={loading || !portfolio} style={{ marginLeft: 8 }}>
              Copy Portfolio HTML
            </button>
          </div>

          {portfolio && (
            <section className="pf-panel">
              {/* Stats */}
              <div className="pf-stats">
                <div className="pf-stat">
                  <span className="pf-stat__num">{portfolioProjects.length}</span>
                  <span className="pf-stat__label">Projects</span>
                </div>
                <div className="pf-stat">
                  <span className="pf-stat__num">{resumeBulletCount}</span>
                  <span className="pf-stat__label">Bullets</span>
                </div>
                <div className="pf-stat">
                  <span className="pf-stat__num">{teamProjectCount}</span>
                  <span className="pf-stat__label">Team</span>
                </div>
              </div>

              {/* Toolbar */}
              <div className="pf-toolbar">
                <button
                  className={`pf-mode-btn ${isPrivateMode ? "pf-mode-btn--private" : "pf-mode-btn--public"}`}
                  onClick={handleToggleMode}
                  disabled={loading || !selectedReport?.id}
                  aria-label="Toggle portfolio mode"
                  data-testid="portfolio-mode-badge"
                >
                  {isPrivateMode ? "🔒 Private" : "🔓 Public"}
                </button>
                {isPublicMode && (
                  <>
                    <input
                      className="pf-search"
                      aria-label="Search projects"
                      placeholder="Search projects…"
                      value={searchText}
                      onChange={(e) => setSearchText(e.target.value)}
                    />
                    <select className="pf-select" aria-label="Filter by language" value={languageFilter} onChange={(e) => setLanguageFilter(e.target.value)}>
                      <option value="all">All languages</option>
                      {availableLanguages.map((lang) => <option key={lang} value={lang}>{lang}</option>)}
                    </select>
                    <select className="pf-select" aria-label="Filter by collaboration" value={collabFilter} onChange={(e) => setCollabFilter(e.target.value)}>
                      <option value="all">All types</option>
                      <option value="individual">Individual</option>
                      <option value="collaborative">Collaborative</option>
                    </select>
                  </>
                )}
              </div>

              {/* Project cards */}
              <div className="pf-cards">
                {visiblePortfolioProjects.map((project, idx) => {
                  const details = project?.portfolio_details ?? {};
                  const key = `${project?.project_name ?? "project"}-${idx}`;
                  const isOpen = !!openProjects[key];
                  const contributorRoles = details?.contributor_roles ?? [];
                  const renderedTitle = getRenderedTitle(project);
                  const renderedOverview = getRenderedOverview(project);
                  const renderedAchievements = getRenderedAchievements(project);
                  const draft = getDraft(project.project_name);
                  const projectBadges = earnedBadgesByProject(project.project_name);

                  return (
                    <div className={`pf-card${isOpen ? " pf-card--open" : ""}`} key={key}>
                      {/* Header — div not button so inputs are valid inside */}
                      <div
                        className="pf-card__header"
                        onClick={() => togglePortfolioProject(key)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") togglePortfolioProject(key); }}
                      >
                        <div className="pf-card__title-row">
                          {isPrivateMode ? (
                            <input
                              className="pf-card__title-input"
                              aria-label={`Custom title ${project?.project_name ?? ""}`}
                              type="text"
                              value={draft.custom_title}
                              onClick={(e) => e.stopPropagation()}
                              onChange={(e) => handleDraftChange(project.project_name, "custom_title", e.target.value)}
                              placeholder={project?.project_name ?? "Untitled Project"}
                            />
                          ) : (
                            <span className="pf-card__title">{renderedTitle}</span>
                          )}
                          {projectBadges.map((b) => (
                            <span
                              key={`badge-${b.badge_id}`}
                              className="portfolio-badge-chip portfolio-badge-chip--unlocked"
                              onClick={(e) => e.stopPropagation()}
                            >
                              🏅 {b.label ?? formatBadgeLabel(b.badge_id)}
                            </span>
                          ))}
                        </div>
                        <span className="pf-card__chevron" aria-hidden="true">{isOpen ? "▾" : "▸"}</span>
                      </div>

                      {isOpen && (
                        <div className="pf-card__body">
                          <p className="pf-card__meta">{details?.role || "Contributor"} · {details?.timeline || "Timeline unavailable"}</p>

                          {isPrivateMode ? (
                            <div className="pf-edit">
                              <label className="pf-edit__label">Overview</label>
                              <textarea
                                className="pf-edit__textarea"
                                aria-label={`Custom overview ${project?.project_name ?? ""}`}
                                rows={4}
                                value={draft.custom_overview}
                                onChange={(e) => handleDraftChange(project.project_name, "custom_overview", e.target.value)}
                              />
                              <label className="pf-edit__label">Key contributions (one per line)</label>
                              <textarea
                                className="pf-edit__textarea"
                                aria-label={`Custom achievements ${project?.project_name ?? ""}`}
                                rows={4}
                                value={draft.custom_achievements}
                                onChange={(e) => handleDraftChange(project.project_name, "custom_achievements", e.target.value)}
                              />
                              <div className="pf-edit__footer">
                                <label className="pf-edit__check">
                                  <input
                                    type="checkbox"
                                    checked={!!draft.is_hidden}
                                    onChange={(e) => handleDraftChange(project.project_name, "is_hidden", e.target.checked)}
                                  />
                                  Hide in public mode
                                </label>
                                <button onClick={() => handleSaveProjectCustomization(project.project_name)} disabled={loading}>
                                  {opState === OP_STATE.SAVING ? "Saving…" : "Save Changes"}
                                </button>
                              </div>
                            </div>
                          ) : (
                            <p className="portfolio-overview">{renderedOverview}</p>
                          )}

                          {!isPrivateMode && renderedAchievements.length > 0 && (
                            <div className="pf-card__section">
                              <span className="pf-card__section-label">Key contributions</span>
                              <ul className="pf-card__bullets">
                                {renderedAchievements.map((b, i) => <li key={i}>{b}</li>)}
                              </ul>
                            </div>
                          )}

                          {contributorRoles.length > 0 && (
                            <div className="pf-card__section">
                              <span className="pf-card__section-label">Contributors</span>
                              <ul className="contrib-list">
                                {contributorRoles.map((c, i) => (
                                  <li key={i}>
                                    <span>{c.name}</span>
                                    {c.role && <span className="confidence-chip">{c.role}</span>}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>
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

      {copyToastVisible && (
        <div
          role="status"
          aria-live="polite"
          style={{
            position: "fixed",
            right: 16,
            bottom: 16,
            zIndex: 9999,
            background: "#1f8f43",
            color: "#fff",
            border: "1px solid #157535",
            boxShadow: "0 8px 24px rgba(0,0,0,.24)",
            borderRadius: 10,
            padding: "10px 14px",
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontWeight: 600,
          }}
          data-testid="copy-html-toast"
        >
          <span aria-hidden="true">✅</span>
          <span>Successfully copied!</span>
        </div>
      )}
    </>
  );
}

export default PortfolioPage;

// ---------------------------------------------------------------------------
// Modal CSS — mirrors ResumePage rs-* pattern under pf-* namespace
// ---------------------------------------------------------------------------
const MODAL_CSS = `
.pf-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center;
}
.pf-modal {
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
  animation: pf-fadein .2s ease both;
}
@keyframes pf-fadein {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.pf-bar {
  height: 3px; flex-shrink: 0;
  background: linear-gradient(90deg, var(--accent), var(--accent2), var(--accent));
  background-size: 200% 100%;
  animation: pf-shimmer 3s linear infinite;
}
@keyframes pf-shimmer {
  0%   { background-position: 200% center; }
  100% { background-position: -200% center; }
}
.pf-confirm-body {
  flex: 1;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 36px 32px 24px;
  text-align: center;
}
.pf-confirm-icon { font-size: 32px; margin-bottom: 12px; }
.pf-confirm-title {
  font-size: 18px; font-weight: 700; color: var(--text);
  margin: 0 0 10px;
}
.pf-confirm-sub {
  font-size: 13px; color: var(--muted); line-height: 1.6;
  max-width: 320px; margin: 0;
}
.pf-modal-footer {
  padding: 12px 24px; flex-shrink: 0;
  border-top: 1px solid var(--border);
  display: flex; justify-content: flex-end; align-items: center; gap: 8px;
}
.pf-btn {
  display: inline-flex; align-items: center; justify-content: center;
  height: 36px; padding: 0 16px; border-radius: var(--r);
  font-size: 13px; font-weight: 600; cursor: pointer;
  border: 1.5px solid transparent; font-family: inherit;
  transition: all .15s;
}
.pf-btn--ghost {
  background: transparent; color: var(--muted); border-color: var(--border);
}
.pf-btn--ghost:hover { border-color: var(--muted); color: var(--text); }
.pf-btn--danger {
  background: transparent; color: #f85149; border-color: #f85149;
}
.pf-btn--danger:hover { border-color: #ff7b72; color: #ff7b72; }
`;
