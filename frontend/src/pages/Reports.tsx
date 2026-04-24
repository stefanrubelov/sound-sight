import { useState } from "react";
import { getDailyReport, getWeeklyReport } from "../api/client";
import styles from "./Reports.module.css";

type ReportType = "daily" | "weekly";

export function Reports() {
  const [reportType, setReportType] = useState<ReportType>("daily");
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function fetchReport(type: ReportType) {
    setReportType(type);
    setLoading(true);
    setError(null);
    try {
      const res =
        type === "daily" ? await getDailyReport() : await getWeeklyReport();
      setContent(res.content);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section aria-labelledby="reports-heading">
      <h1 id="reports-heading">Reports</h1>

      <div className={styles.tabs} role="group" aria-label="Report type">
        <button
          className={[
            styles.tab,
            reportType === "daily" ? styles.active : "",
          ].join(" ")}
          onClick={() => fetchReport("daily")}
          aria-pressed={reportType === "daily"}
        >
          Daily
        </button>
        <button
          className={[
            styles.tab,
            reportType === "weekly" ? styles.active : "",
          ].join(" ")}
          onClick={() => fetchReport("weekly")}
          aria-pressed={reportType === "weekly"}
        >
          Weekly
        </button>
      </div>

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      {loading && <p aria-live="polite">Generating report…</p>}

      {!loading && !error && content === null && (
        <p className={styles.empty}>
          Select a report type above to generate it.
        </p>
      )}

      {content && !loading && (
        <article
          className={styles.report}
          aria-label={`${reportType} report`}
          aria-live="polite"
        >
          <pre className={styles.pre}>{content}</pre>
        </article>
      )}
    </section>
  );
}
