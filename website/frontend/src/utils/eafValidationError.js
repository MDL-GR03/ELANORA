import { apiErrorMessage } from '@/utils/apiError';

const FILE_DETAIL_CODES = new Set([
  'protected_baseline_modified',
  'tier_reintegration_conflict',
  'filename_not_compliant',
]);

function rejectedFileSummary(file, translate) {
  const firstIssue = Array.isArray(file.issues) ? file.issues[0] : null;
  if (!firstIssue) {
    return translate('uploadPage.errors.fileValidationFailed', {
      filename: file.filename,
    });
  }
  const remaining = Math.max(0, (file.issue_count || 0) - 1);
  const translatedMessage = translate(`apiErrors.${firstIssue.code}`, firstIssue);
  const message = translatedMessage || firstIssue.message;
  const summary = `${file.filename}: ${message} (${firstIssue.location})`;
  return remaining > 0
    ? `${summary}; ${translate('uploadPage.errors.moreIssues', remaining)}`
    : summary;
}

/**
 * Explain a refused EAF upload: the refusal itself, then what was wrong with
 * each rejected file, or which tiers conflicted.
 */
export function formatEafUploadError(error, translate, fallback) {
  const message = apiErrorMessage(error, translate, fallback);
  const body = error?.response?.data;
  const params = body?.params || {};

  if (
    body?.code === 'invalid_eaf_batch' &&
    Array.isArray(params.rejected_files)
  ) {
    return [
      message,
      ...params.rejected_files.map((file) =>
        rejectedFileSummary(file, translate)
      ),
    ].join(' ');
  }
  if (FILE_DETAIL_CODES.has(body?.code) && params.filename) {
    const tiers = Array.isArray(params.tiers) ? params.tiers.join(', ') : '';
    const pattern = params.pattern ? ` ${params.pattern}` : '';
    return `${message} (${params.filename}${tiers ? `: ${tiers}` : ''}${pattern})`;
  }
  return message;
}
