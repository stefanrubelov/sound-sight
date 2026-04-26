import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getEvents } from "../api/client";
import type { SoundEvent } from "../api/types";
import styles from "./EventsChart.module.css";

interface ClassCount {
  name: string;
  count: number;
}

function aggregate(events: SoundEvent[]): ClassCount[] {
  const counts: Record<string, number> = {};
  for (const e of events) {
    counts[e.class_name] = (counts[e.class_name] ?? 0) + 1;
  }
  return Object.entries(counts)
    .map(([name, count]) => ({ name: name.replace(/_/g, " "), count }))
    .sort((a, b) => b.count - a.count);
}

export function EventsChart() {
  const [data, setData] = useState<ClassCount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const from = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
    getEvents({ limit: 500, from })
      .then((events) => {
        setData(aggregate(events));
        setLoading(false);
      })
      .catch((e: Error) => {
        setError(e.message);
        setLoading(false);
      });
  }, []);

  if (loading) return <p className={styles.state}>Loading chart…</p>;
  if (error) return null;
  if (data.length === 0)
    return <p className={styles.state}>No events in the last 24 hours yet.</p>;

  return (
    <div className={styles.wrap}>
      <h2 className={styles.title}>Events last 24 h — by class</h2>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart
          data={data}
          margin={{ top: 4, right: 16, left: 0, bottom: 4 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 12, fill: "var(--text)" }}
            tickLine={false}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: 12, fill: "var(--text)" }}
            tickLine={false}
            axisLine={false}
            width={28}
          />
          <Tooltip
            contentStyle={{
              background: "var(--surface, var(--bg))",
              border: "1px solid var(--border)",
              borderRadius: 6,
              fontSize: 13,
            }}
            cursor={{ fill: "var(--accent-bg)" }}
          />
          <Bar dataKey="count" fill="var(--accent)" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
