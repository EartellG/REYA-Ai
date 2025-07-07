import { jsx as _jsx } from "react/jsx-runtime";
export const Avatar = ({ children }) => _jsx("div", { children: children });
export const AvatarImage = ({ src, alt }) => (_jsx("img", { src: src, alt: alt, className: "rounded-full w-10 h-10" }));
