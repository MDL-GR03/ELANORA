<template>
  <section class="research-step">
    <ResearchStepTitle
      number="2"
      :title="t('researchScopes.prepare.fileStepTitle')"
      :text="
        selectedTopic
          ? t('researchScopes.prepare.fileStepRanked')
          : t('researchScopes.prepare.fileStepText')
      "
    />
    <div class="research-file-picker">
      <div class="research-file-browser">
        <label class="research-file-search">
          <font-awesome-icon icon="fa-solid fa-magnifying-glass" />
          <span class="sr-only">{{ t('researchScopes.searchFiles') }}</span>
          <input
            v-model="fileSearch"
            :placeholder="t('researchScopes.searchFiles')"
          />
        </label>
        <div class="research-file-list">
          <button
            v-for="group in visibleGroups"
            :key="group.tier_group_id"
            type="button"
            :class="{ 'is-selected': selectedGroupId === group.tier_group_id }"
            @click="selectGroup(group)"
          >
            <span>
              <strong>{{ group.elan_file_name }}</strong>
              <small>{{ fileSummary(group) }}</small>
            </span>
            <span
              v-if="bestGroupId === group.tier_group_id"
              class="research-file-list__recommended"
              >{{ t('researchScopes.bestMatch') }}</span
            >
            <font-awesome-icon
              v-if="selectedGroupId === group.tier_group_id"
              icon="fa-solid fa-check"
              class="research-file-list__check"
            />
          </button>
        </div>
        <div v-if="!visibleGroups.length" class="research-file-empty">
          {{ t('researchScopes.noSearchResults') }}
        </div>
        <footer
          v-if="filteredGroups.length"
          class="research-file-pagination"
          :aria-label="t('researchScopes.pagination.label')"
        >
          <span>{{ resultRange }}</span>
          <div v-if="filePageCount > 1">
            <button
              type="button"
              :disabled="filePage === 1"
              :aria-label="t('researchScopes.pagination.previousLabel')"
              @click="filePage -= 1"
            >
              {{ t('researchScopes.pagination.previous') }}
            </button>
            <span>{{
              t('researchScopes.pagination.page', {
                page: filePage,
                total: filePageCount,
              })
            }}</span>
            <button
              type="button"
              :disabled="filePage === filePageCount"
              :aria-label="t('researchScopes.pagination.nextLabel')"
              @click="filePage += 1"
            >
              {{ t('researchScopes.pagination.next') }}
            </button>
          </div>
        </footer>
      </div>
    </div>
    <div v-if="selectedTopic" class="topic-coverage">
      <div>
        <strong>{{
          t('researchScopes.topicInFile', {
            topic: selectedTopic.name,
            file: selectedGroup?.elan_file_name,
          })
        }}</strong>
        <span>{{
          selectedTopic.description || t('researchScopes.noDescription')
        }}</span>
      </div>
      <span v-if="missingTopicTiers.length" class="topic-coverage__missing">{{
        t('researchScopes.coverageMissing', {
          available: selectedTopic.tier_names.length - missingTopicTiers.length,
          total: selectedTopic.tier_names.length,
          missing: missingTopicTiers.join(', '),
        })
      }}</span>
      <span v-else class="topic-coverage__complete">{{
        t('researchScopes.coverageComplete')
      }}</span>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import { RESEARCH_FILE_PAGE_SIZE } from '@/composables/useResearchCopySelection';
import { flattenTiers, topicCoverageOf } from '@/utils/tierCoverage';
import ResearchStepTitle from './ResearchStepTitle.vue';
import { useResearchCopyContext } from './researchCopyContext';

const { t } = useI18n();
const {
  selectedTopic,
  selectedGroup,
  selectedGroupId,
  missingTopicTiers,
  fileSearch,
  filePage,
  filePageCount,
  filteredGroups,
  visibleGroups,
  bestGroupId,
  selectGroup,
} = useResearchCopyContext();

function fileSummary(group) {
  return selectedTopic.value
    ? t('researchScopes.topicTierCoverage', {
        available: topicCoverageOf(group, selectedTopic.value),
        total: selectedTopic.value.tier_names.length,
      })
    : t('researchScopes.tierCount', {
        count: flattenTiers(group.tiers).length,
      });
}

const resultRange = computed(() => {
  const total = filteredGroups.value.length;
  if (!total) return t('researchScopes.pagination.empty');
  const first = (filePage.value - 1) * RESEARCH_FILE_PAGE_SIZE + 1;
  const last = Math.min(filePage.value * RESEARCH_FILE_PAGE_SIZE, total);
  return t('researchScopes.pagination.range', { first, last, total });
});
</script>
