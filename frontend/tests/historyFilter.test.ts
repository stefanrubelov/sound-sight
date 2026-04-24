import { describe, expect, it } from "vitest";
import { applyFilters } from "../src/utils/filters";
import type { SoundEvent } from "../src/api/types";

const base: SoundEvent = {
  id: 1,
  device_id: 1,
  class_name: "dog_barking",
  confidence: 0.9,
  timestamp: "2026-04-20T10:00:00Z",
  duration: 1.0,
  raw_features: null,
  llm_summary: null,
};

const events: SoundEvent[] = [
  {
    ...base,
    id: 1,
    class_name: "dog_barking",
    timestamp: "2026-04-20T10:00:00Z",
  },
  {
    ...base,
    id: 2,
    class_name: "fire_alarm",
    timestamp: "2026-04-20T12:00:00Z",
  },
  { ...base, id: 3, class_name: "doorbell", timestamp: "2026-04-21T08:00:00Z" },
];

describe("applyFilters", () => {
  it("returns all events when no filters set", () => {
    expect(
      applyFilters(events, { class_name: "", from: "", to: "" }),
    ).toHaveLength(3);
  });

  it("filters by class_name", () => {
    const result = applyFilters(events, {
      class_name: "fire_alarm",
      from: "",
      to: "",
    });
    expect(result).toHaveLength(1);
    expect(result[0].class_name).toBe("fire_alarm");
  });

  it("filters by from date (inclusive)", () => {
    const result = applyFilters(events, {
      class_name: "",
      from: "2026-04-20T11:00:00Z",
      to: "",
    });
    expect(result).toHaveLength(2);
    expect(result.every((e) => e.timestamp >= "2026-04-20T11:00:00Z")).toBe(
      true,
    );
  });

  it("filters by to date (inclusive)", () => {
    const result = applyFilters(events, {
      class_name: "",
      from: "",
      to: "2026-04-20T23:59:59Z",
    });
    expect(result).toHaveLength(2);
  });

  it("combines class_name and date range", () => {
    const result = applyFilters(events, {
      class_name: "dog_barking",
      from: "2026-04-20T00:00:00Z",
      to: "2026-04-20T23:59:59Z",
    });
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe(1);
  });

  it("returns empty array when nothing matches", () => {
    const result = applyFilters(events, {
      class_name: "glass_breaking",
      from: "",
      to: "",
    });
    expect(result).toHaveLength(0);
  });
});
