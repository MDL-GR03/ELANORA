export function groupContributionThreads(uploads = [], reviewCases = []) {
  const predecessors = new Map();
  for (const upload of uploads) {
    if (upload.superseded_by_upload_id) {
      const versions = predecessors.get(upload.superseded_by_upload_id) || [];
      versions.push(upload);
      predecessors.set(upload.superseded_by_upload_id, versions);
    }
  }

  function collectHistory(upload, seen = new Set()) {
    if (seen.has(upload.upload_id)) return [];
    seen.add(upload.upload_id);
    return (predecessors.get(upload.upload_id) || []).flatMap((previous) => [
      ...collectHistory(previous, seen),
      previous,
    ]);
  }

  return uploads
    .filter((upload) => !upload.superseded_by_upload_id)
    .map((upload) => {
      const versionHistory = collectHistory(upload);
      const lineageIds = new Set([
        upload.upload_id,
        ...versionHistory.map((version) => version.upload_id),
      ]);
      const reviewCase = reviewCases.find(
        (item) =>
          lineageIds.has(item.upload_id) ||
          lineageIds.has(item.resubmitted_upload_id)
      );
      const reviewStatus = {
        open: 'under_review',
        changes_requested: 'changes_requested',
        resubmitted: 'review_required',
      }[reviewCase?.state];
      return {
        ...upload,
        technical_merge_status: upload.merge_status,
        merge_status: reviewStatus || upload.merge_status,
        version_history: versionHistory,
        version_number: versionHistory.length + 1,
        review_case: reviewCase || null,
      };
    });
}

function contributionTimestamp(contribution) {
  const timestamp = Date.parse(contribution.uploaded_at || '');
  return Number.isNaN(timestamp) ? 0 : timestamp;
}

export function sortContributionThreads(threads = [], order = 'oldest') {
  const direction = order === 'newest' ? -1 : 1;
  return [...threads].sort((left, right) => {
    const byDate =
      (contributionTimestamp(left) - contributionTimestamp(right)) * direction;
    if (byDate !== 0) return byDate;
    return (Number(left.upload_id) - Number(right.upload_id)) * direction;
  });
}

export function countAnnotationCollisions(contribution) {
  return new Set(
    (contribution.annotation_collisions || []).flatMap((collision) =>
      Object.entries(collision.annotations || {}).flatMap(
        ([filename, annotationIds]) =>
          annotationIds.map((annotationId) => `${filename}:${annotationId}`)
      )
    )
  ).size;
}
