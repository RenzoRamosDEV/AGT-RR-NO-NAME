/** Duelo mark: two crossed blades with their pommels, one in the accent color and one in purple. */
export function Logo({ size = 24 }: { size?: number }) {
  return (
    <svg
      className="logo"
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M7 7 22 22" stroke="var(--accent)" strokeWidth="3" strokeLinecap="round" />
      <path d="M25 7 10 22" stroke="var(--done)" strokeWidth="3" strokeLinecap="round" />
      <circle cx="24" cy="24" r="3" fill="var(--accent)" />
      <circle cx="8" cy="24" r="3" fill="var(--done)" />
    </svg>
  );
}
