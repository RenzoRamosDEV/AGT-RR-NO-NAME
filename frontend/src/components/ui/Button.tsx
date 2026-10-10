import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  /** `primary` is the green call to action; `danger` an outlined destructive action; `ghost` a borderless one. */
  variant?: "default" | "primary" | "danger" | "ghost";
  size?: "md" | "sm";
};

export function Button({
  variant = "default",
  size = "md",
  className = "",
  type = "button",
  ...rest
}: Props) {
  const cls = [
    "btn",
    variant === "default" ? "" : `btn-${variant}`,
    size === "sm" ? "btn-sm" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return <button type={type} className={cls} {...rest} />;
}
