import React from "react";
export const Avatar = ({ children }: any) => <div>{children}</div>;

export const AvatarImage = ({ src, alt }: { src: string; alt: string }) => (
  <img src={src} alt={alt} className="rounded-full w-10 h-10" />
);

<img
  src="/ReyaAva.png"
  alt="REYA Avatar"
  className="mx-auto h-48 w-48 object-cover rounded-full"
/>
