import { describe, expect, it } from 'vitest';
import {
  findSimilarResearchTopic,
  normalizeResearchTopicName,
} from './researchTopics';

describe('research topic suggestions', () => {
  const topics = [
    { topic_id: 1, name: 'Prosody' },
    { topic_id: 2, name: 'Gaze' },
  ];

  it('normalizes case, accents, punctuation, and spacing', () => {
    expect(normalizeResearchTopicName('  PROSÓDY---Analysis ')).toBe(
      'prosody analysis'
    );
  });

  it('suggests Prosody for a close typo without selecting it', () => {
    expect(findSimilarResearchTopic('prozody', topics)).toEqual(topics[0]);
  });

  it('leaves a distinct topic available as a new proposal', () => {
    expect(findSimilarResearchTopic('Turn taking', topics)).toBeNull();
  });
});
