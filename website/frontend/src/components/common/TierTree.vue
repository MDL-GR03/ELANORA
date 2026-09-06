<template>
  <div class="tiers-tree-container">
    <button
      type="button"
      class="tiers-tree-group-label"
      :aria-expanded="open"
      :aria-controls="contentId"
      @click="toggleGroup"
    >
      <font-awesome-icon
        icon="fa-solid fa-chevron-right"
        class="tiers-tree-toggle"
        :class="{ 'tiers-tree-toggle--open': open }"
      />
      <font-awesome-icon
        icon="fa-solid fa-file-code"
        class="tiers-tree-file-icon"
      />
      <span class="tiers-tree-group-name">{{ groupLabel }}</span>
      <span class="tiers-tree-count">{{
        t('tiersPage.tierCount', { count: tiers.length })
      }}</span>
    </button>
    <div v-if="open" :id="contentId" class="tiers-tree-content">
      <ul v-if="sortedRootTiers.length" class="tiers-tree-root">
        <TierNode
          v-for="rootTier in sortedRootTiers"
          :key="rootTier.tier_id"
          :tier="rootTier"
        />
      </ul>
      <p v-else class="tiers-tree-empty">{{ t('tiersPage.noTiers') }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import TierNode from './TierNode.vue';

const props = defineProps({
  tiers: { type: Array, required: true },
  groupId: { type: [Number, String], required: true },
  groupLabel: { type: String, default: '' },
});

const { t } = useI18n();
const open = ref(false);
const contentId = computed(() => `tier-group-content-${props.groupId}`);

const sortedRootTiers = computed(() => {
  const folders = props.tiers
    .filter((tier) => Array.isArray(tier.children) && tier.children.length > 0)
    .toSorted((a, b) => a.tier_name.localeCompare(b.tier_name));
  const leaves = props.tiers
    .filter(
      (tier) => !Array.isArray(tier.children) || tier.children.length === 0
    )
    .toSorted((a, b) => a.tier_name.localeCompare(b.tier_name));
  return [...folders, ...leaves];
});

function toggleGroup() {
  open.value = !open.value;
}
</script>

<style scoped>
.tiers-tree-container {
  min-width: 0;
  flex: 1;
}

.tiers-tree-group-label {
  width: 100%;
  min-height: 2.75rem;
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.55rem 0.2rem;
  border: 0;
  color: var(--color-text);
  background: transparent;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.tiers-tree-group-label:focus-visible {
  border-radius: 0.4rem;
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

.tiers-tree-toggle {
  width: 0.7rem;
  color: var(--color-text-muted);
  transition: transform 150ms ease;
}

.tiers-tree-toggle--open {
  transform: rotate(90deg);
}

.tiers-tree-file-icon {
  color: var(--primary-color);
}

.tiers-tree-group-name {
  min-width: 0;
  overflow: hidden;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tiers-tree-count {
  margin-left: auto;
  color: var(--color-text-muted);
  font-size: 0.78rem;
  white-space: nowrap;
}

.tiers-tree-content {
  max-height: 28rem;
  margin: 0.25rem 0 0.6rem 1.25rem;
  padding: 0.75rem 0.75rem 0.4rem;
  overflow: auto;
  border-left: 2px solid color-mix(in srgb, var(--primary-color) 22%, white);
}

.tiers-tree-root {
  margin: 0;
  padding: 0;
  list-style: none;
}

.tiers-tree-empty {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 0.88rem;
}
</style>
