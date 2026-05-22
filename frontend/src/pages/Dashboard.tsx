import { useEffect, useMemo, useState } from "react";
import { EventsChart } from "../components/EventsChart";
import { getDashboardSummary } from "../api/client";
import type { DashboardSummary } from "../api/types";
import { useEvents } from "../hooks/useEvents";
import styles from "./Dashboard.module.css";

const SEVERITY_LABEL: Record<string, string> = {
  critical: "Critical",
  warn: "Warning",
  info: "Info",
  none: "—",
};

const ALL_SEVERITIES = ["critical", "warn", "info", "none"] as const;

export function Dashboard() {
  const { events, connected, error } = useEvents();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [hideUnknown, setHideUnknown] = useState(true);
  const [severities, setSeverities] = useState<Set<string>>(
    new Set(ALL_SEVERITIES),
  );
  const [minConfidence, setMinConfidence] = useState(0);

  function toggleSeverity(s: string) {
    setSeverities((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });
  }

  const visibleEvents = useMemo(
    () =>
      events.filter((ev) => {
        if (hideUnknown && ev.class_name === "unknown") return false;
        if (!severities.has(ev.severity)) return false;
        if (ev.confidence * 100 < minConfidence) return false;
        return true;
      }),
    [events, hideUnknown, severities, minConfidence],
  );

  useEffect(() => {
    getDashboardSummary()
      .catch(() => null)
      .then((s) => {
        if (s) setSummary(s);
      });
  }, []);

  return (
    <section aria-labelledby="dashboard-heading">
      <div className={styles.headerRow}>
        <h1 id="dashboard-heading">Live Dashboard</h1>
        <span
          className={[
            styles.dot,
            connected ? styles.online : styles.offline,
          ].join(" ")}
          role="status"
          aria-label={
            connected ? "WebSocket connected" : "WebSocket disconnected"
          }
        />
      </div>

      {summary && (
        <dl className={styles.stats}>
          <div className={styles.stat}>
            <dt>Events today</dt>
            <dd>{summary.events_today}</dd>
          </div>
          <div className={styles.stat}>
            <dt>Events this week</dt>
            <dd>{summary.events_this_week}</dd>
          </div>
          {summary.most_active_class && (
            <div className={styles.stat}>
              <dt>Most active</dt>
              <dd>{summary.most_active_class.replace(/_/g, " ")}</dd>
            </div>
          )}
          <div className={styles.stat}>
            <dt>Devices</dt>
            <dd>{summary.active_device_count}</dd>
          </div>
          <div className={styles.stat}>
            <dt>Rules</dt>
            <dd>{summary.active_rule_count}</dd>
          </div>
        </dl>
      )}

      <div className={styles.filterBar} role="group" aria-label="Event filters">
        <label className={styles.filterToggle}>
          <input
            type="checkbox"
            checked={hideUnknown}
            onChange={(e) => setHideUnknown(e.target.checked)}
          />
          Hide unknown
        </label>

        <div className={styles.filterGroup} role="group" aria-label="Severity">
          {ALL_SEVERITIES.map((s) => (
            <button
              key={s}
              type="button"
              className={[
                styles.filterPill,
                severities.has(s) ? styles[`pill_${s}`] : styles.pillOff,
              ].join(" ")}
              onClick={() => toggleSeverity(s)}
              aria-pressed={severities.has(s)}
            >
              {SEVERITY_LABEL[s]}
            </button>
          ))}
        </div>

        <label className={styles.filterSlider}>
          Min confidence: {minConfidence}%
          <input
            type="range"
            min={0}
            max={100}
            value={minConfidence}
            onChange={(e) => setMinConfidence(Number(e.target.value))}
          />
        </label>
      </div>

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      {visibleEvents.length === 0 ? (
        <p className={styles.empty}>
          {events.length === 0
            ? "No events yet — waiting for audio…"
            : "No events match the current filters."}
        </p>
      ) : (
        <ul className={styles.grid} role="list" aria-label="Recent events">
          {visibleEvents.map((ev) => (
            <li
              key={`${ev.event_id}-${ev.timestamp}`}
              className={[styles.card, styles[ev.severity] ?? ""].join(" ")}
              aria-label={`${ev.class_name} detected, ${SEVERITY_LABEL[ev.severity]} severity`}
            >
              <div className={styles.cardHeader}>
                <strong className={styles.className}>
                  {ev.class_name.replace(/_/g, " ")}
                </strong>
                <span className={styles.badge} aria-hidden="true">
                  {SEVERITY_LABEL[ev.severity]}
                </span>
              </div>
              <dl className={styles.meta}>
                <div>
                  <dt>Confidence</dt>
                  <dd>{(ev.confidence * 100).toFixed(1)}%</dd>
                </div>
                <div>
                  <dt>LED</dt>
                  <dd>
                    <span
                      className={styles.swatch}
                      style={{ background: ev.led_color }}
                      aria-label={ev.led_color}
                    />
                  </dd>
                </div>
                <div>
                  <dt>Vibration</dt>
                  <dd>{ev.vibration_pattern}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      )}

      <EventsChart />
    </section>
  );
}
