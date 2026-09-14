<template>
  <div class="tier-group-row">
    <button
      type="button"
      class="tier-group-drag-handle"
      :aria-label="t('tiersPage.dragFile', { name: group.elan_file_name })"
      :title="t('tiersPage.dragHandle')"
    >
      <font-awesome-icon icon="fa-solid fa-grip-vertical" />
    </button>
    <TierTree
      :tiers="group.tiers"
      :group-label="group.elan_file_name"
      :group-id="group.tier_group_id"
    />
    <label
      class="tier-group-move-control"
      :for="`tier-group-section-${group.tier_group_id}`"
    >
      <span>{{ t('tiersPage.moveTo') }}</span>
      <AppSelect
        :id="`tier-group-section-${group.tier_group_id}`"
        :model-value="currentSectionId ?? ''"
        :disabled="disabled"
        size="small"
        :options="sectionOptions"
        @change="handleMove"
      />
    </label>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import TierTree from '@/components/common/TierTree.vue';
import AppSelect from '@/components/common/AppSelect.vue';

const props = defineProps({
  group: { type: Object, required: true },
  sections: { type: Array, required: true },
  currentSectionId: { type: Number, default: null },
  disabled: { type: Boolean, default: false },
});

const emit = defineEmits(['move']);
const { t } = useI18n();
const sectionOptions = computed(() => [
  ...props.sections.map((section) => ({
    value: section.section_id,
    label: section.name,
  })),
  { value: '', label: t('tiersPage.unsectioned') },
]);

function handleMove(value) {
  emit('move', value === '' ? null : Number(value));
}
</script>
