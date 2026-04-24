import { useEffect, useState } from "react";
import { getEvents } from "../api/client";
import type { EventFilters, SoundEvent } from "../api/types";
import { type HistoryFilters } from "../utils/filters";
import styles from "./History.module.css";

const CLASS_OPTIONS = [
  "",
  "fire_alarm",
  "doorbell",
  "glass_breaking",
  "baby_crying",
  "dog_barking",
  "timer_beep",
  "water_running",
  "unknown",
];

export function History() {
  const [filters, setFilters] = useState<HistoryFilters>({
    class_name: "",
    from: "",
    to: "",
  });
  const [events, setEvents] = useState<SoundEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const limit = 20;

  function buildApiFilters(): EventFilters {
    const f: EventFilters = { limit, offset };
    if (filters.class_name) f.class_name = filters.class_name;
    if (filters.from) f.from = filters.from;
    if (filters.to) f.to = filters.to;
    return f;
  }

  useEffect(() => {
    let active = true;
    getEvents(buildApiFilters())
      .then((res) => {
        if (!active) return;
        setEvents(res.items ?? []);
        setTotal(res.total ?? 0);
        setLoading(false);
        setError(null);
      })
      .catch((e: Error) => {
        if (!active) return;
        setError(e.message);
        setLoading(false);
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, offset]);

  function handleFilterChange(key: keyof HistoryFilters, value: string) {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setOffset(0);
  }

  return (
    <section aria-labelledby="history-heading">
      <h1 id="history-heading">Event History</h1>

      <fieldset className={styles.filters}>
        <legend>Filter events</legend>

        <label htmlFor="filter-class">Sound class</label>
        <select
          id="filter-class"
          value={filters.class_name}
          onChange={(e) => handleFilterChange("class_name", e.target.value)}
        >
          {CLASS_OPTIONS.map((c) => (
            <option key={c} value={c}>
              {c || "All classes"}
            </option>
          ))}
        </select>

        <label htmlFor="filter-from">From</label>
        <input
          id="filter-from"
          type="datetime-local"
          value={filters.from}
          onChange={(e) => handleFilterChange("from", e.target.value)}
        />

        <label htmlFor="filter-to">To</label>
        <input
          id="filter-to"
          type="datetime-local"
          value={filters.to}
          onChange={(e) => handleFilterChange("to", e.target.value)}
        />
      </fieldset>

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      {loading && <p aria-live="polite">Loading…</p>}

      {!loading && events.length === 0 && !error && (
        <p className={styles.empty}>No events match the current filters.</p>
      )}

      {events.length > 0 && (
        <>
          <p className={styles.count} aria-live="polite">
            Showing {offset + 1}–{Math.min(offset + limit, total)} of {total}
          </p>
          <table className={styles.table} aria-label="Event history">
            <thead>
              <tr>
                <th scope="col">Time</th>
                <th scope="col">Class</th>
                <th scope="col">Confidence</th>
                <th scope="col">Duration (s)</th>
                <th scope="col">Device</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.id}>
                  <td>{new Date(e.timestamp).toLocaleString()}</td>
                  <td>{e.class_name.replace(/_/g, " ")}</td>
                  <td>{(e.confidence * 100).toFixed(1)}%</td>
                  <td>{e.duration.toFixed(2)}</td>
                  <td>{e.device_id}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div
            className={styles.pagination}
            role="navigation"
            aria-label="Pagination"
          >
            <button
              onClick={() => setOffset((o) => Math.max(0, o - limit))}
              disabled={offset === 0}
              aria-label="Previous page"
            >
              ← Previous
            </button>
            <button
              onClick={() => setOffset((o) => o + limit)}
              disabled={offset + limit >= total}
              aria-label="Next page"
            >
              Next →
            </button>
          </div>
        </>
      )}
    </section>
  );
}
