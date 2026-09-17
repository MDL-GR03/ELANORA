// @vitest-environment jsdom

import { describe, expect, it } from 'vitest';

import { detectResearchScope } from './researchExtract';

function eaf(metadata) {
  const property = metadata
    ? `<PROPERTY NAME="ELANORA_RESEARCH_EXTRACT">${JSON.stringify(metadata)}</PROPERTY>`
    : '';
  return {
    text: async () =>
      `<ANNOTATION_DOCUMENT><HEADER>${property}</HEADER></ANNOTATION_DOCUMENT>`,
  };
}

const extract = (topicId, topic, tiers) => ({
  purpose: 'tier_scoped_edit',
  research_topic_id: topicId,
  research_topic: topic,
  selected_tiers: tiers,
});

describe('detectResearchScope', () => {
  it('returns null for ordinary files', async () => {
    expect(
      await detectResearchScope([eaf(null), { text: async () => '<' }])
    ).toBeNull();
  });

  it('reads the topic and tiers of research copies', async () => {
    const scope = await detectResearchScope([
      eaf(extract(3, 'Mouthing', ['Gloss'])),
      eaf(extract(3, 'Mouthing', ['Gloss', 'Notes'])),
    ]);
    expect(scope).toEqual({
      topicId: 3,
      topicName: 'Mouthing',
      tiers: ['Gloss', 'Notes'],
    });
  });

  it('leaves the topic unknown when copies disagree', async () => {
    const scope = await detectResearchScope([
      eaf(extract(3, 'Mouthing', ['Gloss'])),
      eaf(extract(4, 'Glossing', ['Notes'])),
    ]);
    expect(scope.topicId).toBeNull();
    expect(scope.topicName).toBeNull();
  });
});
