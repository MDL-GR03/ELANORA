<template>
  <div class="contributions-toolbar">
    <div>
      <h2>{{ t('pendingUploads.queueTitle') }}</h2>
      <p>{{ t('pendingUploads.queueDescription') }}</p>
    </div>
  </div>

  <div class="uploads-summary">
    <button
      type="button"
      class="summary-card"
      :class="{ selected: filter === 'all' }"
      @click="$emit('update:filter', 'all')"
    >
      <font-awesome-icon icon="fa-solid fa-inbox" />
      <h3>{{ total }}</h3>
      <p>{{ t('contributionWorkspace.summary.all') }}</p>
    </button>
    <button
      type="button"
      class="summary-card ready"
      :class="{ selected: filter === 'ready' }"
      @click="$emit('update:filter', 'ready')"
    >
      <font-awesome-icon icon="fa-solid fa-circle-check" />
      <h3>{{ ready }}</h3>
      <p>{{ t('pendingUploads.summary.readyToMerge') }}</p>
    </button>
    <button
      type="button"
      class="summary-card corrections"
      :class="{ selected: filter === 'corrections' }"
      @click="$emit('update:filter', 'corrections')"
    >
      <font-awesome-icon icon="fa-solid fa-clock" />
      <h3>{{ corrections }}</h3>
      <p>{{ t('contributionWorkspace.summary.corrections') }}</p>
    </button>
    <button
      type="button"
      class="summary-card conflicts"
      :class="{ selected: filter === 'resolution' }"
      @click="$emit('update:filter', 'resolution')"
    >
      <font-awesome-icon icon="fa-solid fa-triangle-exclamation" />
      <h3>{{ conflicts }}</h3>
      <p>{{ t('pendingUploads.summary.needResolution') }}</p>
    </button>
  </div>

  <div class="queue-filters">
    <div class="queue-filter-field queue-search-field">
      <label for="incoming-work-search">{{
        t('contributionWorkspace.search.label')
      }}</label>
      <div class="queue-search-row">
        <div class="queue-search-control">
          <font-awesome-icon icon="fa-solid fa-magnifying-glass" />
          <input
            id="incoming-work-search"
            :value="query"
            type="search"
            :placeholder="t('contributionWorkspace.search.placeholder')"
            aria-describedby="incoming-work-search-help incoming-work-search-count"
            @input="$emit('update:query', $event.target.value.trim())"
          />
        </div>
        <span id="incoming-work-search-count" aria-live="polite">
          {{
            t('contributionWorkspace.search.results', { count: resultCount })
          }}
        </span>
      </div>
      <small id="incoming-work-search-help">
        {{ t('contributionWorkspace.search.example') }}
      </small>
    </div>
    <div class="queue-filter-field queue-order-field">
      <label for="incoming-work-order">{{
        t('contributionWorkspace.order.label')
      }}</label>
      <AppSelect
        id="incoming-work-order"
        :model-value="sort"
        :aria-label="t('contributionWorkspace.order.aria')"
        :options="sortOptions"
        @update:model-value="$emit('update:sort', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import AppSelect from '@/components/common/AppSelect.vue';

defineProps({
  filter: { type: String, required: true },
  query: { type: String, required: true },
  sort: { type: String, required: true },
  total: { type: Number, required: true },
  ready: { type: Number, required: true },
  corrections: { type: Number, required: true },
  conflicts: { type: Number, required: true },
  resultCount: { type: Number, required: true },
});

defineEmits(['update:filter', 'update:query', 'update:sort']);

const { t } = useI18n();
const sortOptions = computed(() => [
  { value: 'oldest', label: t('contributionWorkspace.order.oldest') },
  { value: 'newest', label: t('contributionWorkspace.order.newest') },
]);
</script>
