import { computed, ref, watch } from 'vue';

import {
  automaticParentNames,
  rankGroupsForTopic,
  tierNamesOf,
  uniqueBestGroup,
} from '@/utils/tierCoverage';

export const RESEARCH_FILE_PAGE_SIZE = 10;

function toggled(set, name) {
  const next = new Set(set);
  if (next.has(name)) next.delete(name);
  else next.add(name);
  return next;
}

/**
 * The choices behind one research-copy download: a topic, a file, the
 * research tiers to include, and which protected baseline tiers travel with
 * the copy as read-only context or as proposed corrections.
 *
 * Baseline tiers are never research tiers: they can only be included as
 * context, and marking one for correction includes it.
 */
export function useResearchCopySelection({
  tierGroups,
  topics,
  baselineTiers,
}) {
  const selectedGroupId = ref(null);
  const selectedTopicId = ref(null);
  const selectedTierNames = ref(new Set());
  const includedBaselineNames = ref(new Set());
  const editableBaselineNames = ref(new Set());
  const fileSearch = ref('');
  const filePage = ref(1);

  const selectedGroup = computed(() =>
    tierGroups.value.find(
      (group) => group.tier_group_id === selectedGroupId.value
    )
  );
  const selectedTopic = computed(() =>
    topics.value.find((topic) => topic.topic_id === selectedTopicId.value)
  );
  const currentTierNames = computed(() => tierNamesOf(selectedGroup.value));
  const baselineNames = computed(() => new Set(baselineTiers.value));
  const availableBaselineTiers = computed(() =>
    baselineTiers.value.filter((name) => currentTierNames.value.has(name))
  );
  const protectedBaselineNames = computed(
    () =>
      new Set(
        [...includedBaselineNames.value].filter(
          (name) => !editableBaselineNames.value.has(name)
        )
      )
  );
  const allBaselineIncluded = computed(
    () =>
      availableBaselineTiers.value.length > 0 &&
      availableBaselineTiers.value.every((name) =>
        includedBaselineNames.value.has(name)
      )
  );
  const missingTopicTiers = computed(() =>
    (selectedTopic.value?.tier_names || []).filter(
      (name) => !currentTierNames.value.has(name)
    )
  );
  const automaticParents = computed(() =>
    automaticParentNames(selectedGroup.value?.tiers, selectedTierNames.value)
  );
  const canDownload = computed(
    () =>
      Boolean(selectedGroup.value) &&
      (selectedTierNames.value.size > 0 || editableBaselineNames.value.size > 0)
  );

  const rankedGroups = computed(() =>
    rankGroupsForTopic(tierGroups.value, selectedTopic.value)
  );
  const bestGroupId = computed(
    () =>
      uniqueBestGroup(rankedGroups.value, selectedTopic.value)?.tier_group_id ??
      null
  );
  const filteredGroups = computed(() => {
    const query = fileSearch.value.trim().toLowerCase();
    return rankedGroups.value.filter(
      (group) => !query || group.elan_file_name.toLowerCase().includes(query)
    );
  });
  const filePageCount = computed(() =>
    Math.max(
      1,
      Math.ceil(filteredGroups.value.length / RESEARCH_FILE_PAGE_SIZE)
    )
  );
  const visibleGroups = computed(() => {
    const start = (filePage.value - 1) * RESEARCH_FILE_PAGE_SIZE;
    return filteredGroups.value.slice(start, start + RESEARCH_FILE_PAGE_SIZE);
  });
  watch(fileSearch, () => {
    filePage.value = 1;
  });

  function selectGroup(group) {
    const names = tierNamesOf(group);
    selectedGroupId.value = group.tier_group_id;
    selectedTierNames.value = new Set(
      (selectedTopic.value?.tier_names || []).filter(
        (name) => names.has(name) && !baselineNames.value.has(name)
      )
    );
    includedBaselineNames.value = new Set(
      baselineTiers.value.filter((name) => names.has(name))
    );
    editableBaselineNames.value = new Set();
  }

  function applyTopic(topic) {
    selectedTopicId.value = topic?.topic_id ?? null;
    fileSearch.value = '';
    filePage.value = 1;
    const target = topic
      ? rankGroupsForTopic(tierGroups.value, topic)[0]
      : selectedGroup.value || tierGroups.value[0];
    if (target) selectGroup(target);
    else selectedTierNames.value = new Set();
  }

  function toggleTier(name) {
    if (baselineNames.value.has(name)) return;
    selectedTierNames.value = toggled(selectedTierNames.value, name);
  }

  function selectAllTiers() {
    selectedTierNames.value = new Set(
      [...currentTierNames.value].filter(
        (name) => !baselineNames.value.has(name)
      )
    );
  }

  function clearSelectedTiers() {
    selectedTierNames.value = new Set();
  }

  function toggleIncludedBaseline(name) {
    if (includedBaselineNames.value.has(name)) {
      editableBaselineNames.value = new Set(
        [...editableBaselineNames.value].filter((item) => item !== name)
      );
    }
    includedBaselineNames.value = toggled(includedBaselineNames.value, name);
  }

  function toggleEditableBaseline(name) {
    if (!editableBaselineNames.value.has(name)) {
      includedBaselineNames.value = new Set([
        ...includedBaselineNames.value,
        name,
      ]);
    }
    editableBaselineNames.value = toggled(editableBaselineNames.value, name);
  }

  function toggleAllBaselineContext() {
    if (allBaselineIncluded.value) {
      includedBaselineNames.value = new Set();
      editableBaselineNames.value = new Set();
    } else {
      includedBaselineNames.value = new Set(availableBaselineTiers.value);
    }
  }

  function reset() {
    selectedGroupId.value = null;
    selectedTopicId.value = null;
    selectedTierNames.value = new Set();
    includedBaselineNames.value = new Set();
    editableBaselineNames.value = new Set();
    fileSearch.value = '';
    filePage.value = 1;
  }

  return {
    selectedGroupId,
    selectedTopicId,
    selectedGroup,
    selectedTopic,
    selectedTierNames,
    includedBaselineNames,
    editableBaselineNames,
    protectedBaselineNames,
    availableBaselineTiers,
    allBaselineIncluded,
    missingTopicTiers,
    automaticParents,
    canDownload,
    fileSearch,
    filePage,
    filePageCount,
    filteredGroups,
    visibleGroups,
    bestGroupId,
    selectGroup,
    applyTopic,
    toggleTier,
    selectAllTiers,
    clearSelectedTiers,
    toggleIncludedBaseline,
    toggleEditableBaseline,
    toggleAllBaselineContext,
    reset,
  };
}
