function dayLabel(iso) {
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function monthLabel(iso) {
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString(undefined, { month: "short" });
}

function intensityClass(level) {
  if (level <= 0) return "pf-hm-cell--0";
  if (level === 1) return "pf-hm-cell--1";
  if (level === 2) return "pf-hm-cell--2";
  if (level === 3) return "pf-hm-cell--3";
  return "pf-hm-cell--4";
}

function weekChunks(days) {
  const out = [];
  for (let i = 0; i < days.length; i += 7) out.push(days.slice(i, i + 7));
  return out;
}

function monthAnchors(weeks) {
  const anchors = [];
  let prev = "";
  weeks.forEach((week, idx) => {
    const label = monthLabel(week?.[0]?.date);
    if (label !== prev) {
      anchors.push({ idx, label });
      prev = label;
    }
  });
  return anchors;
}

export default function PortfolioActivityHeatmap({ data, loading }) {
  if (loading) {
    return (
      <section className="pf-hm-panel">
        <h4>Activity Heatmap</h4>
        <span className="pf-hm-sub">Loading activity…</span>
      </section>
    );
  }

  if (!data?.days_series?.length) {
    return (
      <section className="pf-hm-panel">
        <h4>Activity Heatmap</h4>
        <span className="pf-hm-sub">No activity data available.</span>
      </section>
    );
  }

  const weeks = weekChunks(data.days_series);
  const anchors = monthAnchors(weeks);
  const agg = data.aggregate ?? { total_commits: 0, total_lines_changed: 0, active_days: 0 };

  return (
    <section className="pf-hm-panel gh-like-heatmap" data-testid="portfolio-activity-heatmap">
      <div className="pf-hm-header">
        <h4>Activity Heatmap</h4>
        <span className="pf-hm-sub">
          {data.usernames?.length ? `Contributors: ${data.usernames.join(", ")}` : "All contributors"} · Last {data.days} days
        </span>
      </div>

      <div className="pf-hm-stats">
        <div className="pf-hm-stat"><strong>{agg.total_commits}</strong><span>Commits</span></div>
        <div className="pf-hm-stat"><strong>{agg.total_lines_changed}</strong><span>Lines changed</span></div>
        <div className="pf-hm-stat"><strong>{agg.active_days}</strong><span>Active days</span></div>
      </div>

      <div className="pf-hm-scroll" aria-label="Activity timeline scroll container">
        <div className="pf-hm-track">
          <div className="pf-hm-month-row">
            {anchors.map((m) => (
              <span key={`m-${m.idx}-${m.label}`} className="pf-hm-month" style={{ gridColumn: `${m.idx + 1} / span 1` }}>
                {m.label}
              </span>
            ))}
          </div>

          <div className="pf-hm-grid">
            {weeks.map((week, i) => (
              <div className="pf-hm-week-col" key={`w-${i}`}>
                {week.map((d) => (
                  <div
                    key={d.date}
                    className={`pf-hm-cell ${intensityClass(d.intensity)}`}
                    title={`${dayLabel(d.date)} · ${d.commits} commits · ${d.lines_changed} lines changed`}
                  />
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="pf-hm-legend">
        <span>Less</span>
        <span className="pf-hm-cell pf-hm-cell--0" />
        <span className="pf-hm-cell pf-hm-cell--1" />
        <span className="pf-hm-cell pf-hm-cell--2" />
        <span className="pf-hm-cell pf-hm-cell--3" />
        <span className="pf-hm-cell pf-hm-cell--4" />
        <span>More</span>
      </div>
    </section>
  );
}
