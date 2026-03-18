import { render,screen,waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach,describe,expect,it,vi } from "vitest";
import PortfolioPage from "../pages/PortfolioPage";

vi.mock("../api/client",()=>({
  listProjects:vi.fn(),
  createReport:vi.fn(),
  listReports:vi.fn(),
  getReport:vi.fn(),
  exportResume:vi.fn(),
  exportPortfolio:vi.fn(),
  generatePortfolioDetailsForReport:vi.fn(),
  getPortfolio:vi.fn(),
  setPrivacyConsent:vi.fn(),
  updatePortfolioMode:vi.fn(),
  updatePortfolioProject:vi.fn(),
  publishPortfolio:vi.fn(),
  unpublishPortfolio:vi.fn(),
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
} from "../api/client";

describe("PortfolioPage web portfolio",()=>{
  beforeEach(()=>{
    vi.clearAllMocks();

    setPrivacyConsent.mockResolvedValue({ consent: true });
    listProjects.mockResolvedValue({ projects: [{ id: 1, name: "Proj A" }] });
    listReports.mockResolvedValue({ reports: [{ id: 9, title: "My Report", report_kind: "portfolio" }] });
    getReport.mockResolvedValue({ report: { id: 9, title: "My Report" } });
    generatePortfolioDetailsForReport.mockResolvedValue({
      ok: true,
      updated_project_names: ["Proj A"],
    });

    getPortfolio.mockResolvedValue({
      portfolio:{
        title:"Portfolio Report",
        portfolio_mode:"public",
        projects:[
          {
            project_name:"Proj A",
            summary:"Short summary",
            bullets:["Implemented API layer"],
            collaboration_status:"collaborative",
            languages:["Python"],
            portfolio_customizations:{},
            portfolio_details:{
              role:"Team Contributor",
              timeline:"2 months",
              overview:"Overview",
              achievements:["A1","A2"],
              contributor_roles:[{name:"alice",role:"Backend"}],
            },
          },
        ],
      },
    });

    updatePortfolioProject.mockResolvedValue({
      portfolio:{
        title:"Portfolio Report",
        portfolio_mode:"private",
        projects:[
          {
            project_name:"Proj A",
            summary:"Short summary",
            bullets:["Implemented API layer"],
            collaboration_status:"collaborative",
            languages:["Python"],
            portfolio_customizations:{custom_overview:"New custom overview"},
            portfolio_details:{
              role:"Team Contributor",
              timeline:"2 months",
              overview:"Overview",
              achievements:["A1","A2"],
              contributor_roles:[{name:"alice",role:"Backend"}],
            },
          },
        ],
      },
    });

    publishPortfolio.mockResolvedValue({
      portfolio:{
        title:"Portfolio Report",
        portfolio_mode:"public",
        projects:[
          {
            project_name:"Proj A",
            summary:"Short summary",
            bullets:["Implemented API layer"],
            collaboration_status:"collaborative",
            languages:["Python"],
            portfolio_customizations:{},
            portfolio_details:{
              role:"Team Contributor",
              timeline:"2 months",
              overview:"Overview",
              achievements:["A1","A2"],
              contributor_roles:[{name:"alice",role:"Backend"}],
            },
          },
        ],
      },
    });

    unpublishPortfolio.mockResolvedValue({
      portfolio:{
        title:"Portfolio Report",
        portfolio_mode:"private",
        projects:[
          {
            project_name:"Proj A",
            summary:"Short summary",
            bullets:["Implemented API layer"],
            collaboration_status:"collaborative",
            languages:["Python"],
            portfolio_customizations:{},
            portfolio_details:{
              role:"Team Contributor",
              timeline:"2 months",
              overview:"Overview",
              achievements:["A1","A2"],
              contributor_roles:[{name:"alice",role:"Backend"}],
            },
          },
        ],
      },
    });
  });

  async function generatePortfolio(user){
    render(<PortfolioPage />);
    await waitFor(()=>screen.getByText("Saved Reports"));
    await user.click(screen.getByRole("button",{name:/my report/i}));
    await user.click(screen.getByRole("button",{name:/generate web portfolio/i}));
  }

  it("renders generated web portfolio in PortfolioPage",async()=>{
    const user=userEvent.setup();
    await generatePortfolio(user);

    await waitFor(()=>{
      expect(screen.getByText("Portfolio Report")).toBeInTheDocument();
      expect(screen.getByText("Resume bullets")).toBeInTheDocument();
      expect(screen.getByText(/Key contributions/i)).toBeInTheDocument();
    });
  });

  it("starts in public mode and shows filters",async()=>{
    const user=userEvent.setup();
    await generatePortfolio(user);

    await waitFor(()=>{
      expect(screen.getByTestId("portfolio-mode-badge")).toHaveTextContent("public");
      expect(screen.getByLabelText(/Search projects/i)).toBeInTheDocument();
      expect(screen.queryByRole("button",{name:/Save Changes/i})).not.toBeInTheDocument();
    });
  });

  it("toggles to private mode and shows inline edit controls",async()=>{
    const user=userEvent.setup();
    await generatePortfolio(user);

    await user.click(screen.getByRole("button",{name:/toggle portfolio mode/i}));

    await waitFor(()=>{
      expect(unpublishPortfolio).toHaveBeenCalledWith(9);
      expect(screen.getByTestId("portfolio-mode-badge")).toHaveTextContent("private");
      expect(screen.getByRole("button",{name:/save changes/i})).toBeInTheDocument();
      expect(screen.getByLabelText(/Custom overview Proj A/i)).toBeInTheDocument();
    });
  });

  it("saves project customization via api in private mode",async()=>{
    const user=userEvent.setup();
    await generatePortfolio(user);

    await user.click(screen.getByRole("button",{name:/toggle portfolio mode/i}));
    const overview=await screen.findByLabelText(/Custom overview Proj A/i);
    await user.clear(overview);
    await user.type(overview,"New custom overview");
    await user.click(screen.getByRole("button",{name:/Save Changes/i}));

    await waitFor(()=>{
      expect(updatePortfolioProject).toHaveBeenCalledWith(
        9,
        "Proj A",
        expect.objectContaining({
          custom_overview:"New custom overview",
        })
      );
    });
  });

  it("toggles back to public mode from private",async()=>{
    const user=userEvent.setup();
    await generatePortfolio(user);

    await user.click(screen.getByRole("button",{name:/toggle portfolio mode/i}));
    await waitFor(()=>expect(screen.getByTestId("portfolio-mode-badge")).toHaveTextContent("private"));

    await user.click(screen.getByRole("button",{name:/toggle portfolio mode/i}));

    await waitFor(()=>{
      expect(publishPortfolio).toHaveBeenCalledWith(9);
      expect(screen.getByTestId("portfolio-mode-badge")).toHaveTextContent("public");
    });
  });
});
