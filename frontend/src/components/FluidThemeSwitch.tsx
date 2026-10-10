import { Liquid } from "liquid-gooey";
import { useLayoutEffect, useRef, useState } from "react";
import { type ThemePreference, useThemePreference } from "../lib/theme";
import { THEME_OPTIONS, ThemeButton } from "./ThemeButton";

type Thumb = { x: number; width: number };

/**
 * The libraries.dev `liquid-gooey` half of the theme switch, in its own module so the library is
 * fetched after first paint (see `ThemeSwitch`). The active segment is a liquid indicator that
 * slides to the new option trailing a droplet (`move` effect); the buttons stay real, crisp DOM.
 */
export default function FluidThemeSwitch({ compact }: { compact: boolean }) {
  const [preference, setPreference] = useThemePreference();
  const buttons = useRef<Partial<Record<ThemePreference, HTMLButtonElement | null>>>({});
  const [thumb, setThumb] = useState<Thumb | null>(null);

  // biome-ignore lint/correctness/useExhaustiveDependencies: re-measure when the choice or the layout (icons only / with text) changes
  useLayoutEffect(() => {
    const measure = () => {
      const el = buttons.current[preference];
      if (el && el.offsetWidth > 0) setThumb({ x: el.offsetLeft, width: el.offsetWidth });
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [preference, compact]);

  return (
    <fieldset
      className="segmented theme-switch"
      data-fluid={thumb ? "" : undefined}
      aria-label={compact ? "Tema (cabecera)" : "Tema"}
    >
      <Liquid className="theme-liquid" fill="var(--accent-bg)" blur={5} contrast={18}>
        {thumb && (
          <Liquid.Item effect="move" move={{ springiness: 0.55, wobble: 0.35, trail: 0.4 }}>
            <span
              className="theme-thumb"
              aria-hidden="true"
              style={{ width: thumb.width, transform: `translateX(${thumb.x}px)` }}
            />
          </Liquid.Item>
        )}
        {THEME_OPTIONS.map((option) => (
          <ThemeButton
            key={option.value}
            option={option}
            compact={compact}
            pressed={preference === option.value}
            onSelect={setPreference}
            buttonRef={(el) => {
              buttons.current[option.value] = el;
            }}
          />
        ))}
      </Liquid>
    </fieldset>
  );
}
