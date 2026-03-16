import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ResumePage from "../pages/ResumePage";

vi.mock("../api/client", () => ({
  listProjects: vi.fn(),
  createReport: vi.fn(),
  listReports: vi.fn(),
  getReport: vi.fn(),
  deleteReport: vi.fn(),
  exportResume: vi.fn(),
  setPrivacyConsent: vi.fn(),
  getResumeContext: vi.fn(),
  patchReportProject: vi.fn(),
  configSet: vi.fn(),
}));

import {
  listProjects,
  listReports,
  getReport,
  deleteReport,
  exportResume,
  getResumeContext,
} from "../api/client";

const MOCK_REPORT = { id: 9, title: "My Report", notes: "SE roles" };

const MOCK_CTX = {
  name: "Dale Smith",
  phone: "250-555-0100",
  email: "dale@example.com",
  github_url: "https://github.com/dale",
  github_display: "github.com/dale",
  linkedin_url: "",
  linkedin_display: "",
  education: [],
  experience: [],
  projects: [
    { name: "Cool Project", stack: "Python", dates: "Jan 2024", bullets: ["Did a thing"] },
  ],
  skills: { Languages: ["Python"] },
};

describe("ResumePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    listProjects.mockResolvedValue({ projects: [{ id: 1, name: "Proj A" }] });
    listReports.mockResolvedValue({ reports: [MOCK_REPORT] });
    getReport.mockResolvedValue({ report: MOCK_REPORT });
    getResumeContext.mockResolvedValue(MOCK_CTX);
    exportResume.mockResolvedValue({ download_url: "/downloads/resume.pdf" });
    deleteReport.mockResolvedValue(undefined);

    vi.stubGlobal("open", vi.fn());
  });

  it("loads and displays saved reports on mount", async () => {
    render(<ResumePage />);

    await waitFor(() => {
      expect(screen.getByText("My Report")).toBeInTheDocument();
    });
  });

  it("loads preview context when a report is selected", async () => {
    const user = userEvent.setup();
    render(<ResumePage />);

    await waitFor(() => screen.getByText("My Report"));
    await user.click(screen.getByRole("button", { name: /my report/i }));

    await waitFor(() => {
      expect(getResumeContext).toHaveBeenCalledWith(9);
      expect(screen.getByText("Dale Smith")).toBeInTheDocument();
    });
  });

  it("exports resume for selected report", async () => {
    const user = userEvent.setup();
    render(<ResumePage />);

    await waitFor(() => screen.getByText("My Report"));
    await user.click(screen.getByRole("button", { name: /my report/i }));
    await waitFor(() => screen.getByText("Dale Smith"));

    await user.click(screen.getByRole("button", { name: /export pdf/i }));

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

  it("shows confirm modal when trash icon is clicked", async () => {
    const user = userEvent.setup();
    render(<ResumePage />);

    await waitFor(() => screen.getByText("My Report"));
    await user.click(screen.getByTitle("Delete report"));

    expect(screen.getByText("Delete report?")).toBeInTheDocument();
    expect(screen.getByText(/permanently delete/i)).toBeInTheDocument();
  });

  it("dismisses modal without deleting when go back is clicked", async () => {
    const user = userEvent.setup();
    render(<ResumePage />);

    await waitFor(() => screen.getByText("My Report"));
    await user.click(screen.getByTitle("Delete report"));
    await user.click(screen.getByRole("button", { name: /go back/i }));

    expect(deleteReport).not.toHaveBeenCalled();
    expect(screen.queryByText("Delete report?")).not.toBeInTheDocument();
  });

  it("deletes report and removes it from list on confirm", async () => {
    const user = userEvent.setup();
    render(<ResumePage />);

    await waitFor(() => screen.getByText("My Report"));
    await user.click(screen.getByTitle("Delete report"));
    await user.click(screen.getByRole("button", { name: /yes, delete/i }));

    await waitFor(() => {
      expect(deleteReport).toHaveBeenCalledWith(9);
      expect(screen.queryByText("My Report")).not.toBeInTheDocument();
    });
  });
});
