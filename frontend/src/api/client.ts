import type {
  DashboardSummary,
  Device,
  EventFilters,
  OnboardingResponse,
  Rule,
  RuleCreate,
  SoundEvent,
  UserProfile,
} from "./types";

const BASE_URL =
  (import.meta.env.VITE_API_URL ?? "http://localhost:8000") + "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

// Events
export function getEvents(filters: EventFilters = {}): Promise<SoundEvent[]> {
  const params = new URLSearchParams();
  const { class_name, ...rest } = filters;
  if (class_name) params.set("class", class_name);
  for (const [k, v] of Object.entries(rest)) {
    if (v !== undefined && v !== "") params.set(k, String(v));
  }
  const qs = params.size ? `?${params}` : "";
  return request<SoundEvent[]>(`/events${qs}`);
}

export function getEvent(id: number): Promise<SoundEvent> {
  return request<SoundEvent>(`/events/${id}`);
}

// Rules
export function getRules(): Promise<Rule[]> {
  return request<Rule[]>("/rules");
}

export function createRule(body: RuleCreate): Promise<Rule> {
  return request<Rule>("/rules", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// Devices
export function getDevices(): Promise<Device[]> {
  return request<Device[]>("/devices");
}

// Settings / profile
export function getUserProfile(): Promise<UserProfile> {
  return request<UserProfile>("/settings");
}

export function updateUserProfile(
  body: Partial<UserProfile>,
): Promise<UserProfile> {
  return request<UserProfile>("/settings", {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function submitOnboarding(
  homeDescription: string,
): Promise<OnboardingResponse> {
  return request<OnboardingResponse>("/onboarding/profile", {
    method: "POST",
    body: JSON.stringify({ home_description: homeDescription }),
  });
}

// Dashboard
export function getDashboardSummary(): Promise<DashboardSummary> {
  return request<DashboardSummary>("/dashboard/summary");
}

// Reports
export function getDailyReport(): Promise<{ content: string }> {
  return request<{ content: string }>("/reports/daily");
}

export function getWeeklyReport(): Promise<{ content: string }> {
  return request<{ content: string }>("/reports/weekly");
}

// WebSocket URL helper
export function wsUrl(): string {
  const base = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
  return base.replace(/^http/, "ws") + "/ws/events";
}
