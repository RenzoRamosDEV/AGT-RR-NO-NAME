import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "primary" | "danger";
};

export function Button({ variant = "default", className = "", type = "button", ...rest }: Props) {
  const cls = ["btn", variant === "default" ? "" : `btn-${variant}`, className]
    .filter(Boolean)
    .join(" ");
  return <button type={type} className={cls} {...rest} />;
}
