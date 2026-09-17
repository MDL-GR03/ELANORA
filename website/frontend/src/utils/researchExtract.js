const EXTRACT_PROPERTY = 'ELANORA_RESEARCH_EXTRACT';

async function extractMetadata(file) {
  try {
    const document = new DOMParser().parseFromString(
      await file.text(),
      'application/xml'
    );
    const property = Array.from(document.querySelectorAll('PROPERTY')).find(
      (item) => item.getAttribute('NAME') === EXTRACT_PROPERTY
    );
    if (!property?.textContent) return null;
    const metadata = JSON.parse(property.textContent);
    return metadata.purpose === 'tier_scoped_edit' ? metadata : null;
  } catch {
    // The server remains authoritative for malformed provenance and EAF data.
    return null;
  }
}

/**
 * The research scope of files downloaded as research copies, read from the
 * provenance property ELANORA writes into each copy. The topic is known only
 * when every copy names the same one. Returns null for ordinary files.
 */
export async function detectResearchScope(files) {
  const scopes = (await Promise.all(files.map(extractMetadata))).filter(
    Boolean
  );
  if (!scopes.length) return null;
  const topicIds = [...new Set(scopes.map((item) => item.research_topic_id))];
  const topicNames = [...new Set(scopes.map((item) => item.research_topic))];
  return {
    topicId: topicIds.length === 1 ? topicIds[0] : null,
    topicName: topicNames.length === 1 ? topicNames[0] : null,
    tiers: [...new Set(scopes.flatMap((item) => item.selected_tiers || []))],
  };
}
