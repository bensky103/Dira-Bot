/**
 * Generate a deterministic offset from a string (e.g., link URL).
 * Returns an offset in degrees (~±200m) so markers in the same area
 * don't stack but remain stable across reloads.
 */
export function hashOffset(input: string): { dlat: number; dlng: number } {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    const char = input.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash |= 0;
  }

  const latHash = (hash & 0xffff) / 0xffff;
  const lngHash = ((hash >> 16) & 0xffff) / 0xffff;

  const MAX_OFFSET = 0.002;
  return {
    dlat: (latHash - 0.5) * 2 * MAX_OFFSET,
    dlng: (lngHash - 0.5) * 2 * MAX_OFFSET,
  };
}
