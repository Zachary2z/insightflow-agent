import React, { type ComponentPropsWithoutRef } from "react";

export type ProductCardProps = ComponentPropsWithoutRef<"section">;

export default function ProductCard({ children, className, ...sectionProps }: ProductCardProps) {
  return (
    <section {...sectionProps} className={["product-card", className].filter(Boolean).join(" ")}>
      {children}
    </section>
  );
}
