import { useState, useEffect, useRef } from "react";
import Settings from "./Settings";
import ProfileSetup from "./pages/ProfileSetup";
import Reports from "./pages/Reports";
import {
  listProjects,
  getProject,
  listSkills,
  getBadgeProgress,
  getYearlyWrapped,
  getConfig,
  getPrivacyConsent,
  uploadProjectZip,
  uploadProjectFromPath,
  clearProjects
} from "./api/client";
import "./App.css";

const formatBadgeLabel = (badgeId = "") =>
  badgeId
    .split("_")
    .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
    .join(" ");

const formatBadgeRequirement = (metric, target) => {
  const label = (metric || "metric").toLowerCase();
  if (label.includes("ratio") || label.includes("share")) return `Reach at least ${(target * 100).toFixed(0)}% ${label}.`;
  return `Reach at least ${target} ${label}.`;
};


const ALL_BADGE_DETAILS = {
  gigantana: {
    label: "Gigantana",
    description: "A massive project with heavyweight assets and scope.",
    howToEarn: "Reach at least 1024 MB project size.",
  },
  slow_burn: {
    label: "Slow Burn",
    description: "Steady long-term effort across a full year.",
    howToEarn: "Keep project duration at 365+ days.",
  },
  flash_build: {
    label: "Flash Build",
    description: "A fast sprint with meaningful output.",
    howToEarn: "Finish in 7 days or less with at least 20 files.",
  },
  fresh_breeze: {
    label: "Fresh Breeze",
    description: "A compact project delivered quickly.",
    howToEarn: "Finish within 30 days and keep files under 50.",
  },
  marathoner: {
    label: "Marathoner",
    description: "A multi-year commitment to growth.",
    howToEarn: "Keep project duration at 730+ days.",
  },
  tiny_but_mighty: {
    label: "Tiny but Mighty",
    description: "Small footprint, high impact.",
    howToEarn: "Keep size at 5 MB or less while shipping at least 10 files.",
  },
  rapid_builder: {
    label: "Rapid Builder",
    description: "High-volume output in a tight window.",
    howToEarn: "Ship 500+ files within 120 days.",
  },
  jack_of_all_trades: {
    label: "Jack of All Trades",
    description: "Excellent language diversity.",
    howToEarn: "Use at least 5 languages in a project.",
  },
  polyglot: {
    label: "Polyglot",
    description: "Comfortable across multiple languages.",
    howToEarn: "Use at least 3 languages.",
  },
  language_specialist: {
    label: "Language Specialist",
    description: "Deep specialization in one primary language.",
    howToEarn: "Make one language at least 80% of code share.",
  },
  balanced_palette: {
    label: "Balanced Palette",
    description: "Great balance across a mixed stack.",
    howToEarn: "Use 3+ languages with top language at or below 50%.",
  },
  solo_runner: {
    label: "Solo Runner",
    description: "Built independently end-to-end.",
    howToEarn: "Have 1 or fewer contributors.",
  },
  team_effort: {
    label: "Team Effort",
    description: "Strong collaboration across contributors.",
    howToEarn: "Have 3 or more contributors.",
  },
  test_pilot: {
    label: "Test Pilot",
    description: "Testing takes a meaningful share of the repo.",
    howToEarn: "Keep test share at 15% or higher.",
  },
  test_scout: {
    label: "Test Scout",
    description: "Testing is present and consistent.",
    howToEarn: "Keep test share between 5% and 15%.",
  },
  docs_guardian: {
    label: "Docs Guardian",
    description: "Documentation-first mindset.",
    howToEarn: "Keep docs share at 20% or higher.",
  },
  doc_enthusiast: {
    label: "Doc Enthusiast",
    description: "Good documentation coverage.",
    howToEarn: "Keep docs share between 10% and 20%.",
  },
  pixel_perfect: {
    label: "Pixel Perfect",
    description: "Strong visual/design emphasis.",
    howToEarn: "Keep design or game assets at 25% or higher.",
  },
  visual_storyteller: {
    label: "Visual Storyteller",
    description: "Visual assets are a key supporting strength.",
    howToEarn: "Keep design or game assets between 15% and 25%.",
  },
  data_seedling: {
    label: "Data Seedling",
    description: "Early signs of data-heavy work.",
    howToEarn: "Keep data share between 10% and 25%.",
  },
  data_wrangler: {
    label: "Data Wrangler",
    description: "Strong data footprint and tooling.",
    howToEarn: "Keep data share at 25%+ or use data stack skills.",
  },
  code_cruncher: {
    label: "Code Cruncher",
    description: "Code-focused project composition.",
    howToEarn: "Keep code share at 60% or higher.",
  },
  container_captain: {
    label: "Container Captain",
    description: "Deployment-ready with containers.",
    howToEarn: "Use Docker in the project skills.",
  },
  full_stack_explorer: {
    label: "Full Stack Explorer",
    description: "Bridges frontend and backend confidently.",
    howToEarn: "Use backend + frontend languages and React/Next.js.",
  },
};

