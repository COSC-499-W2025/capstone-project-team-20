import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PortfolioPage from "../pages/PortfolioPage";

vi.mock("../api/client", () => ({
  listProjects: vi.fn(),
  createReport: vi.fn(),
  listReports: vi.fn(),
  getReport: vi.fn(),
  exportResume: vi.fn(),
  exportPortfolio: vi.fn(),
  generatePortfolioDetailsForReport: vi.fn(),
  getPortfolio: vi.fn(),
  setPrivacyConsent: vi.fn(),
  updatePortfolioMode: vi.fn(),
  updatePortfolioProject: vi.fn(),
  publishPortfolio: vi.fn(),
  unpublishPortfolio: vi.fn(),
  getBadgeProgress: vi.fn(),
  getPortfolioActivityHeatmap: vi.fn(),
}));

import {
  listProjects,
  listReports,
  getReport,
  generatePortfolioDetailsForReport,
  getPortfolio,
  setPrivacyConsent,
  updatePortfolioProject,
  publishPortfolio,
  unpublishPortfolio,
  getBadgeProgress,
  getPortfolioActivityHeatmap,
} from "../api/client";

describe("PortfolioPage web portfolio", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    setPrivacyConsent.mockResolvedValue({ consent: true });
    listProjects.mockResolvedValue({ projects: [{ id: 1, name: "Proj A" }] });
    listReports.mockResolvedValue({ reports: [{ id: 9, title: "My Report", report_kind: "portfolio", project_count: 1 }] });
    getReport.mockResolvedValue({ report: { id: 9, title: "My Report", report_kind: "portfolio", project_count: 1, sort_by: "resume_score" } });
    generatePortfolioDetailsForReport.mockResolvedValue({ ok: true, updated_project_names: ["Proj A"] });

    getBadgeProgress.mockResolvedValue({
      badges: [
        { badge_id: "polyglot", label: "Polyglot", earned: false, progress: 0.65, target: 3, current: 2, metric: "Languages used", project: { id: 1, name: "Proj A" } },
        { badge_id: "team_effort", label: "Team Effort", earned: true, progress: 1, target: 3, current: 4, metric: "Contributors", project: { id: 1, name: "Proj A" } },
      ],
    });

    getPortfolio.mockResolvedValue({
      portfolio:{
        title:"Portfolio Report",
        portfolio_mode:"public",
        public_url:"http://localhost:8000/public/portfolio/my-report",
        public_token:"my-report",
        projects:[
          {
            project_name: "Proj A",
            summary: "Short summary",
            bullets: ["Implemented API layer"],
            collaboration_status: "collaborative",
            languages: ["Python"],
            portfolio_customizations: {},
            portfolio_details: {
              role: "Team Contributor",
              timeline: "2 months",
              overview: "Overview",
              achievements: ["A1", "A2"],
              contributor_roles: [{ name: "alice", role: "Backend" }],
            },
          },
        ],
      },
    });

    getPortfolioActivityHeatmap.mockResolvedValue({
      ok: true,
      report_id: 9,
      usernames: ["alice@example.com"],
      days: 84,
      generated_at: "2026-04-02T00:00:00Z",
      aggregate: { total_commits: 8, total_lines_changed: 140, active_days: 5 },
      days_series: Array.from({ length: 84 }).map((_, i) => ({
        date: `2026-01-${String((i % 28) + 1).padStart(2, "0")}`,
        commits: i % 9 === 0 ? 2 : i % 5 === 0 ? 1 : 0,
        lines_changed: i % 9 === 0 ? 28 : i % 5 === 0 ? 9 : 0,
        intensity: i % 9 === 0 ? 4 : i % 5 === 0 ? 2 : 0,
      })),
    });

    updatePortfolioProject.mockResolvedValue({
      portfolio: {
        title: "Portfolio Report",
        portfolio_mode: "private",
        projects: [
          {
            project_name: "Proj A",
            summary: "Short summary",
            bullets: ["Implemented API layer"],
            collaboration_status: "collaborative",
            languages: ["Python"],
            portfolio_customizations: { custom_overview: "New custom overview" },
            portfolio_details: {
              role: "Team Contributor",
              timeline: "2 months",
              overview: "Overview",
              achievements: ["A1", "A2"],
              contributor_roles: [{ name: "alice", role: "Backend" }],
            },
          },
        ],
      },
    });

    publishPortfolio.mockResolvedValue({
      portfolio: {
        title: "Portfolio Report",
        portfolio_mode: "public",
        projects: [{
          project_name: "Proj A",
          summary: "Short summary",
          bullets: ["Implemented API layer"],
          collaboration_status: "collaborative",
          languages: ["Python"],
          portfolio_customizations: {},
          portfolio_details: { role: "Team Contributor", timeline: "2 months", overview: "Overview", achievements: ["A1", "A2"], contributor_roles: [{ name: "alice", role: "Backend" }] },
        }],
      },
    });

    unpublishPortfolio.mockResolvedValue({
      portfolio: {
        title: "Portfolio Report",
        portfolio_mode: "private",
        projects: [{
          project_name: "Proj A",
          summary: "Short summary",
          bullets: ["Implemented API layer"],
          collaboration_status: "collaborative",
          languages: ["Python"],
          portfolio_customizations: {},
          portfolio_details: { role: "Team Contributor", timeline: "2 months", overview: "Overview", achievements: ["A1", "A2"], contributor_roles: [{ name: "alice", role: "Backend" }] },
        }],
      },
    });
  });

  async function generatePortfolio(user) {
    render(<PortfolioPage />);
    await waitFor(() => screen.getByText("Saved Reports"));
    await user.click(screen.getByRole("button", { name: /my report/i }));
    await user.click(screen.getByRole("button", { name: /generate web portfolio/i }));
  }

  it("renders generated web portfolio in PortfolioPage", async () => {
    const user = userEvent.setup();
    await generatePortfolio(user);
    await waitFor(() => {
      expect(screen.getAllByText("Proj A").length).toBeGreaterThan(0);
      expect(screen.getByText(/Key contributions/i)).toBeInTheDocument();
    });
  });

  it("shows status banner updates during generation", async () => {
    const user = userEvent.setup();
    render(<PortfolioPage />);
    await waitFor(() => screen.getByText("Saved Reports"));
    await user.click(screen.getByRole("button", { name: /my report/i }));
    await user.click(screen.getByRole("button", { name: /generate web portfolio/i }));
    await waitFor(() => {
      expect(screen.getByTestId("portfolio-status-banner")).toHaveTextContent(/generated successfully/i);
    });
  });

  it("renders activity heatmap panel after portfolio generation", async () => {
    const user = userEvent.setup();
    await generatePortfolio(user);
    await waitFor(() => {
      expect(screen.getByTestId("portfolio-activity-heatmap")).toBeInTheDocument();
      expect(screen.getByText(/Activity Heatmap/i)).toBeInTheDocument();
    });
    expect(getPortfolioActivityHeatmap).toHaveBeenCalled();
  });

  it("date range filter updates rendered heatmap stats", async () => {
    const user = userEvent.setup();
    await generatePortfolio(user);

    const fromInputs = screen.getAllByLabelText(/From/i);
    const toInputs = screen.getAllByLabelText(/To/i);
    expect(fromInputs.length).toBeGreaterThan(0);
    expect(toInputs.length).toBeGreaterThan(0);

    await user.clear(fromInputs[0]);
    await user.type(fromInputs[0], "2026-01-15");
    await user.clear(toInputs[0]);
    await user.type(toInputs[0], "2026-01-25");

    await waitFor(() => {
      expect(screen.getByText(/Commits/i)).toBeInTheDocument();
    });
  });

  it("Open Public Page button is disabled before a portfolio is generated",async()=>{
    render(<PortfolioPage />);
    await waitFor(()=>screen.getByText("Saved Reports"));

    const btn = screen.getByRole("button", { name: /open public page/i });
    expect(btn).toBeDisabled();
  });

  it("Open Public Page button is disabled when portfolio is private",async()=>{
    const user=userEvent.setup();
    await generatePortfolio(user);

    // toggle to private — unpublishPortfolio returns portfolio_mode:"private", no public_url
    unpublishPortfolio.mockResolvedValueOnce({
      portfolio:{
        title:"Portfolio Report",
        portfolio_mode:"private",
        public_url:null,
        public_token:null,
        projects:[{
          project_name:"Proj A",
          summary:"",
          bullets:[],
          collaboration_status:"individual",
          languages:["Python"],
          portfolio_customizations:{},
          portfolio_details:{ role:"", timeline:"", overview:"", achievements:[], contributor_roles:[] },
        }],
      },
    });

    await user.click(screen.getByRole("button",{name:/toggle portfolio mode/i}));
    await waitFor(()=>expect(screen.getByTestId("portfolio-mode-badge")).toHaveTextContent(/private/i));

    expect(screen.getByRole("button",{name:/open public page/i})).toBeDisabled();
  });

  it("Open Public Page button is enabled and opens the correct URL when public",async()=>{
    const openSpy = vi.spyOn(window, "open").mockImplementation(()=>{});
    const user=userEvent.setup();
    await generatePortfolio(user);

    const btn = await screen.findByRole("button",{name:/open public page/i});
    expect(btn).not.toBeDisabled();

    await user.click(btn);
    expect(openSpy).toHaveBeenCalledWith(
      "http://localhost:8000/public/portfolio/my-report",
      "_blank",
      "noopener,noreferrer"
    );
    openSpy.mockRestore();
  });
});
