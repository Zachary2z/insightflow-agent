"use client";

import React, { useEffect, useRef, useState } from "react";
import { resolveApiUrl, type ChartArtifact } from "../lib/api";

type ChartArtifactGalleryProps = {
  artifacts?: ChartArtifact[];
};

type EChartsInstance = {
  setOption: (option: Record<string, unknown>, notMerge?: boolean) => void;
  resize: () => void;
  dispose: () => void;
};

type InteractiveChartProps = {
  option: Record<string, unknown>;
  title: string;
  fallbackUrl: string;
};

function InteractiveChart({ option, title, fallbackUrl }: InteractiveChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let disposed = false;
    let chart: EChartsInstance | null = null;
    let removeResize: (() => void) | null = null;

    setFailed(false);
    import("../lib/echarts-runtime")
      .then(({ echarts }) => {
        if (disposed || !containerRef.current) {
          return;
        }
        chart = echarts.init(containerRef.current) as EChartsInstance;
        chart.setOption(option, true);
        const handleResize = () => chart?.resize();
        window.addEventListener("resize", handleResize);
        removeResize = () => window.removeEventListener("resize", handleResize);
      })
      .catch(() => {
        if (!disposed) {
          setFailed(true);
        }
      });

    return () => {
      disposed = true;
      removeResize?.();
      chart?.dispose();
    };
  }, [option]);

  if (failed && fallbackUrl) {
    return <img src={fallbackUrl} alt={title || "分析图表"} />;
  }

  return (
    <div
      ref={containerRef}
      className="echarts-artifact"
      data-testid="echarts-chart"
      role="img"
      aria-label={title || "分析图表"}
    />
  );
}

export default function ChartArtifactGallery({ artifacts = [] }: ChartArtifactGalleryProps) {
  const displayable = artifacts.filter(
    (artifact) =>
      artifact.echarts_option || artifact.image_url || artifact.url || artifact.path || artifact.skip_reason || artifact.failure_reason,
  );

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
            const title = artifact.title || "分析图表";
            const imageUrl = resolveApiUrl(artifact.image_url || artifact.url || "");
            const hasEchartsOption = Boolean(artifact.echarts_option);
            const statusReason = artifact.skip_reason || artifact.failure_reason || "";
            return (
              <figure
                key={`${artifact.artifact_id || artifact.image_path || artifact.path || artifact.url || index}-${index}`}
                className="chart-artifact"
              >
                {hasEchartsOption ? (
                  <InteractiveChart option={artifact.echarts_option as Record<string, unknown>} title={title} fallbackUrl={imageUrl} />
                ) : imageUrl ? (
                  <img src={imageUrl} alt={title} />
                ) : null}
                <figcaption>
                  <strong>{title}</strong>
                  {artifact.unit ? <span>单位：{artifact.unit}</span> : null}
                  {statusReason ? <span>{statusReason}</span> : null}
                  {!hasEchartsOption && !imageUrl && !statusReason ? <span>图表已生成，可在技术细节查看文件路径。</span> : null}
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
