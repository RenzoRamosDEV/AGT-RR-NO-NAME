/**
 * Text for the "last updated" indicator. Under 5 s it says "ahora" so a ticking counter does not
 * distract; afterwards seconds, then minutes, then hours.
 */
export function updatedAgo(seconds: number): string {
  if (seconds < 5) return "Actualizado ahora";
  if (seconds < 60) return `Actualizado hace ${Math.floor(seconds)} s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `Actualizado hace ${minutes} min`;
  return `Actualizado hace ${Math.floor(minutes / 60)} h`;
}
