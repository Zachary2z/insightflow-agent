import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import "./product-refresh.css";

export const metadata: Metadata = {
  title: "InsightFlow · 数据决策工作台",
  description: "从数据准备到业务分析与报告交付的一体化决策工作台。",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
