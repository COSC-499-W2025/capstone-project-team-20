import { render, screen, fireEvent } from "@testing-library/react";
import Help from "./Help";

describe("Help Page", () => {
  test("renders help page title", () => {
    render(<Help />);
    expect(screen.getByText("Help & Info")).toBeInTheDocument();
  });

  test("renders section titles", () => {
    render(<Help />);

    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.getByText("Uploading a Project")).toBeInTheDocument();
    expect(screen.getByText("Running an Analysis")).toBeInTheDocument();
    expect(screen.getByText("Understanding Results")).toBeInTheDocument();
    expect(screen.getByText("Badges")).toBeInTheDocument();
    expect(screen.getByText("Troubleshooting")).toBeInTheDocument();
    expect(screen.getByText("Privacy & Security")).toBeInTheDocument();
  });

  test("sections are collapsed by default", () => {
    render(<Help />);

    expect(
      screen.queryByText(/Project Analyzer evaluates software projects/i)
    ).not.toBeInTheDocument();
  });

  test("clicking a section expands its content", () => {
    render(<Help />);

    const overviewButton = screen.getByRole("button", { name: /Overview/i });

    fireEvent.click(overviewButton);

    expect(
      screen.getByText(/Project Analyzer evaluates software projects/i)
    ).toBeInTheDocument();
  });

  test("clicking again collapses the section", () => {
    render(<Help />);

    const overviewButton = screen.getByRole("button", { name: /Overview/i });

    fireEvent.click(overviewButton);
    expect(
      screen.getByText(/Project Analyzer evaluates software projects/i)
    ).toBeInTheDocument();

    fireEvent.click(overviewButton);
    expect(
      screen.queryByText(/Project Analyzer evaluates software projects/i)
    ).not.toBeInTheDocument();
  });

  test("arrow indicator changes when toggled", () => {
    render(<Help />);

    const overviewButton = screen.getByRole("button", { name: /Overview/i });

    expect(overviewButton).toHaveTextContent("▼");

    fireEvent.click(overviewButton);
    expect(overviewButton).toHaveTextContent("▲");
  });
});