<template>
  <div class="topic-tier-picker">
    <label v-for="name in names" :key="name">
      <input
        type="checkbox"
        :checked="selected.has(name)"
        @change="emit('toggle', name)"
      />
      <span>{{ name }}</span>
      <small>{{
        t('researchScopes.fileCount', {
          count: filesWithTier(tierGroups, name).length,
        })
      }}</small>
    </label>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n';

import { filesWithTier } from '@/utils/tierCoverage';

defineProps({
  names: { type: Array, required: true },
  selected: { type: Set, required: true },
  tierGroups: { type: Array, required: true },
});
const emit = defineEmits(['toggle']);
const { t } = useI18n();
</script>