function App() {
  const [profileReady, setProfileReady] = useState(null);
  const [current, setCurrent] = useState(1);

  useEffect(() => {
    getConfig().then((cfg) => setProfileReady(!!(cfg?.name && cfg?.email && cfg?.phone))).catch(() => setProfileReady(false));
  }, []);

  const buttons = [
    { id: 0, label: "Settings" },
    { id: 1, label: "Projects" },
    { id: 2, label: "Badges" },
    { id: 3, label: "Reports" },
    { id: 4, label: "Help" }
  ];

  const menuRender = () => {
    switch (current) {
      case 0: return <Settings />;
      case 1: return <Projects />;
      case 2: return <Badges />;
      case 3: return <Reports />;
      case 4: return <Help />;
      default: return <Projects />;
    }
  };

  if (profileReady === null) return <div className="ps-loading">Loading…</div>;
  if (!profileReady) return <ProfileSetup onComplete={() => setProfileReady(true)} />;

  return (
    <div className="screen">
      <div className="stacked-buttons">
        {buttons.map((button) => (
          <button key={button.id} className={button.id === current ? "button-on" : "button-off"} onClick={() => setCurrent(button.id)}>
            {button.label}
          </button>
        ))}
      </div>
      <div className="menu">{menuRender()}</div>
    </div>
  );
}

