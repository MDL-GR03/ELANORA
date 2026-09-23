import { extractComponentsFromFilename } from '@/utils/filenameCompliance';
import { reportClientError } from '@/utils/errorDiagnostics';

/**
 * Derive a media file's basename from its MEDIA_DESCRIPTOR URL attributes,
 * mirroring the backend's extraction in
 * app/crud/elan_file_media.py:get_project_files_with_media_simple so a
 * not-yet-uploaded file's media filenames match what the server would report
 * once it's committed.
 * @param {string|null} mediaUrl - MEDIA_DESCRIPTOR@MEDIA_URL
 * @param {string|null} relativeMediaUrl - MEDIA_DESCRIPTOR@RELATIVE_MEDIA_URL
 * @returns {string|null} The media file's basename, or null if neither URL yields one
 */
function mediaUrlBasename(mediaUrl, relativeMediaUrl) {
  const source = relativeMediaUrl || mediaUrl;
  if (!source) return null;
  const withoutFileScheme = source.startsWith('file:///')
    ? source.slice('file:///'.length)
    : source;
  const segments = withoutFileScheme.split(/[/\\]/);
  const basename = segments[segments.length - 1];
  return basename || null;
}

/**
 * Extract the linked media filenames from raw ELAN (.eaf) XML text, without
 * uploading the file first. Used to suggest a compliant filename for a file
 * still sitting in the browser's upload selection, the same way an already
 * uploaded file's linked media suggests one on the Projects page.
 * @param {string} eafText - Raw XML content of an .eaf file
 * @returns {string[]} Deduplicated media filenames referenced by the file, or [] if none/unparsable
 */
export function extractMediaFilenamesFromEafText(eafText) {
  if (!eafText || typeof DOMParser === 'undefined') return [];
  try {
    const doc = new DOMParser().parseFromString(eafText, 'text/xml');
    if (doc.querySelector('parsererror')) return [];
    const descriptors = Array.from(
      doc.querySelectorAll('HEADER > MEDIA_DESCRIPTOR')
    );
    const filenames = [];
    for (const descriptor of descriptors) {
      const filename = mediaUrlBasename(
        descriptor.getAttribute('MEDIA_URL'),
        descriptor.getAttribute('RELATIVE_MEDIA_URL')
      );
      if (filename && !filenames.includes(filename)) {
        filenames.push(filename);
      }
    }
    return filenames;
  } catch (error) {
    reportClientError('Error parsing EAF media descriptors', error);
    return [];
  }
}

/**
 * Extract naming components from media filenames using a naming standard
 * @param {Array} mediaFilenames - Array of media filenames
 * @param {Object} mediaStandard - The naming standard for media files
 * @returns {Object|null} Extracted components or null if extraction fails
 */
export function extractComponentsFromMedia(mediaFilenames, mediaStandard) {
  if (!mediaFilenames || mediaFilenames.length === 0 || !mediaStandard) {
    return null;
  }

  // Try to extract from the first media file
  const firstMediaFile = mediaFilenames[0];

  // Remove file extension to get the base filename
  const baseFilename = firstMediaFile.replace(/\.[^/.]+$/, '');

  // Use the existing extraction function
  const extractedComponents = extractComponentsFromFilename(
    mediaStandard,
    baseFilename
  );

  return extractedComponents;
}

/**
 * Get value for a component from various sources
 */
function getComponentValue(
  componentName,
  targetComponent,
  extractedComponents
) {
  // Handle prefix: use project's accepted values
  if (componentName.includes('prefix')) {
    if (
      targetComponent.accepted_values &&
      targetComponent.accepted_values.length > 0
    ) {
      return targetComponent.accepted_values[0];
    }
    return null;
  }

  // Try to use value from media if component exists
  if (Object.hasOwn(extractedComponents, componentName)) {
    return extractedComponents[componentName];
  }

  // Fallback to accepted values
  if (
    targetComponent.accepted_values &&
    targetComponent.accepted_values.length > 0
  ) {
    return targetComponent.accepted_values[0];
  }

  // Generate default based on regex pattern
  return generateDefaultValue(targetComponent);
}

/**
 * Generate a default value based on component regex pattern
 */
function generateDefaultValue(targetComponent) {
  if (!targetComponent.regex) {
    return 'DEFAULT';
  }

  if (targetComponent.regex.includes('\\p{N}')) {
    // Numeric component - use zeros
    const numMatch = targetComponent.regex.match(/\{(\d+)\}/);
    const length = numMatch ? parseInt(numMatch[1]) : 2;
    return '0'.repeat(length);
  }

  if (targetComponent.regex.includes('\\p{L}')) {
    // Letter component - use A
    const letterMatch = targetComponent.regex.match(/\{(\d+)\}/);
    const length = letterMatch ? parseInt(letterMatch[1]) : 1;
    return 'A'.repeat(length);
  }

  return 'DEFAULT';
}

/**
 * Map media components to target standard components using project-based logic:
 * 1. For prefix: use the project files standard prefix directly (from accepted_values)
 * 2. Copy over common components when they exist in both standards
 * 3. Use accepted values for missing components that the target requires
 * @param {Object} extractedComponents - Components from media
 * @param {Object} targetStandard - Target standard (project files)
 * @returns {Object} Mapped components
 */
function mapMediaToTargetComponents(extractedComponents, targetStandard) {
  const mappedComponents = {};

  // Process each component required by the target standard
  for (const targetComponent of targetStandard.components) {
    const componentName = targetComponent.name;
    const value = getComponentValue(
      componentName,
      targetComponent,
      extractedComponents
    );

    if (value) {
      mappedComponents[componentName] = value;
    }
  }

  return mappedComponents;
}

