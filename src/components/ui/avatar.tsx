import React from "react";
export const Avatar = ({ children }: any) => <div>{children}</div>;

export const AvatarImage = ({ src, alt }: { src: string; alt: string }) => (
  <img src={src} alt={alt} className="rounded-full w-10 h-10" />
);

