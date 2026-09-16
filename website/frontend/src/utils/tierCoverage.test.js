import { describe, expect, it } from 'vitest';

import {
  allTierNamesOf,
  automaticParentNames,
  filesCoveringTopic,
  filesWithTier,
  rankGroupsForTopic,
  topicCoverageRows,
  uniqueBestGroup,
} from './tierCoverage';

const tier = (tier_name, children = []) => ({ tier_name, children });
const groups = [
  {
    tier_group_id: 1,
    elan_file_name: 'b.eaf',
    tiers: [tier('Gloss', [tier('Translation')])],
  },
  {
    tier_group_id: 2,
    elan_file_name: 'a.eaf',
    tiers: [tier('Gloss'), tier('Mouthing')],
  },
  { tier_group_id: 3, elan_file_name: 'c.eaf', tiers: [tier('Notes')] },
];
const topic = { tier_names: ['Gloss', 'Translation'] };

describe('tier coverage', () => {
  it('ranks files by topic coverage, then by name', () => {
    expect(
      rankGroupsForTopic(groups, topic).map((g) => g.elan_file_name)
    ).toEqual(['b.eaf', 'a.eaf', 'c.eaf']);
    expect(
      rankGroupsForTopic(groups, null).map((g) => g.elan_file_name)
    ).toEqual(['a.eaf', 'b.eaf', 'c.eaf']);
  });

  it('recommends a best file only when it is not tied', () => {
    const ranked = rankGroupsForTopic(groups, topic);
    expect(uniqueBestGroup(ranked, topic)?.elan_file_name).toBe('b.eaf');
    expect(uniqueBestGroup(ranked, { tier_names: ['Gloss'] })).toBeNull();
    expect(uniqueBestGroup(ranked, { tier_names: ['Absent'] })).toBeNull();
  });

  it('counts and lists files by tier, including nested tiers', () => {
    expect(filesCoveringTopic(groups, topic)).toBe(2);
    expect(filesWithTier(groups, 'Translation')).toEqual(['b.eaf']);
    expect(allTierNamesOf(groups)).toEqual([
      'Gloss',
      'Mouthing',
      'Notes',
      'Translation',
    ]);
  });

  it('builds coverage rows for files that contain the topic', () => {
    expect(topicCoverageRows(groups, topic)).toEqual([
      { filename: 'b.eaf', matches: ['Gloss', 'Translation'], percent: 100 },
      { filename: 'a.eaf', matches: ['Gloss'], percent: 50 },
    ]);
  });

  it('keeps unselected parents of selected tiers', () => {
    const tiers = [tier('Root', [tier('Middle', [tier('Leaf')])])];
    expect([...automaticParentNames(tiers, new Set(['Leaf']))]).toEqual([
      'Root',
      'Middle',
    ]);
    expect([...automaticParentNames(tiers, new Set(['Root', 'Leaf']))]).toEqual(
      ['Middle']
    );
  });
});
