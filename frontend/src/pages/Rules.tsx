import { useEffect, useState } from "react";
import { createRule, getRules } from "../api/client";
import type { Rule } from "../api/types";
import styles from "./Rules.module.css";

export function Rules() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [nlText, setNlText] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getRules()
      .then((data) => {
        if (!active) return;
        setRules(data);
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

  async function handleNlSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!nlText.trim()) return;
    setSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      const rule = await createRule({ source_text: nlText });
      setRules((prev) => [rule, ...prev]);
      setNlText("");
      setSuccess("Rule created successfully.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section aria-labelledby="rules-heading">
      <h1 id="rules-heading">Rules</h1>

      <form
        onSubmit={handleNlSubmit}
        className={styles.form}
        aria-label="Create rule from natural language"
      >
        <label htmlFor="nl-input">Describe a rule in plain English</label>
        <textarea
          id="nl-input"
          className={styles.textarea}
          value={nlText}
          onChange={(e) => setNlText(e.target.value)}
          rows={3}
          placeholder='e.g. "Vibrate continuously if fire alarm detected after 22:00"'
          aria-describedby="nl-hint"
        />
        <p id="nl-hint" className={styles.hint}>
          The AI will parse this into a structured rule.
        </p>
        <button
          type="submit"
          disabled={submitting || !nlText.trim()}
          className={styles.btn}
        >
          {submitting ? "Creating…" : "Create rule"}
        </button>
      </form>

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      {success && (
        <p className={styles.success} role="status">
          {success}
        </p>
      )}

      {loading && <p aria-live="polite">Loading rules…</p>}

      {!loading && rules.length === 0 && !error && (
        <p className={styles.empty}>No rules yet.</p>
      )}

      {rules.length > 0 && (
        <table className={styles.table} aria-label="Active rules">
          <thead>
            <tr>
              <th scope="col">Trigger</th>
              <th scope="col">Time window</th>
              <th scope="col">Priority</th>
              <th scope="col">Alert</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((r) => (
              <tr key={r.id}>
                <td>{r.trigger}</td>
                <td>
                  {r.time_start && r.time_end
                    ? `${r.time_start} – ${r.time_end}`
                    : "Always"}
                </td>
                <td>{r.priority}</td>
                <td>{r.alert_type}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
