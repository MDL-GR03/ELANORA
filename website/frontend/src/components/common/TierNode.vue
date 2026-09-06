<template>
  <li class="tiers-tree-node">
    <button
      v-if="hasChildren"
      type="button"
      class="tiers-tree-label"
      :aria-expanded="open"
      @click="toggle"
    >
      <font-awesome-icon
        icon="fa-solid fa-chevron-right"
        class="tiers-tree-node-toggle"
        :class="{ 'tiers-tree-node-toggle--open': open }"
      />
      <font-awesome-icon
        icon="fa-solid fa-folder"
        class="tiers-tree-node-icon"
      />
      <span class="tiers-tree-tiername">{{ tier.tier_name }}</span>
      <span class="tiers-tree-children-count">{{ tier.children.length }}</span>
    </button>
    <div v-else class="tiers-tree-label tiers-tree-label--leaf">
      <span class="tiers-tree-node-toggle" aria-hidden="true"></span>
      <font-awesome-icon
        icon="fa-solid fa-tag"
        class="tiers-tree-node-icon tiers-tree-node-icon--leaf"
      />
      <span class="tiers-tree-tiername">{{ tier.tier_name }}</span>
    </div>
    <ul v-if="hasChildren && open" class="tiers-tree-children">
      <TierNode
        v-for="child in sortedChildren"
        :key="child.tier_id"
        :tier="child"
      />
    </ul>
  </li>
</template>

<script setup>
import { computed, ref } from 'vue';
import TierNode from './TierNode.vue';

const props = defineProps({
  tier: { type: Object, required: true },
});

const open = ref(false);
const hasChildren = computed(() => props.tier.children?.length > 0);
const sortedChildren = computed(() => {
  const children = props.tier.children || [];
  return children.toSorted((a, b) => {
    const aHasChildren = a.children?.length > 0;
    const bHasChildren = b.children?.length > 0;
    if (aHasChildren !== bHasChildren) return aHasChildren ? -1 : 1;
    return a.tier_name.localeCompare(b.tier_name);
  });
});

function toggle() {
  open.value = !open.value;
}
</script>

<style scoped>
.tiers-tree-node {
  margin: 0.15rem 0;
  list-style: none;
}

.tiers-tree-label {
  width: 100%;
  min-height: 2rem;
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.3rem 0.45rem;
  border: 0;
  border-radius: 0.4rem;
  color: var(--color-text);
  background: transparent;
  font: inherit;
  font-size: 0.9rem;
  text-align: left;
}

button.tiers-tree-label {
  cursor: pointer;
}

button.tiers-tree-label:hover {
  background: var(--color-surface-subtle);
}

button.tiers-tree-label:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 1px;
}

.tiers-tree-node-toggle {
  width: 0.55rem;
  height: 0.75rem;
  flex: none;
  color: var(--color-text-muted);
  transition: transform 150ms ease;
}

.tiers-tree-node-toggle--open {
  transform: rotate(90deg);
}

.tiers-tree-node-icon {
  color: #7c3aed;
}

.tiers-tree-node-icon--leaf {
  color: #0f766e;
}

.tiers-tree-tiername {
  min-width: 0;
  overflow-wrap: anywhere;
}

.tiers-tree-children-count {
  min-width: 1.45rem;
  margin-left: auto;
  padding: 0.05rem 0.35rem;
  border-radius: 999px;
  color: #6d28d9;
  background: #f3efff;
  font-size: 0.75rem;
  text-align: center;
}

.tiers-tree-children {
  margin: 0.1rem 0 0 1rem;
  padding-left: 0.65rem;
  border-left: 1px solid var(--color-border);
}
</style>
