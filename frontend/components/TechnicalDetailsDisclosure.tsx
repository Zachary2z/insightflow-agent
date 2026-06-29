import React, { useState } from "react";
import type { TechnicalDetails } from "../lib/api";

type TechnicalDetailsDisclosureProps = {
  details?: TechnicalDetails;
};

function hasValue(value: unknown) {
  if (Array.isArray(value)) {
    return value.length > 0;
  }
  if (value && typeof value === "object") {
    return Object.keys(value).length > 0;
  }
  return typeof value === "string" ? value.trim().length > 0 : Boolean(value);
}

function JsonBlock({ title, value }: { title: string; value: unknown }) {
  if (!hasValue(value)) {
    return null;
  }
  return (
    <div className="technical-block">
      <h4>{title}</h4>
      <pre>{typeof value === "string" ? value : JSON.stringify(value, null, 2)}</pre>
    </div>
  );
}

export default function TechnicalDetailsDisclosure({ details }: TechnicalDetailsDisclosureProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <details className="technical-details">
      <summary onClick={() => setIsOpen((current) => !current)}>技术详情</summary>
      {isOpen ? (
        <div className="technical-content">
          <p>默认折叠；仅在需要排查 SQL、Trace、Provider Metadata 或校验日志时展开。</p>
          <JsonBlock title="SQL" value={details?.sql} />
          <JsonBlock title="Raw rows" value={details?.raw_rows} />
          <JsonBlock title="Trace" value={details?.trace_path} />
          <JsonBlock title="Provider metadata" value={details?.provider_metadata} />
          <JsonBlock title="Validation logs" value={details?.validation_logs} />
          <JsonBlock title="Debug" value={details?.debug} />
          {!details || !Object.values(details).some(hasValue) ? <p>暂无技术细节。</p> : null}
        </div>
      ) : null}
    </details>
  );
}
