import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Reports from "../pages/Reports";

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
}));

import {
  listProjects, listReports, getReport, generatePortfolioDetailsForReport, getPortfolio, setPrivacyConsent
} from "../api/client";

describe("Reports web portfolio", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setPrivacyConsent.mockResolvedValue({ consent: true });
    listProjects.mockResolvedValue({ projects: [{ id: 1, name: "Proj A" }] });
    listReports.mockResolvedValue({ reports: [{ id: 9, title: "My Report" }] });
    getReport.mockResolvedValue({ report: { id: 9, title: "My Report" } });
    generatePortfolioDetailsForReport.mockResolvedValue({ ok: true, updated_project_names: ["Proj A"] });
    getPortfolio.mockResolvedValue({
      portfolio: {
        title: "Portfolio Report",
        projects: [{
          project_name: "Proj A",
          summary: "Short summary",
          bullets: ["Implemented API layer"],
          collaboration_status: "collaborative",
          portfolio_details: { role: "Team Contributor", timeline: "2 months", overview: "Overview", contributor_roles: [{ name: "alice", role: "Backend" }] }
        }]
      }
    });
  });

  it("renders generated web portfolio in Reports", async () => {
    const user = userEvent.setup();
    render(<Reports />);
    await waitFor(() => screen.getByText("Saved Reports"));
    await user.click(screen.getByRole("button", { name: /my report/i }));
    await user.click(screen.getByRole("button", { name: /generate web portfolio/i }));
    await waitFor(() => {
      expect(screen.getByText("Portfolio Report")).toBeInTheDocument();
      expect(screen.getByText("Resume bullets")).toBeInTheDocument();
      expect(screen.getByText(/Key contributions/i)).toBeInTheDocument();
    });
  });
});
