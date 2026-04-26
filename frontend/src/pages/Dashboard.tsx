import { useEffect, useState } from "react";
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

export function Dashboard() {
  const { events, connected, error } = useEvents();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);

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

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      {events.length === 0 ? (
        <p className={styles.empty}>No events yet — waiting for audio…</p>
      ) : (
        <ul className={styles.grid} role="list" aria-label="Recent events">
          {events.map((ev) => (
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
