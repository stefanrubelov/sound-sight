import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { Dashboard } from "../src/pages/Dashboard";
import { Devices } from "../src/pages/Devices";
import { History } from "../src/pages/History";
import { Onboarding } from "../src/pages/Onboarding";
import { Reports } from "../src/pages/Reports";
import { Rules } from "../src/pages/Rules";
import { Settings } from "../src/pages/Settings";

// Mock the API and WebSocket so pages render without network
vi.mock("../src/api/client", () => ({
  getEvents: () =>
    Promise.resolve({ items: [], total: 0, limit: 20, offset: 0 }),
  getRules: () => Promise.resolve([]),
  getDevices: () => Promise.resolve([]),
  getUserProfile: () =>
    Promise.resolve({
      id: 1,
      home_description: null,
      enabled_classes: null,
      quiet_hours: null,
      notes: null,
    }),
  wsUrl: () => "ws://localhost:8000/ws/events",
}));

vi.mock("../src/hooks/useEvents", () => ({
  useEvents: () => ({ events: [], connected: false, error: null }),
}));

function renderPage(element: React.ReactElement) {
  return render(
    <MemoryRouter>
      <Routes>
        <Route path="*" element={element} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("Page smoke tests", () => {
  it("Dashboard renders heading", () => {
    renderPage(<Dashboard />);
    expect(
      screen.getByRole("heading", { name: /live dashboard/i }),
    ).toBeInTheDocument();
  });

  it("Dashboard shows empty state", () => {
    renderPage(<Dashboard />);
    expect(screen.getByText(/no events yet/i)).toBeInTheDocument();
  });

  it("History renders heading", () => {
    renderPage(<History />);
    expect(
      screen.getByRole("heading", { name: /event history/i }),
    ).toBeInTheDocument();
  });

  it("History renders filter fieldset", () => {
    renderPage(<History />);
    expect(
      screen.getByRole("group", { name: /filter events/i }),
    ).toBeInTheDocument();
  });

  it("Rules renders heading", () => {
    renderPage(<Rules />);
    expect(screen.getByRole("heading", { name: /rules/i })).toBeInTheDocument();
  });

  it("Rules renders NL text input", () => {
    renderPage(<Rules />);
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  it("Devices renders heading", () => {
    renderPage(<Devices />);
    expect(
      screen.getByRole("heading", { name: /devices/i }),
    ).toBeInTheDocument();
  });

  it("Settings renders heading", async () => {
    renderPage(<Settings />);
    expect(
      await screen.findByRole("heading", { name: /settings/i }),
    ).toBeInTheDocument();
  });

  it("Onboarding renders heading", () => {
    renderPage(<Onboarding />);
    expect(
      screen.getByRole("heading", { name: /onboarding/i }),
    ).toBeInTheDocument();
  });

  it("Onboarding renders textarea", () => {
    renderPage(<Onboarding />);
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  it("Reports renders heading", () => {
    renderPage(<Reports />);
    expect(
      screen.getByRole("heading", { name: /reports/i }),
    ).toBeInTheDocument();
  });

  it("Reports renders Daily and Weekly buttons", () => {
    renderPage(<Reports />);
    expect(screen.getByRole("button", { name: /daily/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /weekly/i })).toBeInTheDocument();
  });
});
