import { useEffect, useState } from "react";
import {
  listSkills,
  getBadgeProgress,
  getYearlyWrapped,
} from "../api/client";

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

export default Badges;

