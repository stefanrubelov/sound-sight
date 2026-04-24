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
    </section>
  );
}
