import React from "react";
export const ScrollArea = ({ children }: any) => (
  <div style={{ overflowY: "auto", maxHeight: "400px" }}>{children}</div>
);
