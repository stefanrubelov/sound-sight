import type { SoundEvent } from "../api/types";

export interface HistoryFilters {
  class_name: string;
  from: string;
  to: string;
}

export function applyFilters(
  events: SoundEvent[],
  filters: HistoryFilters,
): SoundEvent[] {
  return events.filter((e) => {
    if (filters.class_name && e.class_name !== filters.class_name) return false;
    if (filters.from && e.timestamp < filters.from) return false;
    if (filters.to && e.timestamp > filters.to) return false;
    return true;
  });
}
