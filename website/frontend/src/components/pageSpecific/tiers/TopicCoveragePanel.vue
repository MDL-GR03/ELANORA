<template>
  <div class="topic-coverage-panel">
    <label class="topic-coverage-search">
      <span class="sr-only">{{
        t('researchScopes.topics.searchInTopic', { topic: topic.name })
      }}</span>
      <font-awesome-icon icon="fa-solid fa-magnifying-glass" />
      <input v-model="search" :placeholder="t('researchScopes.searchFiles')" />
    </label>
    <div class="topic-tier-summary">
      <span v-for="name in topic.tier_names.slice(0, TIER_PREVIEW)" :key="name">
        {{ name }}
        <small>{{
          t('researchScopes.fileCount', {
            count: filesWithTier(tierGroups, name).length,
          })
        }}</small>
      </span>
      <span v-if="topic.tier_names.length > TIER_PREVIEW">
        {{
          t('researchScopes.topics.moreTiers', {
            count: topic.tier_names.length - TIER_PREVIEW,
          })
        }}
      </span>
    </div>
    <div v-if="!visibleRows.length" class="topic-coverage-empty">
      {{ t('researchScopes.topics.noMatchingFiles') }}
    </div>
    <div v-else class="topic-file-coverage-list">
      <div
        v-for="row in visibleRows"
        :key="row.filename"
        class="topic-file-coverage-row"
      >
        <div>
          <strong>{{ row.filename }}</strong>
          <span>{{
            t('researchScopes.topicTierCoverage', {
              available: row.matches.length,
              total: topic.tier_names.length,
            })
          }}</span>
        </div>
        <div
          class="topic-file-coverage-bar"
          :aria-label="
            t('researchScopes.topics.coverageAria', {
              available: row.matches.length,
              total: topic.tier_names.length,
            })
          "
        >
          <span :style="{ width: `${row.percent}%` }" />
        </div>
        <div class="topic-file-tier-names">
          <span v-for="name in row.matches.slice(0, 3)" :key="name">{{
            name
          }}</span>
          <small v-if="row.matches.length > 3"
            >+{{ row.matches.length - 3 }}</small
          >
        </div>
      </div>
    </div>
    <button
      v-if="filteredRows.length > limit"
      type="button"
      class="topic-show-more"
      @click="limit += PAGE"
    >
      {{
        t('researchScopes.topics.showMoreFiles', {
          count: Math.min(PAGE, filteredRows.length - limit),
        })
      }}
    </button>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { filesWithTier, topicCoverageRows } from '@/utils/tierCoverage';

const TIER_PREVIEW = 12;
const PAGE = 10;

const props = defineProps({
  topic: { type: Object, required: true },
  tierGroups: { type: Array, required: true },
});

const { t } = useI18n();
const search = ref('');
const limit = ref(PAGE);

const filteredRows = computed(() => {
  const query = search.value.trim().toLowerCase();
  return topicCoverageRows(props.tierGroups, props.topic).filter(
    (row) =>
      !query ||
      row.filename.toLowerCase().includes(query) ||
      row.matches.some((name) => name.toLowerCase().includes(query))
  );
});
const visibleRows = computed(() => filteredRows.value.slice(0, limit.value));
</script>
