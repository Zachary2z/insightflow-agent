import React from "react";
import { resolveApiUrl, type ChartArtifact } from "../lib/api";

type ChartArtifactGalleryProps = {
  artifacts?: ChartArtifact[];
};

export default function ChartArtifactGallery({ artifacts = [] }: ChartArtifactGalleryProps) {
  const displayable = artifacts.filter((artifact) => artifact.url || artifact.path);

  return (
    <article className="panel chart-gallery">
      <div className="section-heading">
        <div>
          <p className="product-eyebrow">Charts</p>
          <h3>图表</h3>
          <p className="panel-help">图表在业务结论和证据之后展示，便于快速复核趋势和对比。</p>
        </div>
      </div>
      {displayable.length ? (
        <div className="chart-list">
          {displayable.map((artifact, index) => {
            const url = resolveApiUrl(artifact.url || "");
            return (
              <figure key={`${artifact.path || artifact.url}-${index}`} className="chart-artifact">
                {url ? <img src={url} alt={artifact.title || "分析图表"} /> : null}
                <figcaption>
                  <strong>{artifact.title || "分析图表"}</strong>
                  {!url ? <span>图表已生成，可在技术细节查看文件路径。</span> : null}
                  {artifact.business_annotation ? <span>{artifact.business_annotation}</span> : null}
                </figcaption>
              </figure>
            );
          })}
        </div>
      ) : (
        <p>暂无图表</p>
      )}
    </article>
  );
}
