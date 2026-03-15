import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ResumePage from "../pages/ResumePage";

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
  listProjects,
  listReports,
  getReport,
  exportResume,
} from "../api/client";

describe("ResumePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    listProjects.mockResolvedValue({ projects: [{ id: 1, name: "Proj A" }] });
    listReports.mockResolvedValue({ reports: [{ id: 9, title: "My Report" }] });
    getReport.mockResolvedValue({ report: { id: 9, title: "My Report" } });
    exportResume.mockResolvedValue({ download_url: "/downloads/resume.pdf" });

    vi.stubGlobal("open", vi.fn());
  });

  it("exports resume for selected report", async () => {
    const user = userEvent.setup();

    render(<ResumePage />);

    await waitFor(() => screen.getByText("Saved Reports"));

    await user.click(screen.getByRole("button", { name: /my report/i }));
    await user.click(screen.getByRole("button", { name: /export resume pdf/i }));

    await waitFor(() => {
      expect(exportResume).toHaveBeenCalledWith({
        report_id: 9,
        template: "jake",
        output_name: "resume.pdf",
      });
      expect(window.open).toHaveBeenCalledWith(
        "http://localhost:8000/downloads/resume.pdf",
        "_blank"
      );
    });
  });
});