function Projects() {
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  const fileInputRef = useRef(null);
  const [projects, setProjects] = useState([]);
  const [currentProjects, setCurrentProjects] = useState([]);
  const [previousProjects, setPreviousProjects] = useState([]);
  const [selected, setSelected] = useState(null);
  const [zipFile, setZipFile] = useState(null);
  const [pathInput, setPathInput] = useState("");

  async function loadProjects() {
    setLoading(true);
    setError(null);
    try {
      const data = await listProjects();
      const allProjects = data.projects ?? [];
      const current = data.current_projects ?? allProjects;
      const previous = data.previous_projects ?? [];
      setProjects(allProjects);
      setCurrentProjects(current);
      setPreviousProjects(previous);
    } catch (e) {
      setError(e.message ?? "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }

  async function handleSelect(id) {
    setLoading(true);
    setError(null);
    try {
      const data = await getProject(id);
      setSelected(data.project ?? null);
    } catch (e) {
      setError(e.message ?? "Failed to load project");
    } finally {
      setLoading(false);
    }
  }

  async function handleUploadPath() {
<<<<<<< feature/portfolio-web-page
    if (!pathInput.trim()) {
      setError("Enter a path first (example: testResources/sample.zip)");
      return;
    }
    const consent = await getPrivacyConsent();
    if (!consent) {
      setError("You must grant consent in Settings in order to upload projects.");
      return;
    }
=======
  if (!pathInput.trim()) {
    setError("Enter a path first (example: TestResources/sample.zip)");
    return;
  }
  const consent = await getPrivacyConsent();
  if (!consent) { setError("You must grant consent in Settings in order to upload projects."); return; }

  setUploading(true);
  setError(null);
  setUploadStatus("Uploading and analyzing… this may take a moment.");

  try {
>>>>>>> main

    setUploading(true);
    setError(null);

    try {
      const res = await uploadProjectFromPath(pathInput.trim());
      await loadProjects();

      if (res?.projects?.length) await handleSelect(res.projects[0].id);
      setPathInput("");
    } catch (e) {
      setError(e.message ?? "Path upload failed");
    } finally {
      setUploading(false);
    }
<<<<<<< feature/portfolio-web-page
=======

    setUploadStatus(`Done! Loaded ${res?.projects?.length ?? 0} project(s).`);
    setPathInput("");
  } catch (e) {
    setError(e.message ?? "Path upload failed");
    setUploadStatus(null);
  } finally {
    setUploading(false);
>>>>>>> main
  }

  async function handleUpload() {
<<<<<<< feature/portfolio-web-page
    if (!zipFile) {
      setError("Pick a .zip file first.");
      return;
    }
    const consent = await getPrivacyConsent();
    if (!consent) {
      setError("You must grant consent in Settings in order to upload projects.");
      return;
    }
=======
  if (!zipFile) {
    setError("Pick a .zip file first.");
    return;
  }
  const consent = await getPrivacyConsent();
  if (!consent) { setError("You must grant consent in Settings in order to upload projects."); return; }

  setUploading(true);
  setError(null);
  setUploadStatus("Uploading and analyzing… this may take a moment.");

  try {
>>>>>>> main

    setUploading(true);
    setError(null);

    try {
      const res = await uploadProjectZip(zipFile);
      await loadProjects();

      if (res?.projects?.length) await handleSelect(res.projects[0].id);
      setZipFile(null);
    } catch (e) {
      setError(e.message ?? "Upload failed");
    } finally {
      setUploading(false);
    }
<<<<<<< feature/portfolio-web-page
=======

    setUploadStatus(`Done! Loaded ${res?.projects?.length ?? 0} project(s).`);
    setZipFile(null);
  } catch (e) {
    setError(e.message ?? "Upload failed");
    setUploadStatus(null);
  } finally {
    setUploading(false);
>>>>>>> main
  }

  useEffect(() => {
    loadProjects();
  }, []);

  return (
    <>
      <h3>Projects</h3>

      <button onClick={loadProjects} disabled={loading}>
        {loading ? "Loading..." : "Refresh Projects"}
      </button>
      <button
        onClick={async () => {
          setLoading(true);
          setError(null);
          try {
            await clearProjects();
            setSelected(null);
            await loadProjects();
          } catch (e) {
            setError(e.message ?? "Failed to clear database");
          } finally {
            setLoading(false);
          }
        }}
        disabled={loading}
        style={{ marginLeft: 8 }}
      >
        {loading ? "Clearing..." : "Clear Database"}
      </button>

      <div style={{ marginTop: 12, padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
        <h4>Add Project (Upload ZIP)</h4>

<<<<<<< feature/portfolio-web-page
        <input
          type="file"
          accept=".zip"
          onChange={(e) => setZipFile(e.target.files?.[0] ?? null)}
          disabled={loading}
        />

        <button onClick={handleUpload} disabled={uploading || !zipFile} style={{ marginLeft: 8 }}>
          {uploading ? "Uploading..." : "Upload ZIP"}
        </button>

        {zipFile && <p style={{ marginTop: 8, opacity: 0.8 }}>Selected: {zipFile.name}</p>}
      </div>
=======
      <input
        ref={fileInputRef}
        type="file"
        accept=".zip"
        onChange={(e) => setZipFile(e.target.files?.[0] ?? null)}
        disabled={loading}
        style={{ display: "none" }}
      />

      <button
        onClick={() => zipFile ? handleUpload() : fileInputRef.current?.click()}
        disabled={uploading}
        style={{ marginLeft: 8 }}
      >
        {uploading ? "Uploading..." : zipFile ? "Upload ZIP" : "Choose ZIP"}
      </button>

      {uploadStatus && <p style={{ marginTop: 8, opacity: 0.8 }}>{uploadStatus}</p>}

      {zipFile && (
        <p style={{ marginTop: 8, opacity: 0.8 }}>
          Selected: {zipFile.name}
        </p>
      )}
    </div>
>>>>>>> main

      <div style={{ marginTop: 12, padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
        <h4>Quick Load Test Projects</h4>

        {[
          "testResources/testMultiFileAndRepos.zip",
          "testResources/testMultiRepo.zip",
          "testResources/earlyProject.zip",
          "testResources/lateProject.zip",
        ].map((p) => (
          <div key={p} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <code style={{ flex: 1 }}>{p}</code>
            <button onClick={() => setPathInput(p)} disabled={uploading}>Use</button>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 12, padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
        <h4>Or Load from Local Path (Dev)</h4>

        <input
          type="text"
          placeholder="testResources/sample.zip"
          value={pathInput}
          onChange={(e) => setPathInput(e.target.value)}
          disabled={loading}
          style={{ width: 320 }}
        />

        <button onClick={handleUploadPath} disabled={uploading || !pathInput.trim()} style={{ marginLeft: 8 }}>
          {uploading ? "Loading..." : "Load From Path"}
        </button>
      </div>

      {error && <pre style={{ color: "crimson" }}>{error}</pre>}

      <div style={{ display: "flex", gap: 16, marginTop: 12 }}>
        <div style={{ minWidth: 320 }}>
          <h4>Current Projects</h4>
          {currentProjects.length === 0 ? <p>No projects in the current import batch yet.</p> : (
            <ul>
              {currentProjects.map((p) => (
                <li key={`current-${p.id}`}>
                  <button
                    onClick={() => handleSelect(p.id)}
                    disabled={loading}
                    style={{ background: "transparent", border: "none", cursor: "pointer", padding: 0 }}
                  >
                    {p.name} (#{p.id})
                  </button>
                </li>
              ))}
            </ul>
          )}

          <h4>Previous Projects</h4>
          {previousProjects.length === 0 ? <p>No previous projects yet.</p> : (
            <ul>
              {previousProjects.map((p) => (
                <li key={`previous-${p.id}`}>
                  <button
                    onClick={() => handleSelect(p.id)}
                    disabled={loading}
                    style={{ background: "transparent", border: "none", cursor: "pointer", padding: 0 }}
                  >
                    {p.name} (#{p.id})
                  </button>
                </li>
              ))}
            </ul>
          )}

          <p style={{ opacity: 0.7 }}>Total projects stored: {projects.length}</p>
        </div>

        <div style={{ flex: 1 }}>
          <h4>Selected Project</h4>
          {selected ? <pre>{JSON.stringify(selected, null, 2)}</pre> : <p>Click a project to view details.</p>}
        </div>
      </div>
    </>
  );
}

function Badges() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [skills, setSkills] = useState([]);
  const [progress, setProgress] = useState([]);
  const [wrapped, setWrapped] = useState([]);
  const [activeWrappedYear, setActiveWrappedYear] = useState(null);

  async function loadBadgeData() {
    setLoading(true);
    setError(null);
    try {
      const [skillsData, progressData, wrappedData] = await Promise.all([
        listSkills(),
        getBadgeProgress(),
        getYearlyWrapped(),
      ]);
      setSkills(skillsData.skills ?? []);
      setProgress(progressData.badges ?? []);
      setWrapped(wrappedData.wrapped ?? []);
    } catch (e) {
      setError(e.message ?? "Failed to load badges and wrapped stats");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadBadgeData();
  }, []);

  const progressLookup = progress.reduce((acc, badge) => {
    acc[badge.badge_id] = badge;
    return acc;
  }, {});

  const inProgress = progress.filter((b) => !b.earned).map((badge) => ({
    ...badge,
    description: ALL_BADGE_DETAILS[badge.badge_id]?.description ?? "Keep building to unlock this badge.",
    howToEarn: ALL_BADGE_DETAILS[badge.badge_id]?.howToEarn ?? formatBadgeRequirement(badge.metric, badge.target),
  }));

  const achievedProgressBadges = progress.filter((b) => b.earned);
  const achievedBadgeMap = new Map();

  wrapped.forEach((yearBlock) => {
    (yearBlock.milestones ?? []).forEach((m) => {
      if (!achievedBadgeMap.has(m.badge_id)) {
        achievedBadgeMap.set(m.badge_id, { badge_id: m.badge_id, projects: [] });
      }
      const badge = achievedBadgeMap.get(m.badge_id);
      const projectKey = `${m.project}::${m.achieved_on ?? ""}`;
      const alreadyListed = badge.projects.some((p) => `${p.project}::${p.achieved_on ?? ""}` === projectKey);
      if (!alreadyListed) {
        badge.projects.push({
          project: m.project,
          achieved_on: m.achieved_on,
        });
      }
    });
  });

  achievedProgressBadges.forEach((b) => {
    const projectName = b.project?.name ?? "Unknown project";
    if (!achievedBadgeMap.has(b.badge_id)) {
      achievedBadgeMap.set(b.badge_id, { badge_id: b.badge_id, label: b.label, projects: [] });
    }
    const badge = achievedBadgeMap.get(b.badge_id);
    if (!badge.label) badge.label = b.label;
    const alreadyListed = badge.projects.some((p) => p.project === projectName);
    if (!alreadyListed) badge.projects.push({ project: projectName, achieved_on: null });
  });

  const achievedBadges = Array.from(achievedBadgeMap.values())
    .map((badge) => ({
      ...badge,
      label: badge.label ?? ALL_BADGE_DETAILS[badge.badge_id]?.label ?? formatBadgeLabel(badge.badge_id),
      description: ALL_BADGE_DETAILS[badge.badge_id]?.description ?? "Unlocked through project analytics.",
      howToEarn: ALL_BADGE_DETAILS[badge.badge_id]?.howToEarn ?? "Complete its badge conditions in a project.",
    }))
    .sort((a, b) => (a.label ?? a.badge_id).localeCompare(b.label ?? b.badge_id));

  const unlockedSet = new Set(achievedBadges.map((badge) => badge.badge_id));
  const allBadgeCatalog = Object.entries(ALL_BADGE_DETAILS)
    .map(([badgeId, details]) => ({
      badgeId,
      ...details,
      unlocked: unlockedSet.has(badgeId),
      trackedProgress: progressLookup[badgeId] ?? null,
    }))
    .sort((a, b) => a.label.localeCompare(b.label));

  const now = new Date();
  const currentYear = now.getFullYear();
  const isCurrentYearComplete = now.getMonth() === 11 && now.getDate() === 31;

  const wrappedByYear = wrapped.reduce((acc, yearBlock) => {
    acc[yearBlock.year] = yearBlock;
    return acc;
  }, {});

  const wrappedButtons = wrapped.map((yearBlock) => ({
    year: yearBlock.year,
    label:
      yearBlock.year === currentYear
        ? isCurrentYearComplete
          ? "Get Yearly Stats"
          : "Get Yearly Stats (so far)"
        : `Get ${yearBlock.year} Stats`,
  }));

  const openWrappedYear = (year) => setActiveWrappedYear(year);
  const selectedWrapped = activeWrappedYear ? wrappedByYear[activeWrappedYear] : null;

  return (
    <>
      <h3>Badges</h3>
      <button onClick={loadBadgeData} disabled={loading}>
        {loading ? "Loading..." : "Refresh Badge Data"}
      </button>

      {error && <pre style={{ color: "crimson" }}>{error}</pre>}

      <section className="badges-hero">
        <h4>🏆 All Possible Badges</h4>
        <p>Every badge, what it means, and how to earn it.</p>
        <div className="badge-guide-grid">
          {allBadgeCatalog.map((badge) => (
            <article className="badge-guide-card" key={badge.badgeId}>
              <h5>{badge.label} {badge.unlocked ? "✅" : "🔒"}</h5>
              <p>{badge.description}</p>
              <p><strong>How to earn:</strong> {badge.howToEarn}</p>
              <p className="badge-description">{badge.trackedProgress ? `Tracked progress: ${Math.round((badge.trackedProgress.progress ?? 0) * 100)}%` : "Tracked progress: calculated when unlocked in projects."}</p>
            </article>
          ))}
        </div>
      </section>

      <h4>🎯 Badge Progress Tracker (Uncompleted)</h4>
      {inProgress.length === 0 ? (
        <p>All tracked progress badges are complete 🎉</p>
      ) : (
        <ul className="in-progress-list">
          {inProgress.map((b) => (
            <li key={b.badge_id} className="progress-card">
              <strong>{b.label}</strong> — {Math.round((b.progress ?? 0) * 100)}%
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${Math.round((b.progress ?? 0) * 100)}%` }} />
              </div>
              <small>
                {b.metric}: {(b.current ?? 0).toFixed(2)} / {b.target} • Closest project: {b.project?.name ?? "N/A"} • ⏳ In progress
              </small>
              <p className="badge-description">{b.description}</p>
              <p className="badge-description"><strong>How to earn:</strong> {b.howToEarn}</p>
            </li>
          ))}
        </ul>
      )}

      <h4>🏅 Unlocked Badges</h4>
      {achievedBadges.length === 0 ? (
        <p>No achieved badges yet. Upload and analyze projects to start earning them.</p>
      ) : (
        <ul>
          {achievedBadges.map((badge) => (
            <li key={`achieved-${badge.badge_id}`}>
              ✅ <strong>{badge.label ?? badge.badge_id}</strong>
              <p className="badge-description">{badge.description}</p>
              <p className="badge-description"><strong>How to earn:</strong> {badge.howToEarn}</p>
              <ul>
                {badge.projects.map((projectEntry, idx) => (
                  <li key={`achieved-${badge.badge_id}-${projectEntry.project}-${idx}`}>
                    <strong>{projectEntry.project}</strong>
                    {projectEntry.achieved_on ? ` — ${projectEntry.achieved_on}` : ""}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      )}
      <h4>🎉 Yearly Wrapped</h4>
      {wrapped.length === 0 ? (
        <p>No yearly wrapped history available yet.</p>
      ) : (
        <div className="wrapped-buttons">
          {wrappedButtons.map((button) => (
            <button key={button.year} onClick={() => openWrappedYear(button.year)}>
              {button.label}
            </button>
          ))}
        </div>
      )}

      {selectedWrapped ? (
        <div className="wrapped-modal-backdrop" onClick={() => setActiveWrappedYear(null)}>
          <div className="wrapped-modal" onClick={(event) => event.stopPropagation()}>
            <button className="wrapped-close" onClick={() => setActiveWrappedYear(null)}>✕</button>
            <h5>{selectedWrapped.year} — {selectedWrapped.vibe_title}</h5>
            <p>
              Projects: {selectedWrapped.projects_count} • LOC: {selectedWrapped.total_loc} • Files: {selectedWrapped.total_files} • Avg test ratio: {(selectedWrapped.avg_test_file_ratio * 100).toFixed(1)}%
            </p>
            {selectedWrapped.highlights?.length ? (
              <ul>
                {selectedWrapped.highlights.map((line, idx) => (
                  <li key={`${selectedWrapped.year}-highlight-${idx}`}>{line}</li>
                ))}
              </ul>
            ) : null}
            <p><strong>Milestones:</strong></p>
            {selectedWrapped.milestones?.length ? (
              <ul>
                {selectedWrapped.milestones.map((m, idx) => (
                  <li key={`${selectedWrapped.year}-${m.badge_id}-${idx}`}>
                    🏅 {(ALL_BADGE_DETAILS[m.badge_id]?.label ?? progressLookup[m.badge_id]?.label ?? formatBadgeLabel(m.badge_id))} earned in <strong>{m.project}</strong>{m.achieved_on ? ` on ${m.achieved_on}` : ""}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No badge milestones recorded for this year.</p>
            )}
          </div>
        </div>
      ) : null}

      <h4>🔥 Skill Heatmap</h4>
      {skills.length === 0 ? (
        <p>No skills found yet. Upload a project first.</p>
      ) : (
        <ul>
          {skills.map((s) => (
            <li key={s.name}>
              {s.name} — used in {s.project_count} project{s.project_count === 1 ? "" : "s"}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function Help() {
  return <><h3>This is the Help page.</h3></>;
}

export default App;
