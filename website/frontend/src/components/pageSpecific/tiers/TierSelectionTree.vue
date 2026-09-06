<template>
  <ul class="tier-selection-tree" :class="{ 'tier-selection-tree--root': root }">
    <li v-for="tier in tiers" :key="tier.tier_id">
      <label class="tier-selection-option">
        <input
          type="checkbox"
          :checked="selectedNames.has(tier.tier_name) || automaticNames.has(tier.tier_name)"
          :disabled="automaticNames.has(tier.tier_name) && !selectedNames.has(tier.tier_name)"
          @change="$emit('toggle', tier.tier_name)"
        />
        <span class="tier-selection-option__name">{{ tier.tier_name }}</span>
        <span
          v-if="automaticNames.has(tier.tier_name) && !selectedNames.has(tier.tier_name)"
          class="tier-selection-option__automatic"
        >
          Required parent
        </span>
        <span v-if="tier.children?.length" class="tier-selection-option__meta">
          {{ tier.children.length }} related
        </span>
      </label>
      <TierSelectionTree
        v-if="tier.children?.length"
        :tiers="tier.children"
        :selected-names="selectedNames"
        :automatic-names="automaticNames"
        @toggle="$emit('toggle', $event)"
      />
    </li>
  </ul>
</template>

<script setup>
defineOptions({ name: 'TierSelectionTree' });
defineProps({
  tiers: { type: Array, required: true },
  selectedNames: { type: Set, required: true },
  automaticNames: { type: Set, default: () => new Set() },
  root: { type: Boolean, default: false },
});
defineEmits(['toggle']);
</script>
