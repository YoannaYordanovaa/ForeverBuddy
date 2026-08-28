import React from "react";

export default function BrandLogo({
  namePart1 = "Forever",
  namePart2 = "Buddy",
  accentColor = "#FFC300",
}) {
  return (
    <div style={{ fontSize: 16, whiteSpace: "nowrap" }}>
      <strong style={{ color: "#fff" }}>{namePart1}</strong>
      <strong style={{ color: accentColor }}>{namePart2}</strong>
    </div>
  );
}
