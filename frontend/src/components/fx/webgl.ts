/** Answers cached per WebGL version: creating a context is not free and the answer never changes. */
const cached = new Map<1 | 2, boolean>();

/** `true` when a WebGL context can be created here (never in jsdom, rarely in locked-down browsers). */
export function hasWebGL(version: 1 | 2 = 1): boolean {
  const known = cached.get(version);
  if (known !== undefined) return known;
  let ok = false;
  try {
    const canvas = document.createElement("canvas");
    ok = Boolean(
      version === 2
        ? canvas.getContext("webgl2")
        : (canvas.getContext("webgl2") ?? canvas.getContext("webgl")),
    );
  } catch {
    ok = false;
  }
  cached.set(version, ok);
  return ok;
}

/** Test hook: forget the cached answers. */
export function resetWebGLForTests(): void {
  cached.clear();
}
