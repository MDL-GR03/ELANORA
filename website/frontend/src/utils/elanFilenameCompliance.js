import { isFilenameCompliant } from './filenameCompliance';

/** ELAN-specific fail-closed wrapper around the shared naming-standard engine. */

/**
 * Check if an ELAN filename complies with the given naming standard
 * @param {Object} standard - The naming standard to check against
 * @param {string} filename - The filename to check (may include .eaf extension)
 * @returns {boolean} true if compliant, false otherwise
 */
export function isElanFilenameCompliant(standard, filename) {
  if (!standard?.pattern || !Array.isArray(standard?.components)) {
    return false; // Require valid standard
  }

  if (!filename || !filename.trim()) {
    return false;
  }

  const normalizedFilename = filename.trim();
  if (!normalizedFilename.toLowerCase().endsWith('.eaf')) {
    return false;
  }
  return isFilenameCompliant(standard, normalizedFilename);
}
