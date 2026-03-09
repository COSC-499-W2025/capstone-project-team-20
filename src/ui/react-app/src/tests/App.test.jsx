import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";

vi.mock("../Settings", () => ({ default: () => <div>Settings View</div> }));
vi.mock("../ProfileSetup", () => ({ default: () => <div>Profile Setup</div> }));

vi.mock("../api/client", () => ({
  listProjects: vi.fn(),
  getProject: vi.fn(),
  listSkills: vi.fn(),
  getBadgeProgress: vi.fn(),
  getYearlyWrapped: vi.fn(),
  getConfig: vi.fn(),
  setPrivacyConsent: vi.fn(),
  getPrivacyConsent: vi.fn(),
  createReport: vi.fn(),
  exportResume: vi.fn(),
  uploadProjectZip: vi.fn(),
  uploadProjectFromPath: vi.fn(),
  clearProjects: vi.fn(),
  generatePortfolioDetailsForReport: vi.fn(),
  getPortfolio: vi.fn(),
}));

import {
  listProjects,
  getConfig,
  setPrivacyConsent,
  createReport,
  generatePortfolioDetailsForReport,
  getPortfolio,
} from "../api/client";

describe("Portfolio rendering", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getConfig.mockResolvedValue({ name: "Ada", email: "ada@test.com", phone: "555" });
    setPrivacyConsent.mockResolvedValue({ consent: true });
    listProjects.mockResolvedValue({ projects: [{ id: 1, name: "Proj A" }] });
    createReport.mockResolvedValue({ report: { id: 9 } });
    generatePortfolioDetailsForReport.mockResolvedValue({ ok: true, updated_project_names: ["Proj A"] });
    getPortfolio.mockResolvedValue({
      ok: true,
      portfolio: {
        title: "Portfolio Report",
        projects: [
          {
            project_name: "Proj A",
            summary: "Short polished summary",
            bullets: ["Implemented API layer", "Added tests"],
            collaboration_status: "collaborative",
            portfolio_details: {
              role: "Team Contributor (Team of 3)",
              timeline: "2 months",
              technologies: "Python",
              overview: "Overview text",
              achievements: [],
              contributor_roles: [
                { name: "alice", role: "Backend", confidence_pct: 88 },
                { name: "bob", role: "Contributor", confidence_pct: 0 },
              ],
            },
          },
        ],
      },
    });
  });

  it("shows summary pills and expanded first accordion project", async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => screen.getByRole("button", { name: /portfolio/i }));
    await user.click(screen.getByRole("button", { name: /portfolio/i }));
    await user.click(screen.getByRole("button", { name: /generate web portfolio/i }));

    await waitFor(() => {
      expect(screen.getByText("Portfolio Report")).toBeInTheDocument();
      expect(screen.getByText("Resume bullets")).toBeInTheDocument();
      expect(screen.getByText("Team projects")).toBeInTheDocument();
      expect(screen.getByText(/Key contributions/i)).toBeInTheDocument();
      expect(screen.getByText("alice")).toBeInTheDocument();
      expect(screen.getByText("Backend")).toBeInTheDocument();
    });

    const projectButtons = screen.getAllByRole("button", { name: /projects/i });
    expect(projectButtons.length).toBeGreaterThan(0);

    const portfolioContainer = screen.getByText("Portfolio Report").closest("section");
    expect(portfolioContainer).toBeTruthy();
    expect(within(portfolioContainer).getByText("Projects")).toBeInTheDocument();
  });

  it("collapses and expands project card", async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => screen.getByRole("button", { name: /portfolio/i }));
    await user.click(screen.getByRole("button", { name: /portfolio/i }));
    await user.click(screen.getByRole("button", { name: /generate web portfolio/i }));

    await waitFor(() => expect(screen.getByText(/Key contributions/i)).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /collapse/i }));
    expect(screen.queryByText(/Key contributions/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /expand/i }));
    expect(screen.getByText(/Key contributions/i)).toBeInTheDocument();
  });
});
