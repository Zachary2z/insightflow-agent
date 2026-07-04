import React from "react";

export type ProductPageHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
};

export default function ProductPageHeader({ eyebrow, title, description, action }: ProductPageHeaderProps) {
  return (
    <header className="product-page-header">
      <div>
        <p className="product-eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="product-lead">{description}</p>
      </div>
      {action ? <div className="product-page-header-action">{action}</div> : null}
    </header>
  );
}
