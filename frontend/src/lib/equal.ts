/** Structural equality for plain JSON data (API responses); cheap enough for one page of results. */
export function sameValue<T>(a: T, b: T): boolean {
  return a === b || JSON.stringify(a) === JSON.stringify(b);
}
