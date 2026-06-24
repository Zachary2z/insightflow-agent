import React from "react";
import type { ChartArtifact } from "../lib/api";

type ChartArtifactGalleryProps = {
  artifacts?: ChartArtifact[];
};

export default function ChartArtifactGallery({ artifacts = [] }: ChartArtifactGalleryProps) {
  const displayable = artifacts.filter((artifact) => artifact.url || artifact.path);

  return (
    <article className="panel chart-gallery">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Charts</p>
          <h3>图表</h3>
        </div>
      </div>
      {displayable.length ? (
        <div className="chart-list">
          {displayable.map((artifact, index) => (
            <figure key={`${artifact.path || artifact.url}-${index}`} className="chart-artifact">
              {artifact.url ? <img src={artifact.url} alt={artifact.title || "分析图表"} /> : null}
              <figcaption>
                <strong>{artifact.title || "分析图表"}</strong>
                {artifact.business_annotation ? <span>{artifact.business_annotation}</span> : null}
                {artifact.path ? <code>{artifact.path}</code> : null}
              </figcaption>
            </figure>
          ))}
        </div>
      ) : (
        <p>暂无图表。</p>
      )}
    </article>
  );
}
