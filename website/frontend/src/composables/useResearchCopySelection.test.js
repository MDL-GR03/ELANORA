import { nextTick, ref } from 'vue';
import { describe, expect, it } from 'vitest';

import { useResearchCopySelection } from './useResearchCopySelection';

const tier = (tier_name, children = []) => ({ tier_name, children });

function setup({ groupCount = 2 } = {}) {
  const tierGroups = ref([
    {
      tier_group_id: 1,
      elan_file_name: 'a.eaf',
      tiers: [tier('Role', [tier('Gloss')]), tier('Notes')],
    },
    {
      tier_group_id: 2,
      elan_file_name: 'b.eaf',
      tiers: [tier('Role', [tier('Gloss'), tier('Translation')])],
    },
    ...Array.from({ length: groupCount - 2 }, (_, index) => ({
      tier_group_id: 10 + index,
      elan_file_name: `z${String(index).padStart(2, '0')}.eaf`,
      tiers: [],
    })),
  ]);
  const topics = ref([
    { topic_id: 7, name: 'Glossing', tier_names: ['Gloss', 'Translation'] },
  ]);
  const baselineTiers = ref(['Role']);
  return useResearchCopySelection({ tierGroups, topics, baselineTiers });
}

describe('useResearchCopySelection', () => {
  it('applies a topic to its best file without selecting baseline tiers', () => {
    const selection = setup();
    selection.applyTopic({
      topic_id: 7,
      tier_names: ['Gloss', 'Translation', 'Role'],
    });

    expect(selection.selectedGroup.value.elan_file_name).toBe('b.eaf');
    expect([...selection.selectedTierNames.value]).toEqual([
      'Gloss',
      'Translation',
    ]);
    expect([...selection.includedBaselineNames.value]).toEqual(['Role']);
    expect(selection.bestGroupId.value).toBe(2);
    expect(selection.canDownload.value).toBe(true);
  });

  it('never toggles a baseline tier as a research tier', () => {
    const selection = setup();
    selection.selectGroup(selection.filteredGroups.value[0]);
    selection.toggleTier('Role');
    selection.toggleTier('Notes');
    expect([...selection.selectedTierNames.value]).toEqual(['Notes']);
    selection.selectAllTiers();
    expect([...selection.selectedTierNames.value].sort()).toEqual([
      'Gloss',
      'Notes',
    ]);
  });

  it('includes a baseline tier marked for correction and drops the mark when excluded', () => {
    const selection = setup();
    selection.selectGroup(selection.filteredGroups.value[0]);
    selection.toggleAllBaselineContext();
    expect(selection.includedBaselineNames.value.size).toBe(0);

    selection.toggleEditableBaseline('Role');
    expect(selection.includedBaselineNames.value.has('Role')).toBe(true);
    expect(selection.protectedBaselineNames.value.size).toBe(0);
    expect(selection.canDownload.value).toBe(true);

    selection.toggleIncludedBaseline('Role');
    expect(selection.includedBaselineNames.value.has('Role')).toBe(false);
    expect(selection.editableBaselineNames.value.has('Role')).toBe(false);
  });

  it('paginates files and returns to the first page on a new search', async () => {
    const selection = setup({ groupCount: 23 });
    expect(selection.filePageCount.value).toBe(3);
    selection.filePage.value = 3;
    expect(selection.visibleGroups.value).toHaveLength(3);

    selection.fileSearch.value = 'z1';
    await nextTick();
    expect(selection.filePage.value).toBe(1);
    expect(selection.filteredGroups.value).toHaveLength(10);
  });
});
