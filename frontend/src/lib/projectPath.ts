/**
 * Project routes. Backend slugs look like `owner/repo`, which a `:slug` route param cannot match
 * (it never consumes a "/"), so the app has a single `p/*` route and reads the rest with
 * `parseProjectPath`. Every internal link to a project or change is built here.
 */
const encodeSlug = (slug: string) => slug.split("/").map(encodeURIComponent).join("/");

export function projectPath(slug: string): string {
  return `/p/${encodeSlug(slug)}`;
}

export function changePath(slug: string, id: string): string {
  return `${projectPath(slug)}/changes/${encodeURIComponent(id)}`;
}

export type ProjectRoute =
  | { kind: "channel"; slug: string }
  | { kind: "change"; slug: string; id: string }
  | { kind: "none" };

/**
 * Interprets what follows `/p/`. With three or more segments and `changes` second to last it is
 * a change detail (slug = the segments before it); otherwise the whole path is a channel slug, so
 * a project called `changes` or `x/changes` is still a channel.
 */
export function parseProjectPath(rest: string | undefined): ProjectRoute {
  const segments = (rest ?? "").split("/").filter((s) => s !== "");
  if (segments.length === 0) return { kind: "none" };
  if (segments.length >= 3 && segments[segments.length - 2] === "changes") {
    return {
      kind: "change",
      slug: segments.slice(0, -2).join("/"),
      id: segments[segments.length - 1],
    };
  }
  return { kind: "channel", slug: segments.join("/") };
}
