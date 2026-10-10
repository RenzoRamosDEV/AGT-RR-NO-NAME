import { type ThemePreference, useThemePreference } from "../lib/theme";
import { MonitorIcon, MoonIcon, SunIcon } from "./icons";

const OPTIONS: { value: ThemePreference; label: string; Icon: typeof SunIcon }[] = [
  { value: "system", label: "Sistema", Icon: MonitorIcon },
  { value: "light", label: "Claro", Icon: SunIcon },
  { value: "dark", label: "Oscuro", Icon: MoonIcon },
];

/**
 * Theme selector (System / Light / Dark), a segmented control of toggle buttons. `compact` keeps
 * only the icons (header); the accessible name always carries the full text.
 */
export function ThemeSwitch({ compact = false }: { compact?: boolean }) {
  const [preference, setPreference] = useThemePreference();
  return (
    <fieldset className="segmented theme-switch" aria-label={compact ? "Tema (cabecera)" : "Tema"}>
      {OPTIONS.map(({ value, label, Icon }) => (
        <button
          key={value}
          type="button"
          className="segment"
          aria-pressed={preference === value}
          aria-label={compact ? `Tema ${label.toLowerCase()}` : undefined}
          title={`Tema ${label.toLowerCase()}`}
          onClick={() => setPreference(value)}
        >
          <Icon />
          {!compact && <span>{label}</span>}
        </button>
      ))}
    </fieldset>
  );
}