/**
 * Generate a suggested filename using extracted components and target standard
 * @param {Object} extractedComponents - Components extracted from media
 * @param {Object} targetStandard - The target naming standard for ELAN files
 * @param {string} extension - File extension (default: '.eaf')
 * @returns {string} Suggested filename
 */
export function generateSuggestedFilename(
  extractedComponents,
  targetStandard,
  extension = '.eaf'
) {
  if (!extractedComponents || !targetStandard?.pattern) {
    return null;
  }

  // Intelligently map media components to target components
  const mappedComponents = mapMediaToTargetComponents(
    extractedComponents,
    targetStandard
  );

  let suggestedName = targetStandard.pattern;

  // Sort components by order to build filename correctly
  const sortedComponents = [...targetStandard.components].sort(
    (a, b) => a.order - b.order
  );

  // Replace each component placeholder with mapped value
  for (const component of sortedComponents) {
    const value = mappedComponents[component.name];
    if (value) {
      // Replace component placeholder with actual value
      const placeholder = `{${component.name}}`;
      suggestedName = suggestedName.replace(
        new RegExp(placeholder.replace(/[{}]/g, '\\$&'), 'g'),
        value
      );
    }
  }

  // If we still have placeholders, the extraction wasn't complete
  if (suggestedName.includes('{') && suggestedName.includes('}')) {
    return null;
  }

  const result = suggestedName + extension;
  return result;
}

/**
 * Suggest a compliant filename for a not-yet-uploaded .eaf file by reading
 * its own linked media descriptors, the same information an already
 * uploaded file's suggestion is built from on the Projects page.
 * @param {File} file - The selected .eaf file, not yet uploaded
 * @param {Object|null} targetStandard - The project's EAF naming standard
 * @param {Object|null} mediaStandard - The project's media naming standard
 * @returns {Promise<string|null>} A suggested filename, or null if none could be derived
 */
export async function suggestEafFilenameFromMedia(
  file,
  targetStandard,
  mediaStandard
) {
  if (!file || !targetStandard || !mediaStandard) return null;
  let text;
  try {
    text = await file.text();
  } catch (error) {
    reportClientError('Error reading EAF file for rename suggestion', error);
    return null;
  }
  const mediaFilenames = extractMediaFilenamesFromEafText(text);
  const extractedComponents = extractComponentsFromMedia(
    mediaFilenames,
    mediaStandard
  );
  if (!extractedComponents) return null;
  return generateSuggestedFilename(extractedComponents, targetStandard);
}

/**
 * Generate media-based rename suggestions for multiple files
 * @param {Array} filesWithMedia - Files with their associated media
 * @param {Object} mediaStandard - Naming standard for media files
 * @param {Object} targetStandard - Target naming standard for ELAN files
 * @returns {Array} Array of files with suggested names
 */
export function generateMediaBasedSuggestions(
  filesWithMedia,
  mediaStandard,
  targetStandard
) {
  if (!filesWithMedia || !mediaStandard || !targetStandard) {
    return [];
  }

  const suggestions = [];

  for (const file of filesWithMedia) {
    // Check if the file has media filenames (from the new API response format)
    if (!file.media_filenames || file.media_filenames.length === 0) {
      continue;
    }

    // Extract components from media filenames
    const extractedComponents = extractComponentsFromMedia(
      file.media_filenames,
      mediaStandard
    );

    if (extractedComponents) {
      // Generate suggested filename
      const suggestedName = generateSuggestedFilename(
        extractedComponents,
        targetStandard
      );

      if (suggestedName) {
        suggestions.push({
          elan_id: file.elan_id,
          currentName: file.name,
          suggestedName: suggestedName,
          extractedComponents: extractedComponents,
          mediaFiles: file.media_filenames,
        });
      }
    }
  }

  return suggestions;
}

/**
 * Get the media standard for a project (location 3 = elanMedia)
 * @param {number} projectId - Project ID
 * @param {Object} effectiveStandardStore - Store for effective standards
 * @param {Object} namingStandardStore - Store for naming standards
 * @returns {Object|null} Media naming standard or null
 */
export async function getMediaStandardForProject(
  projectId,
  effectiveStandardStore,
  namingStandardStore,
  fetchData = true
) {
  const ELAN_MEDIA_LOCATION_ID = 3;

  try {
    // Fetch effective standards for media location
    if (fetchData) {
      await effectiveStandardStore.fetchEffectiveStandards(
        projectId,
        ELAN_MEDIA_LOCATION_ID
      );
    }

    // Get the effective standards for this location
    const effectiveStandards =
      effectiveStandardStore.effectiveStandards[ELAN_MEDIA_LOCATION_ID];

    if (!effectiveStandards) {
      return null;
    }

    // Find the first assigned standard (assuming one file type for now)
    const assignedStandardId = Object.values(effectiveStandards).find(
      (id) => id && id !== ''
    );

    if (!assignedStandardId) {
      return null;
    }

    // Make sure we have the naming standards loaded
    if (fetchData) {
      await namingStandardStore.fetchStandardsAndComponentNames(projectId);
    }

    // Find the actual standard
    const mediaStandard = namingStandardStore.standards.find(
      (std) => std.id === parseInt(assignedStandardId)
    );

    return mediaStandard || null;
  } catch (error) {
    reportClientError('Error fetching media standard', error);
    return null;
  }
}
