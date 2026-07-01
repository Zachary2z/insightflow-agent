"use client";

import React from "react";
import { getWorkspaceSettings, type WorkspaceSettings } from "../lib/api";
import { StatusPill, type StatusPillProps } from "./ProductStatus";

type ModelModePillProps = {
  workspaceId: string;
};

type PillState = {
  label: string;
  tone: StatusPillProps["tone"];
};

function pillState(modelMode?: WorkspaceSettings["model_mode"]): PillState {
  if (!modelMode) {
    return { label: "模型状态检查中", tone: "neutral" };
  }
  if (modelMode.product_live_mode) {
    return { label: "真实模型已开启", tone: "green" };
  }
  if (modelMode.provider?.api_key_present) {
    return { label: "仅已配置密钥", tone: "orange" };
  }
  return { label: "真实模型未开启", tone: "neutral" };
}

export default function ModelModePill({ workspaceId }: ModelModePillProps) {
  const [state, setState] = React.useState<PillState>(() => pillState());

  React.useEffect(() => {
    let isMounted = true;
    Promise.resolve(getWorkspaceSettings(workspaceId))
      .then((settings) => {
        if (isMounted) {
          setState(pillState(settings?.model_mode));
        }
      })
      .catch(() => {
        if (isMounted) {
          setState({ label: "模型状态未知", tone: "neutral" });
        }
      });
    return () => {
      isMounted = false;
    };
  }, [workspaceId]);

  return <StatusPill tone={state.tone}>{state.label}</StatusPill>;
}
