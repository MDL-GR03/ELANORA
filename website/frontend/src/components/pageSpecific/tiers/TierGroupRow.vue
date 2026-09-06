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
    <label class="tier-group-move-control">
      <span>{{ t('tiersPage.moveTo') }}</span>
      <select
        :value="currentSectionId ?? ''"
        :disabled="disabled"
        @change="handleMove"
      >
        <option
          v-for="section in sections"
          :key="section.section_id"
          :value="section.section_id"
        >
          {{ section.name }}
        </option>
        <option value="">{{ t('tiersPage.unsectioned') }}</option>
      </select>
    </label>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n';
import TierTree from '@/components/common/TierTree.vue';

defineProps({
  group: { type: Object, required: true },
  sections: { type: Array, required: true },
  currentSectionId: { type: Number, default: null },
  disabled: { type: Boolean, default: false },
});

const emit = defineEmits(['move']);
const { t } = useI18n();

function handleMove(event) {
  const value = event.target.value;
  emit('move', value === '' ? null : Number(value));
}
</script>
