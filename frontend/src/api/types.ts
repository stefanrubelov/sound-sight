export interface SoundEvent {
  id: number;
  device_id: number;
  class_name: string;
  confidence: number;
  timestamp: string;
  duration: number;
  llm_summary: string | null;
}

export interface ClassifyResponse {
  event_id: number;
  class_name: string;
  confidence: number;
  severity: string;
  led_color: string;
  vibration_pattern: string;
  device_id: number;
  timestamp?: string;
}

export interface Rule {
  id: number;
  trigger: string;
  time_start: string | null;
  time_end: string | null;
  priority: string;
  alert_type: string;
  source_text: string | null;
  created_at: string;
}

export interface RuleCreate {
  trigger?: string;
  time_start?: string;
  time_end?: string;
  priority?: string;
  alert_type?: string;
  source_text?: string;
}

export interface Device {
  id: number;
  name: string;
  room: string;
  registered_at: string;
  last_seen: string | null;
}

export interface UserProfile {
  id: number;
  home_description: string | null;
  enabled_classes: string[] | null;
  quiet_hours: { start: string; end: string } | null;
  notes: string | null;
}

export interface OnboardingResponse {
  enabled_classes: string[];
  priorities: Record<string, string>;
  quiet_hours_default: { start: string; end: string } | null;
  profile_id: number;
}

export interface DashboardSummary {
  events_today: number;
  events_this_week: number;
  most_active_class: string | null;
  active_device_count: number;
  active_rule_count: number;
}

export interface EventFilters {
  class_name?: string;
  room?: string;
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}
