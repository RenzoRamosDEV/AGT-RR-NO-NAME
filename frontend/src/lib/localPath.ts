/** True for POSIX (`/home/me/repo`) and Windows (`C:\repo`, `C:/repo`) absolute paths. */
export function isAbsolutePath(path: string): boolean {
  return /^(\/|[A-Za-z]:[\\/])/.test(path.trim());
}

/**
 * `owner/repo` guess from the last two segments of a local path (the sample source has no git
 * remote to read); a single segment gives just that name. Returns "" for a root path.
 */
export function slugFromPath(path: string): string {
  const segments = path
    .trim()
    .split(/[\\/]+/)
    .filter((s) => s !== "" && !/^[A-Za-z]:$/.test(s));
  return segments.slice(-2).join("/");
}
