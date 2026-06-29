import React from "react";

export type ProductCardProps = {
  children: React.ReactNode;
  className?: string;
};

export default function ProductCard({ children, className }: ProductCardProps) {
  return <section className={["product-card", className].filter(Boolean).join(" ")}>{children}</section>;
}
