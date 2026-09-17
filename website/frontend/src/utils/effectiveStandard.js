/**
 * The naming standard assigned at a location, from the effective standards
 * store. A location maps file types to standard ids, or holds one id.
 */
export function standardIdAt(effectiveStandards, locationId) {
  const assignment = effectiveStandards[locationId];
  if (typeof assignment === 'string' || typeof assignment === 'number') {
    return assignment;
  }
  if (assignment && typeof assignment === 'object') {
    return Object.values(assignment).find(Boolean);
  }
  return undefined;
}

export function standardAt(effectiveStandards, namingStandards, locationId) {
  const id = standardIdAt(effectiveStandards, locationId);
  return namingStandards.find((standard) => standard.id === id) ?? null;
}
