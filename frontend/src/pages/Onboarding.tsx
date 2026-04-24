import { useState } from "react";
import { submitOnboarding } from "../api/client";
import type { UserProfile } from "../api/types";
import styles from "./Onboarding.module.css";

export function Onboarding() {
  const [description, setDescription] = useState("");
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!description.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await submitOnboarding(description);
      setProfile(result);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section aria-labelledby="onboarding-heading">
      <h1 id="onboarding-heading">Home Onboarding</h1>
      <p className={styles.intro}>
        Describe your home and living situation. SoundSight will suggest a sound
        monitoring profile tailored to you.
      </p>

      <form
        onSubmit={handleSubmit}
        className={styles.form}
        aria-label="Home description form"
      >
        <label htmlFor="home-desc">Describe your home</label>
        <textarea
          id="home-desc"
          className={styles.textarea}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={5}
          placeholder='e.g. "I live alone in a flat. I have a dog. I want to be alerted to fire alarms and doorbells."'
          aria-describedby="desc-hint"
        />
        <p id="desc-hint" className={styles.hint}>
          The more detail you provide, the better the suggested profile.
        </p>
        <button
          type="submit"
          disabled={loading || !description.trim()}
          className={styles.btn}
        >
          {loading ? "Generating profile…" : "Generate profile"}
        </button>
      </form>

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      {profile && (
        <div
          className={styles.result}
          aria-label="Generated profile"
          aria-live="polite"
        >
          <h2>Your suggested profile</h2>
          <dl className={styles.profileDl}>
            <div>
              <dt>Enabled classes</dt>
              <dd>{profile.enabled_classes ?? "All"}</dd>
            </div>
            <div>
              <dt>Quiet hours</dt>
              <dd>{profile.quiet_hours ?? "None"}</dd>
            </div>
            {profile.notes && (
              <div>
                <dt>Notes</dt>
                <dd>{profile.notes}</dd>
              </div>
            )}
          </dl>
        </div>
      )}
    </section>
  );
}
