import React from "react";

export const Card = ({ children }: any) => (
  <div className="border p-4 rounded">{children}</div>
);

export const CardContent = ({ children }: any) => (
  <div className="mt-2">{children}</div>
);
