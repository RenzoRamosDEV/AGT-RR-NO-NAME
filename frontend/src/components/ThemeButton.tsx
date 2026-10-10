import type { Ref } from "react";
import type { ThemePreference } from "../lib/theme";
import { MonitorIcon, MoonIcon, SunIcon } from "./icons";

export type ThemeOption = { value: ThemePreference; label: string; Icon: typeof SunIcon };

export const THEME_OPTIONS: ThemeOption[] = [
  { value: "system", label: "Sistema", Icon: MonitorIcon },
  { value: "light", label: "Claro", Icon: SunIcon },
  { value: "dark", label: "Oscuro", Icon: MoonIcon },
];

/** One segment of the theme switch; shared by the static and the liquid versions. */
export function ThemeButton({
  option: { value, label, Icon },
  compact,
  pressed,
  onSelect,
  buttonRef,
}: {
  option: ThemeOption;
  compact: boolean;
  pressed: boolean;
  onSelect: (next: ThemePreference) => void;
  buttonRef?: Ref<HTMLButtonElement>;
}) {
  return (
    <button
      ref={buttonRef}
      type="button"
      className="segment"
      aria-pressed={pressed}
      aria-label={compact ? `Tema ${label.toLowerCase()}` : undefined}
      title={`Tema ${label.toLowerCase()}`}
      onClick={() => onSelect(value)}
    >
      <Icon />
      {!compact && <span>{label}</span>}
    </button>
  );
}
