export function formatEafUploadError(detail, fallback) {
  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }
  if (
    !detail ||
    detail.code !== 'invalid_eaf_batch' ||
    !Array.isArray(detail.rejected_files)
  ) {
    return typeof detail?.message === 'string' && detail.message.trim()
      ? detail.message
      : fallback;
  }

  const files = detail.rejected_files.map((file) => {
    const firstIssue = Array.isArray(file.issues) ? file.issues[0] : null;
    if (!firstIssue) {
      return `${file.filename}: validation failed`;
    }
    const remaining = Math.max(0, file.issue_count - 1);
    const suffix = remaining > 0 ? `; ${remaining} more issue(s)` : '';
    return `${file.filename}: ${firstIssue.message} (${firstIssue.location})${suffix}`;
  });

  return [detail.message, ...files].filter(Boolean).join(' ');
}
