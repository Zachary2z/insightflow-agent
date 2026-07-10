"use client";

import React, { useState } from "react";
import { createProfile, type WorkspaceProfile } from "../lib/api";
import ProductCard from "./ProductCard";
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
      setError(err instanceof Error ? err.message : "字段画像生成失败");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="stack">
      <ProductCard className="action-panel">
        <div>
          <p className="product-eyebrow">字段准备</p>
          <h2>生成字段画像</h2>
          <p className="panel-help">读取当前工作区数据库，生成表、字段、行数和候选角色信息。</p>
        </div>
        <button type="button" onClick={handleCreateProfile} disabled={isLoading}>
          {isLoading ? "生成中…" : "生成字段画像"}
        </button>
      </ProductCard>
      {error ? <p role="alert">{error}</p> : null}
      {profile ? <ProfileSummary profile={profile} /> : null}
    </section>
  );
}
