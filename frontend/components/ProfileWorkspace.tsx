"use client";

import React, { useState } from "react";
import { createProfile, type WorkspaceProfile } from "../lib/api";
import ProfileSummary from "./ProfileSummary";

type ProfileWorkspaceProps = {
  workspaceId: string;
};

export default function ProfileWorkspace({ workspaceId }: ProfileWorkspaceProps) {
  const [profile, setProfile] = useState<WorkspaceProfile | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleCreateProfile() {
    try {
      setIsLoading(true);
      setError("");
      const response = await createProfile(workspaceId);
      setProfile(response.profile);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate profile");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="stack">
      <article className="panel action-panel">
        <div>
          <h2>Profile Data</h2>
          <p>Generate table, column, and role metadata from the workspace database.</p>
        </div>
        <button type="button" onClick={handleCreateProfile} disabled={isLoading}>
          {isLoading ? "Generating..." : "Generate profile"}
        </button>
      </article>
      {error ? <p role="alert">{error}</p> : null}
      {profile ? <ProfileSummary profile={profile} /> : null}
    </section>
  );
}
