/**
 * Interpret a bulk rename response. The backend reports each file by its
 * filename before the rename; a file counts as renamed only when its result
 * succeeded without a conflicting file.
 */
export function successfulRenames(renames, result, files) {
  if (!result?.results) return renames;
  return renames.filter((rename) => {
    const file = files.find((item) => item.elan_id === rename.elan_id);
    if (!file) return false;
    const outcome = result.results.find(
      (item) => item.old_filename === file.name
    );
    return Boolean(outcome?.success && !outcome.conflict_elan_id);
  });
}

const warning = (key, params) => ({
  key,
  type: 'warning',
  duration: 6000,
  params,
});

/** The message summarizing a bulk rename, or null when there is nothing to say. */
export function bulkRenameMessage({ requested, successful, conflicts }) {
  const failed = requested - successful;
  if (successful === requested && conflicts === 0) {
    return { key: 'rename.bulkSuccess', type: 'success', duration: 4000 };
  }
  if (successful > 0 && conflicts > 0) {
    if (successful === 1 && conflicts === 1)
      return warning('rename.bulkMixedSingular');
    if (successful === 1)
      return warning('rename.bulkMixedOneSuccess', { failed: conflicts });
    if (conflicts === 1)
      return warning('rename.bulkMixedOneConflict', { successful });
    return warning('rename.bulkMixed', { successful, failed: conflicts });
  }
  if (successful === 0 && conflicts > 0) {
    return conflicts === 1
      ? warning('rename.bulkAllConflictsSingular')
      : warning('rename.bulkAllConflicts', { count: conflicts });
  }
  if (successful > 0) {
    if (successful === 1 && failed === 1)
      return warning('rename.bulkPartialSingular');
    if (successful === 1)
      return warning('rename.bulkPartialOneSuccess', { failed });
    if (failed === 1)
      return warning('rename.bulkPartialOneFailed', { successful });
    return warning('rename.bulkPartial', { successful, failed });
  }
  return null;
}
