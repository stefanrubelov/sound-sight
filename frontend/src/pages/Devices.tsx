import { useEffect, useState } from "react";
import { getDevices } from "../api/client";
import type { Device } from "../api/types";
import styles from "./Devices.module.css";

export function Devices() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getDevices()
      .then((data) => {
        if (!active) return;
        setDevices(data);
        setLoading(false);
      })
      .catch((e: Error) => {
        if (!active) return;
        setError(e.message);
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <section aria-labelledby="devices-heading">
      <h1 id="devices-heading">Devices</h1>

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      {loading && <p aria-live="polite">Loading devices…</p>}

      {!loading && devices.length === 0 && !error && (
        <p className={styles.empty}>
          No devices registered yet. Flash the firmware on your ESP32 and it
          will appear here after first boot.
        </p>
      )}

      {devices.length > 0 && (
        <ul className={styles.grid} role="list">
          {devices.map((d) => (
            <li key={d.id} className={styles.card}>
              <h2 className={styles.name}>{d.name}</h2>
              <dl className={styles.meta}>
                <div>
                  <dt>Room</dt>
                  <dd>{d.room}</dd>
                </div>
                <div>
                  <dt>Registered</dt>
                  <dd>{new Date(d.registered_at).toLocaleDateString()}</dd>
                </div>
                <div>
                  <dt>Last seen</dt>
                  <dd>
                    {d.last_seen
                      ? new Date(d.last_seen).toLocaleString()
                      : "Never"}
                  </dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
