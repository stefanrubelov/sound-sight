import { useEffect, useState } from "react";
import { getUserProfile, updateUserProfile } from "../api/client";
import type { UserProfile } from "../api/types";
import styles from "./Settings.module.css";

export function Settings() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [notes, setNotes] = useState("");

  useEffect(() => {
    let active = true;
    getUserProfile()
      .then((p) => {
        if (!active) return;
        setProfile(p);
        setNotes(p.notes ?? "");
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

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!profile) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateUserProfile({ notes });
      setProfile(updated);
      setSuccess("Settings saved.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p aria-live="polite">Loading settings…</p>;

  return (
    <section aria-labelledby="settings-heading">
      <h1 id="settings-heading">Settings</h1>

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

      {profile && (
        <form
          onSubmit={handleSave}
          className={styles.form}
          aria-label="User settings"
        >
          <div className={styles.field}>
            <label>Enabled sound classes</label>
            <p className={styles.value}>
              {profile.enabled_classes ?? "All classes enabled"}
            </p>
          </div>

          <div className={styles.field}>
            <label>Quiet hours</label>
            <p className={styles.value}>
              {profile.quiet_hours ?? "None configured"}
            </p>
          </div>

          <div className={styles.field}>
            <label htmlFor="notes-input">Notes</label>
            <textarea
              id="notes-input"
              className={styles.textarea}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={4}
              placeholder="Any personal notes about your setup…"
            />
          </div>

          <button type="submit" disabled={saving} className={styles.btn}>
            {saving ? "Saving…" : "Save settings"}
          </button>
        </form>
      )}
    </section>
  );
}
