export interface SoundEvent {
  id: number;
  device_id: number;
  class_name: string;
  confidence: number;
  timestamp: string;
  duration: number;
  raw_features: string | null;
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
  enabled_classes: string | null;
  quiet_hours: string | null;
  notes: string | null;
}

export interface EventFilters {
  class_name?: string;
  room?: string;
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}

export interface PaginatedEvents {
  items: SoundEvent[];
  total: number;
  limit: number;
  offset: number;
}
