import { useEffect, useState } from "react";
import {
  listSkillsUsage,
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

const drawRoundedRect = (ctx, x, y, width, height, radius = 16) => {
  const safeRadius = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + safeRadius, y);
  ctx.lineTo(x + width - safeRadius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + safeRadius);
  ctx.lineTo(x + width, y + height - safeRadius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - safeRadius, y + height);
  ctx.lineTo(x + safeRadius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - safeRadius);
  ctx.lineTo(x, y + safeRadius);
  ctx.quadraticCurveTo(x, y, x + safeRadius, y);
  ctx.closePath();
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
  const [activeHeatmapBadgeId, setActiveHeatmapBadgeId] = useState(null);
  const [activeSkill, setActiveSkill] = useState(null);

  const [, setShareFeedback] = useState("");

  const setTimedFeedback = (message) => {
    setShareFeedback(message);
    window.setTimeout(() => setShareFeedback(""), 3500);
  };

  const openLinkedInShareWindow = (deepLink) => {
    const shareUrl = new URL("https://www.linkedin.com/sharing/share-offsite/");
    shareUrl.searchParams.set("url", deepLink || window.location.href);
    window.open(shareUrl.toString(), "_blank", "noopener,noreferrer");
  };

  const copyThenOpenLinkedIn = async (copyTask, deepLink) => {
    // Open synchronously before any await so the user gesture context is preserved.
    // Browsers/macOS block window.open called after an await.
    openLinkedInShareWindow(deepLink);

    const copyResult = await Promise.race([
      copyTask().then(() => true).catch(() => false),
      new Promise((resolve) => {
        window.setTimeout(() => resolve(false), 1200);
      }),
    ]);

    if (!copyResult) {
      setTimedFeedback("Opened LinkedIn. If copy didn't finish, use the Share button first, then paste.");
    }
  };

  const copyBadgeThenOpenLinkedIn = async (badge, achievedBadge, deepLink) => {
    await copyThenOpenLinkedIn(() => shareBadgeWithImage(badge, achievedBadge), deepLink);
  };

  const copyWrappedThenOpenLinkedIn = async (yearBlock, deepLink) => {
    await copyThenOpenLinkedIn(() => shareWrappedWithImage(yearBlock), deepLink);
  };

  const copyImageAndCaptionToClipboard = async (imageBlob, text) => {
    if (!(navigator?.clipboard?.write && window.ClipboardItem)) {
      return false;
    }

    const clipboardPayload = {
      "image/png": imageBlob,
    };
    if (text) {
      clipboardPayload["text/plain"] = new Blob([text], { type: "text/plain" });
    }

    await navigator.clipboard.write([
      new window.ClipboardItem(clipboardPayload),
    ]);
    return true;
  };


  const buildBadgeShareImage = async (badge, achievedBadge) => {
    const width = 1200;
    const height = 627;
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas not supported");

    const gradient = ctx.createLinearGradient(0, 0, width, height);
    gradient.addColorStop(0, "#051b38");
    gradient.addColorStop(1, "#0d1117");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);

    ctx.fillStyle = "rgba(88,166,255,0.2)";
    ctx.beginPath();
    ctx.arc(1010, 110, 62, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "rgba(159,231,182,0.25)";
    ctx.beginPath();
    ctx.arc(1080, 172, 30, 0, Math.PI * 2);
    ctx.fill();

    drawRoundedRect(ctx, 70, 62, 1060, 510, 24);
    ctx.fillStyle = "rgba(9, 22, 39, 0.64)";
    ctx.fill();
    ctx.strokeStyle = "rgba(88,166,255,0.4)";
    ctx.stroke();

    ctx.fillStyle = "#9fe7b6";
    ctx.font = "700 32px 'DM Sans', 'Segoe UI', sans-serif";
    ctx.fillText("Badge Unlocked", 104, 124);

    ctx.fillStyle = "#f2fbff";
    ctx.font = "700 56px 'DM Sans', 'Segoe UI', sans-serif";
    ctx.fillText(badge.label, 104, 190);

    drawRoundedRect(ctx, 650, 146, 176, 58, 16);
    ctx.fillStyle = badge.unlocked ? "rgba(63, 185, 80, 0.2)" : "rgba(247, 129, 102, 0.2)";
    ctx.fill();
    ctx.strokeStyle = badge.unlocked ? "rgba(63, 185, 80, 0.65)" : "rgba(247, 129, 102, 0.65)";
    ctx.stroke();
    ctx.fillStyle = badge.unlocked ? "#9fe7b6" : "#ffd7c8";
    ctx.font = "700 30px 'DM Sans', 'Segoe UI', sans-serif";
    ctx.fillText(badge.unlocked ? "Unlocked" : "In Progress", 670, 185);

    ctx.fillStyle = "#d8edf8";
    ctx.font = "500 26px 'DM Sans', 'Segoe UI', sans-serif";
    ctx.fillText(ALL_BADGE_DETAILS[badge.badgeId]?.description ?? "Unlocked through project analytics.", 104, 238);

    const completion = badge.unlocked ? 100 : badge.completionPercent ?? 0;
    drawRoundedRect(ctx, 104, 276, 992, 98, 14);
    ctx.fillStyle = "rgba(19, 36, 55, 0.7)";
    ctx.fill();
    ctx.strokeStyle = "rgba(88,166,255,0.25)";
    ctx.stroke();
    ctx.fillStyle = "#e6edf3";
    ctx.font = "600 26px 'DM Sans', 'Segoe UI', sans-serif";
    ctx.fillText(`Progress: ${completion}%`, 120, 316);
    drawRoundedRect(ctx, 120, 330, 960, 20, 12);
    ctx.fillStyle = "rgba(41, 65, 93, 0.9)";
    ctx.fill();
    drawRoundedRect(ctx, 120, 330, Math.max(60, (960 * completion) / 100), 20, 12);
    ctx.fillStyle = "rgba(88,166,255,0.95)";
    ctx.fill();
    
    const projectLines = (achievedBadge?.projects ?? []).slice(0, 3).map((entry) =>
      entry.achieved_on ? `• ${entry.project} (${entry.achieved_on})` : `• ${entry.project}`,
    );
    const fallbackProject = badge.trackedProgress?.project?.name ? [`• ${badge.trackedProgress.project.name}`] : ["• Keep shipping to unlock this badge."];
    const displayProjects = projectLines.length ? projectLines : fallbackProject;

    ctx.fillStyle = "#9bc9ff";
    ctx.font = "600 24px 'DM Sans', 'Segoe UI', sans-serif";
    ctx.fillText("Projects tied to this badge", 104, 422);
    ctx.fillStyle = "#e6edf3";
    ctx.font = "500 22px 'DM Sans', 'Segoe UI', sans-serif";
    displayProjects.forEach((line, idx) => {
      ctx.fillText(line, 104, 462 + idx * 34);
    });

    ctx.fillStyle = "#cfeaf7";
    ctx.font = "500 22px 'DM Sans', 'Segoe UI', sans-serif";


    return new Promise((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (blob) resolve(blob);
        else reject(new Error("Could not export badge image"));
      }, "image/png");
    });
  };

  const shareBadgeWithImage = async (badge, achievedBadge) => {
    const text = buildBadgeShareText(badge, achievedBadge);

    try {
      const imageBlob = await buildBadgeShareImage(badge, achievedBadge);
      const imageFile = new File([imageBlob], `badge-${badge.badgeId}.png`, { type: "image/png" });

      if (navigator?.share && navigator?.canShare?.({ files: [imageFile] })) {
        await navigator.share({ files: [imageFile], text, title: `${badge.label} Badge` });
        setTimedFeedback("Opened your device share sheet for posting to any app.");
        return;
      }

      if (await copyImageAndCaptionToClipboard(imageBlob, text)) {
        setTimedFeedback("Badge image + caption copied to clipboard. Open LinkedIn (or any platform) and paste.");
      } else {
        const objectUrl = URL.createObjectURL(imageBlob);
        const downloadLink = document.createElement("a");
        downloadLink.href = objectUrl;
        downloadLink.download = `badge-${badge.badgeId}.png`;
        downloadLink.click();
        URL.revokeObjectURL(objectUrl);
        if (navigator?.clipboard?.writeText) {
          await navigator.clipboard.writeText(text);
        }
        setTimedFeedback("Badge image downloaded and caption copied when possible. Upload it to LinkedIn (or any platform).");
      }
    } catch {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      }
      setTimedFeedback("Could not generate badge image. Caption copied when possible.");
    }
  };

  const buildBadgeShareText = (badge, achievedBadge) => {
    const projectLabel = achievedBadge?.projects?.[0]?.project;
    if (projectLabel) {
      return `I just unlocked the ${badge.label} badge on my developer dashboard for ${projectLabel}. 🚀 #DeveloperJourney #Portfolio`;
    }
    return `I just unlocked the ${badge.label} badge on my developer dashboard. 🚀 #DeveloperJourney #Portfolio`;
  };

  const buildWrappedShareText = (yearBlock) =>
    `My ${yearBlock.year} Developer Wrapped: ${yearBlock.projects_count} projects, ${yearBlock.total_loc} lines of code, ${yearBlock.total_files} files, and ${yearBlock.milestones?.length ?? 0} badge milestones. 📈 #YearInReview #SoftwareEngineering`;

  const buildWrappedShareImage = async (yearBlock) => {
    const width = 1200;
    const height = 627;
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas not supported");

    const gradient = ctx.createLinearGradient(0, 0, width, height);
    gradient.addColorStop(0, "#03132e");
    gradient.addColorStop(1, "#0d1117");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);

    const glow = ctx.createRadialGradient(920, 70, 40, 920, 70, 420);
    glow.addColorStop(0, "rgba(88,166,255,0.22)");
    glow.addColorStop(1, "rgba(88,166,255,0)");
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, width, height);

    ctx.fillStyle = "rgba(88,166,255,0.22)";
    ctx.beginPath();
    ctx.arc(1080, 112, 56, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "rgba(247,129,102,0.22)";
    ctx.beginPath();
    ctx.arc(1020, 170, 24, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "#58a6ff";
    ctx.font = "600 27px 'DM Sans', 'Segoe UI', sans-serif";
    ctx.fillText(yearBlock.vibe_title || "Your year in code", 70, 132);

    const statCards = [
      { label: "Projects shipped", value: `${yearBlock.projects_count}` },
      { label: "Lines of code", value: `${yearBlock.total_loc.toLocaleString()}` },
      { label: "Files touched", value: `${yearBlock.total_files.toLocaleString()}` },
      { label: "Average test ratio", value: `${((yearBlock.avg_test_file_ratio ?? 0) * 100).toFixed(1)}%` },
      { label: "Badge milestones", value: `${yearBlock.milestones?.length ?? 0}` },
    ];

    const cardWidth = 332;
    const cardHeight = 88;
    const cardGap = 16;
    const startX = 70;
    const startY = 172;

    statCards.forEach((card, index) => {
      const col = index % 3;
      const row = Math.floor(index / 3);
      const x = startX + (cardWidth + cardGap) * col;
      const y = startY + (cardHeight + cardGap) * row;

      drawRoundedRect(ctx, x, y, cardWidth, cardHeight, 16);
      ctx.fillStyle = "rgba(13,17,23,0.68)";
      ctx.fill();
      ctx.strokeStyle = "rgba(88,166,255,0.35)";
      ctx.lineWidth = 1.2;
      ctx.stroke();

      ctx.fillStyle = "#9bc9ff";
      ctx.font = "500 19px 'DM Sans', 'Segoe UI', sans-serif";
      ctx.fillText(card.label, x + 20, y + 33);
      ctx.fillStyle = "#f2fbff";
      ctx.font = "700 28px 'DM Sans', 'Segoe UI', sans-serif";
      ctx.fillText(card.value, x + 20, y + 68);
    });

    const highlights = (yearBlock.highlights ?? []).slice(0, 2);
    const milestonePreview = (yearBlock.milestones ?? []).slice(0, 2)
      .map((m) => `🏅 ${(ALL_BADGE_DETAILS[m.badge_id]?.label ?? formatBadgeLabel(m.badge_id))} • ${m.project}`);

    drawRoundedRect(ctx, 70, 380, 1060, 174, 18);
    ctx.fillStyle = "rgba(7, 21, 40, 0.7)";
    ctx.fill();
    ctx.strokeStyle = "rgba(151, 201, 255, 0.26)";
    ctx.stroke();
    ctx.fillStyle = "#cfeaf7";
    ctx.font = "600 24px 'DM Sans', 'Segoe UI', sans-serif";
    ctx.fillText("Year Highlights", 92, 418);
    ctx.font = "500 20px 'DM Sans', 'Segoe UI', sans-serif";
    highlights.forEach((line, idx) => {
      ctx.fillText(`• ${line}`, 92, 452 + idx * 30);
    });

    if (milestonePreview.length > 0) {
      ctx.fillStyle = "#9fe7b6";
      ctx.font = "600 21px 'DM Sans', 'Segoe UI', sans-serif";
      ctx.fillText("Badge moments", 640, 418);
      ctx.fillStyle = "#d7f8e3";
      ctx.font = "500 18px 'DM Sans', 'Segoe UI', sans-serif";
      milestonePreview.forEach((line, idx) => {
        ctx.fillText(line, 640, 452 + idx * 30);
      });
    } else {
      ctx.fillStyle = "#d8edf8";
      ctx.font = "500 18px 'DM Sans', 'Segoe UI', sans-serif";
      ctx.fillText("No badge milestones yet — next year is your glow-up arc ✨", 640, 452);
    }

    ctx.fillStyle = "#cfeaf7";
    ctx.font = "500 24px 'DM Sans', 'Segoe UI', sans-serif";
    ctx.fillText("Built with Capstone Portfolio Insights", 70, 595);

    return new Promise((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (blob) resolve(blob);
        else reject(new Error("Could not export yearly wrapped image"));
      }, "image/png");
    });
  };

  const shareWrappedWithImage = async (yearBlock) => {
    const text = buildWrappedShareText(yearBlock);

    try {
      const imageBlob = await buildWrappedShareImage(yearBlock);
      const imageFile = new File([imageBlob], `developer-wrapped-${yearBlock.year}.png`, { type: "image/png" });

      if (await copyImageAndCaptionToClipboard(imageBlob, text)) {
        setTimedFeedback("Wrapped image + caption copied to clipboard. Open LinkedIn (or any platform) and paste.");
        return;
      }

      if (navigator?.share && navigator?.canShare?.({ files: [imageFile] })) {
        await navigator.share({ files: [imageFile], text, title: `${yearBlock.year} Developer Wrapped` });
        setTimedFeedback("Opened your device share sheet for posting to any app.");
        return;
      }

      if (await copyImageAndCaptionToClipboard(imageBlob, text)) {
        setTimedFeedback("Wrapped image + caption copied to clipboard. Open LinkedIn (or any platform) and paste.");
      } else {
        const objectUrl = URL.createObjectURL(imageBlob);
        const downloadLink = document.createElement("a");
        downloadLink.href = objectUrl;
        downloadLink.download = `developer-wrapped-${yearBlock.year}.png`;
        downloadLink.click();
        URL.revokeObjectURL(objectUrl);
        if (navigator?.clipboard?.writeText) {
          await navigator.clipboard.writeText(text);
        }
        setTimedFeedback("Wrapped image downloaded and caption copied when possible. Upload it to LinkedIn (or any platform).");
      }
    } catch {
      if (navigator?.clipboard?.write && window.ClipboardItem) {
        await navigator.clipboard.write([
          new window.ClipboardItem({
            "text/plain": new Blob([text], { type: "text/plain" }),
          }),
        ]);
      }
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      }
      setTimedFeedback("Could not generate wrapped image. Caption copied when possible.");
    }
  };

  async function loadBadgeData() {
    setLoading(true);
    setError(null);
    try {
      const [skillsData, progressData, wrappedData] = await Promise.all([
        listSkillsUsage(),
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

  const inProgress = progress.filter((b) => !b.earned && (b.progress ?? 0) > 0).map((badge) => ({
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

  const badgeHeatmapTiles = allBadgeCatalog.map((badge) => {
    const progressValue = badge.unlocked ? 1 : (badge.trackedProgress?.progress ?? 0);
    const completionPercent = Math.round(progressValue * 100);
    const stateLabel = badge.unlocked ? "Unlocked" : completionPercent === 0 ? "Not started" : `${completionPercent}% complete`;

    let intensityClass = "badge-heatmap-tile--cold";
    if (badge.unlocked || completionPercent >= 90) intensityClass = "badge-heatmap-tile--hot";
    else if (completionPercent >= 60) intensityClass = "badge-heatmap-tile--warm";
    else if (completionPercent >= 30) intensityClass = "badge-heatmap-tile--mild";

    return {
      ...badge,
      completionPercent,
      stateLabel,
      intensityClass,
    };
  });

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
  const selectedHeatmapBadge = activeHeatmapBadgeId
    ? badgeHeatmapTiles.find((badge) => badge.badgeId === activeHeatmapBadgeId) ?? null
    : null;
  const selectedAchievedBadge = selectedHeatmapBadge
    ? achievedBadges.find((badge) => badge.badge_id === selectedHeatmapBadge.badgeId) ?? null
    : null;
  const maxSkillProjects = Math.max(...skills.map((s) => Number(s.project_count) || 0), 1);

  return (
    <div className="badges-page">
      <h3>Badges</h3>
      <button onClick={loadBadgeData} disabled={loading}>
        {loading ? "Loading..." : "Refresh Badge Data"}
      </button>

      {error && <pre style={{ color: "crimson" }}>{error}</pre>}

      <section className="badge-heatmap">
        <h4>🏆 All Badges</h4>
        <p>
          Click any badge tile to view details. Darker tiles indicate higher completion progress.
          {" "}
          {achievedBadges.length > 0
            ? `${achievedBadges.length} unlocked badge${achievedBadges.length === 1 ? "" : "s"} are now listed directly in each badge modal.`
            : "Unlock badges to see completion history by project."}
        </p>
        <div className="badge-heatmap-grid">
          {badgeHeatmapTiles.map((badge) => (
            <button
              type="button"
              key={`heatmap-${badge.badgeId}`}
              className={`badge-heatmap-tile ${badge.intensityClass}`}
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                setActiveHeatmapBadgeId(badge.badgeId);
              }}
              aria-label={`Open ${badge.label} badge details`}
            >
              <div className="badge-heatmap-header">
                <strong>{badge.label}</strong>
                <span>{badge.unlocked ? "✅" : "🔒"}</span>
              </div>
              <p>{badge.stateLabel}</p>
            </button>
          ))}
        </div>
      </section>

      <h4>🎯 Badge Progress Tracker</h4>
      {inProgress.length === 0 ? (
        <p>No started in-progress badges yet. Start building to unlock more badges.</p>
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

      {selectedHeatmapBadge ? (
        <div className="badge-detail-backdrop" onClick={() => setActiveHeatmapBadgeId(null)}>
          <div className="badge-detail-modal" role="dialog" aria-modal="true" aria-label={`${selectedHeatmapBadge.label} badge details`} onClick={(event) => event.stopPropagation()}>
            <button className="wrapped-close" onClick={() => setActiveHeatmapBadgeId(null)}>✕</button>
            <h5>{selectedHeatmapBadge.label}</h5>
            <p>{selectedHeatmapBadge.description}</p>
            <p><strong>How to earn:</strong> {selectedHeatmapBadge.howToEarn}</p>
            <p>
              <strong>Progress:</strong> {selectedHeatmapBadge.stateLabel}
              {selectedHeatmapBadge.trackedProgress?.project?.name ? ` • Closest project: ${selectedHeatmapBadge.trackedProgress.project.name}` : ""}
            </p>
            {selectedAchievedBadge?.projects?.length ? (
              <>
                <p><strong>Completed in:</strong></p>
                <ul>
                  {selectedAchievedBadge.projects.map((projectEntry, idx) => (
                    <li key={`modal-achieved-${selectedHeatmapBadge.badgeId}-${projectEntry.project}-${idx}`}>
                      <strong>{projectEntry.project}</strong>
                      {projectEntry.achieved_on ? ` — ${projectEntry.achieved_on}` : ""}
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p>No completion milestones yet for this badge.</p>
            )}

            <div className="linkedin-share-panel">
              <button
                type="button"
                onClick={() =>
                  shareBadgeWithImage(selectedHeatmapBadge, selectedAchievedBadge)
                }
              >
                 Share Badge Card Image (Any Platform)
              </button>
              <button
                type="button"
                onClick={() =>
                  copyBadgeThenOpenLinkedIn(
                    selectedHeatmapBadge,
                    selectedAchievedBadge,
                    `${window.location.origin}${window.location.pathname}#badge-${selectedHeatmapBadge.badgeId}`,
                  )
                }
              >
                Open LinkedIn Composer
              </button>
              <small>
                The share button only uses your device share sheet / clipboard / download. The LinkedIn button copies first, then opens LinkedIn so you can paste immediately.
              </small>
            </div>
          </div>
        </div>
      ) : null}

      {selectedWrapped ? (
        <div className="wrapped-modal-backdrop" onClick={() => setActiveWrappedYear(null)}>
          <div className="wrapped-modal" onClick={(event) => event.stopPropagation()}>
            <button className="wrapped-close" onClick={() => setActiveWrappedYear(null)}>✕</button>
            <h5>{selectedWrapped.year} — {selectedWrapped.vibe_title}</h5>
            <div className="wrapped-stat-grid">
              <div className="wrapped-stat-card"><span>Projects</span><strong>{selectedWrapped.projects_count}</strong></div>
              <div className="wrapped-stat-card"><span>LOC</span><strong>{selectedWrapped.total_loc.toLocaleString()}</strong></div>
              <div className="wrapped-stat-card"><span>Files</span><strong>{selectedWrapped.total_files.toLocaleString()}</strong></div>
              <div className="wrapped-stat-card"><span>Avg Test Ratio</span><strong>{(selectedWrapped.avg_test_file_ratio * 100).toFixed(1)}%</strong></div>
            </div>
            {selectedWrapped.highlights?.length ? (
              <ul className="wrapped-highlights-list">
                {selectedWrapped.highlights.map((line, idx) => (
                  <li key={`${selectedWrapped.year}-highlight-${idx}`}>{line}</li>
                ))}
              </ul>
            ) : null}
            <p><strong>Milestones:</strong></p>
            {selectedWrapped.milestones?.length ? (
              <ul className="wrapped-milestone-list">
                {selectedWrapped.milestones.map((m, idx) => (
                  <li key={`${selectedWrapped.year}-${m.badge_id}-${idx}`} className="wrapped-milestone-item">
                    🏅 {(ALL_BADGE_DETAILS[m.badge_id]?.label ?? progressLookup[m.badge_id]?.label ?? formatBadgeLabel(m.badge_id))} earned in <strong>{m.project}</strong>{m.achieved_on ? ` on ${m.achieved_on}` : ""}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No badge milestones recorded for this year.</p>
            )}
            <div className="linkedin-share-panel">
              <button
                type="button"
                onClick={() =>
                  shareWrappedWithImage(selectedWrapped)
                }
              >
                Share Wrapped Image (Any Platform)
              </button>
              <button
                type="button"
                onClick={() =>
                  copyWrappedThenOpenLinkedIn(
                    selectedWrapped,
                    `${window.location.origin}${window.location.pathname}#wrapped-${selectedWrapped.year}`,
                  )
                }
              >
                Open LinkedIn Composer
              </button>
              <small>
                The share button only uses your device share sheet / clipboard / download. The LinkedIn button copies first, then opens LinkedIn so you can paste immediately.
              </small>
            </div>
          </div>
        </div>
      ) : null}

      <section className="skill-heatmap">
        <h4>🔥 Skill Heatmap</h4>
        {skills.length === 0 ? (
          <p>No skills found yet. Upload a project first.</p>
        ) : (
          <div className="skill-heatmap-grid">
            {skills.map((s) => {
              const count = Number(s.project_count) || 0;
              const fillPercent = Math.round((count / maxSkillProjects) * 100);
              const skillDomId = `skill-projects-${s.name.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
              return (
                <article
                  key={s.name}
                  className={`skill-heatmap-tile ${activeSkill === s.name ? "skill-heatmap-tile--active" : ""}`}
                >
                  <button
                    type="button"
                    className="skill-heatmap-trigger"
                    onClick={() => setActiveSkill((prev) => (prev === s.name ? null : s.name))}
                    aria-expanded={activeSkill === s.name}
                    aria-controls={skillDomId}
                  >
                    <div className="skill-heatmap-title-row">
                      <strong>{s.name}</strong>
                      <span>{count} project{count === 1 ? "" : "s"}</span>
                    </div>
                  </button>
                  <div className="skill-heatmap-bar" aria-hidden="true">
                    <div className="skill-heatmap-bar-fill" style={{ width: `${fillPercent}%` }} />
                  </div>
                  {activeSkill === s.name && (
                    <div className="skill-project-list" id={skillDomId}>
                      <p><strong>Used in:</strong></p>
                      <ul>
                        {(s.projects ?? []).map((projectName) => (
                          <li key={`${s.name}-${projectName}`}>{projectName}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}

export default Badges;

