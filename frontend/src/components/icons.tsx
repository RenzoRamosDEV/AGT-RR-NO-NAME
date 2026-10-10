import type { ReactNode, SVGProps } from "react";

/** Small inline icons (16 px, `currentColor`); decorative unless the caller labels them. */
function Svg({
  children,
  size = 16,
  ...rest
}: { children: ReactNode; size?: number } & SVGProps<SVGSVGElement>) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {children}
    </svg>
  );
}

type IconProps = { size?: number } & SVGProps<SVGSVGElement>;

export const CheckCircleIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="8" cy="8" r="6.2" />
    <path d="m5.2 8.2 1.9 1.9 3.7-3.9" />
  </Svg>
);

export const XCircleIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="8" cy="8" r="6.2" />
    <path d="m5.8 5.8 4.4 4.4M10.2 5.8l-4.4 4.4" />
  </Svg>
);

export const ClockIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="8" cy="8" r="6.2" />
    <path d="M8 4.6V8l2.3 1.4" />
  </Svg>
);

export const DotCircleIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="8" cy="8" r="6.2" />
    <circle cx="8" cy="8" r="2" fill="currentColor" stroke="none" />
  </Svg>
);

export const AlertIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M8 2.2 14.2 13H1.8z" />
    <path d="M8 6.6v3M8 11.6h.01" />
  </Svg>
);

export const CommitIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="8" cy="8" r="2.6" />
    <path d="M1.5 8h3.9M10.6 8h3.9" />
  </Svg>
);

export const PullRequestIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="4" cy="3.6" r="1.7" />
    <circle cx="4" cy="12.4" r="1.7" />
    <circle cx="12" cy="12.4" r="1.7" />
    <path d="M4 5.3v5.4M12 10.7V6.5a2 2 0 0 0-2-2H8.4m0 0 1.6-1.6M8.4 4.5l1.6 1.6" />
  </Svg>
);

export const PlusIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M8 3v10M3 8h10" />
  </Svg>
);

export const SearchIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="7" cy="7" r="4.4" />
    <path d="m10.4 10.4 3.4 3.4" />
  </Svg>
);

export const SunIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="8" cy="8" r="2.8" />
    <path d="M8 1.5v1.6M8 12.9v1.6M1.5 8h1.6M12.9 8h1.6M3.4 3.4l1.1 1.1M11.5 11.5l1.1 1.1M3.4 12.6l1.1-1.1M11.5 4.5l1.1-1.1" />
  </Svg>
);

export const MoonIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M13.4 9.6A5.8 5.8 0 0 1 6.4 2.6a5.8 5.8 0 1 0 7 7Z" />
  </Svg>
);

export const MonitorIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="1.8" y="2.6" width="12.4" height="8.4" rx="1.2" />
    <path d="M5.6 13.6h4.8M8 11v2.6" />
  </Svg>
);

export const ChevronIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="m4.4 6.2 3.6 3.6 3.6-3.6" />
  </Svg>
);

export const MenuIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M2.5 4h11M2.5 8h11M2.5 12h11" />
  </Svg>
);

export const ChartIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M2.5 13.5h11M4.5 11V7.5M8 11V3.5M11.5 11V6" />
  </Svg>
);

export const GearIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="8" cy="8" r="2.2" />
    <path d="M8 1.6v1.7M8 12.7v1.7M1.6 8h1.7M12.7 8h1.7M3.5 3.5l1.2 1.2M11.3 11.3l1.2 1.2M3.5 12.5l1.2-1.2M11.3 4.7l1.2-1.2" />
  </Svg>
);

export const FileIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M4 1.8h5l3 3V14H4z" />
    <path d="M9 1.8v3h3" />
  </Svg>
);

/** Curved arrow going back: a commit that was undone. */
export const UndoIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M5.4 3.4 2.6 6.2l2.8 2.8" />
    <path d="M2.6 6.2h6.5a3.7 3.7 0 0 1 0 7.4H5.6" />
  </Svg>
);

export const ExternalIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M9 2.5h4.5V7M13.5 2.5 7.5 8.5M11.5 9.5v3a1 1 0 0 1-1 1h-6a1 1 0 0 1-1-1v-6a1 1 0 0 1 1-1h3" />
  </Svg>
);

export const CopyIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="5.4" y="5.4" width="8" height="8" rx="1.4" />
    <path d="M10.6 5.4V4a1.4 1.4 0 0 0-1.4-1.4H4A1.4 1.4 0 0 0 2.6 4v5.2A1.4 1.4 0 0 0 4 10.6h1.4" />
  </Svg>
);

export const InfoIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="8" cy="8" r="6.2" />
    <path d="M8 7.2v3.6M8 5h.01" />
  </Svg>
);

export const FolderIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M2 4.2a1 1 0 0 1 1-1h3l1.4 1.6H13a1 1 0 0 1 1 1V12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1z" />
  </Svg>
);

export const SparkIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M8 1.8 9.4 6.6 14.2 8 9.4 9.4 8 14.2 6.6 9.4 1.8 8 6.6 6.6z" />
  </Svg>
);
