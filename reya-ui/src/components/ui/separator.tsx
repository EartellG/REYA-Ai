import * as React from "react";

export function Separator({ className = "" }: { className?: string }) {
  return <div className={`h-px w-full bg-gray-800 ${className}`} />;
}

export default Separator;
