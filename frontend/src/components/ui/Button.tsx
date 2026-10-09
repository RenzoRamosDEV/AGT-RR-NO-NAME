import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "primary" };

export function Button({ variant = "default", className = "", type = "button", ...rest }: Props) {
  const cls = ["btn", variant === "primary" ? "btn-primary" : "", className]
    .filter(Boolean)
    .join(" ");
  return <button type={type} className={cls} {...rest} />;
}
