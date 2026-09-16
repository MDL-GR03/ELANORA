<template>
  <ul class="tier-tree" :class="{ nested: depth > 0 }">
    <li v-for="node in nodes" :key="node.name">
      <div class="tier-node">
        <span class="tier-icon" aria-hidden="true">T</span>
        <span>
          <strong>{{ node.name }}</strong>
          <small>{{
            node.type || t('protocolRules.tiers.any_linguistic_type')
          }}</small>
        </span>
      </div>
      <ProtocolTierTree
        v-if="node.children.length"
        :nodes="node.children"
        :depth="depth + 1"
      />
    </li>
  </ul>
</template>

<script setup>
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

defineProps({
  nodes: {
    type: Array,
    required: true,
  },
  depth: {
    type: Number,
    default: 0,
  },
});
</script>

<style scoped>
.tier-tree {
  display: grid;
  gap: 0.65rem;
  padding: 0;
  margin: 0;
  list-style: none;
}

.tier-tree.nested {
  position: relative;
  margin: 2px 0 0 1.15rem;
  padding: 0.65rem 0 0 1.35rem;
  border-left: 2px solid #bfdbfe;
}

.tier-tree.nested::before {
  position: absolute;
  top: 1.65rem;
  left: 0;
  width: 1rem;
  border-top: 2px solid #bfdbfe;
  content: '';
}

.tier-node {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  width: fit-content;
  min-width: 13rem;
  padding: 0.65rem 0.8rem;
  border: 1px solid #dbeafe;
  border-radius: 0.7rem;
  background: #fff;
  box-shadow: 0 0.15rem 0.4rem rgb(15 23 42 / 5%);
}

.tier-node > span:last-child {
  display: grid;
  gap: 0.08rem;
}

.tier-node small {
  color: #64748b;
  font-size: 0.75rem;
}

.tier-icon {
  display: grid;
  width: 1.7rem;
  height: 1.7rem;
  place-items: center;
  border-radius: 0.5rem;
  background: #eff6ff;
  color: #2563eb;
  font-size: 0.72rem;
  font-weight: 900;
}
</style>
