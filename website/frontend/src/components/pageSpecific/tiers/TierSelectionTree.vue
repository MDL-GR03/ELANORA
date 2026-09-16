<template>
  <ul
    class="tier-selection-tree"
    :class="{ 'tier-selection-tree--root': root }"
  >
    <li v-for="tier in tiers" :key="tier.tier_id">
      <label class="tier-selection-option">
        <input
          type="checkbox"
          :checked="
            selectedNames.has(tier.tier_name) ||
            automaticNames.has(tier.tier_name) ||
            contextNames.has(tier.tier_name) ||
            correctionNames.has(tier.tier_name)
          "
          :disabled="
            contextNames.has(tier.tier_name) ||
            correctionNames.has(tier.tier_name) ||
            (automaticNames.has(tier.tier_name) &&
              !selectedNames.has(tier.tier_name))
          "
          @change="$emit('toggle', tier.tier_name)"
        />
        <span class="tier-selection-option__name">{{ tier.tier_name }}</span>
        <span
          v-if="contextNames.has(tier.tier_name)"
          class="tier-selection-option__automatic"
        >
          {{ t('tierSelection.protectedContext') }}
        </span>
        <span
          v-else-if="correctionNames.has(tier.tier_name)"
          class="tier-selection-option__correction"
        >
          {{ t('tierSelection.baselineCorrection') }}
        </span>
        <span
          v-else-if="
            automaticNames.has(tier.tier_name) &&
            !selectedNames.has(tier.tier_name)
          "
          class="tier-selection-option__automatic"
        >
          {{ t('tierSelection.requiredParent') }}
        </span>
        <span v-if="tier.children?.length" class="tier-selection-option__meta">
          {{ t('tierSelection.related', { count: tier.children.length }) }}
        </span>
      </label>
      <TierSelectionTree
        v-if="tier.children?.length"
        :tiers="tier.children"
        :selected-names="selectedNames"
        :automatic-names="automaticNames"
        :context-names="contextNames"
        :correction-names="correctionNames"
        @toggle="$emit('toggle', $event)"
      />
    </li>
  </ul>
</template>

<script setup>
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
defineOptions({ name: 'TierSelectionTree' });
defineProps({
  tiers: { type: Array, required: true },
  selectedNames: { type: Set, required: true },
  automaticNames: { type: Set, default: () => new Set() },
  contextNames: { type: Set, default: () => new Set() },
  correctionNames: { type: Set, default: () => new Set() },
  root: { type: Boolean, default: false },
});
defineEmits(['toggle']);
</script>
