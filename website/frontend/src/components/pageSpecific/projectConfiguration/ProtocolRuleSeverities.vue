<template>
  <ul v-if="ruleKeys.length" class="severities" aria-label="Rule enforcement">
    <li v-for="key in ruleKeys" :key="key">
      <span>{{ RULE_LABELS[key] }}</span>
      <AppSelect
        :id="`protocol-severity-${key}`"
        :model-value="severityOf(modelValue, key)"
        size="small"
        :aria-label="`${RULE_LABELS[key]}: when not met`"
        :options="options"
        @change="
          emit('update:modelValue', withSeverity(modelValue, key, $event))
        "
      />
    </li>
  </ul>
  <p v-else class="empty">Rules you add above can be enforced here.</p>
</template>

<script setup>
import { computed } from 'vue';
import AppSelect from '@/components/common/AppSelect.vue';
import {
  RULE_LABELS,
  configuredRuleKeys,
  severityOf,
  withSeverity,
} from '@/utils/protocolRules';

const props = defineProps({
  modelValue: {
    type: Object,
    required: true,
  },
});
const emit = defineEmits(['update:modelValue']);

const options = [
  { value: 'error', label: 'Refuse the file' },
  { value: 'warning', label: 'Accept and warn reviewers' },
];

const ruleKeys = computed(() => configuredRuleKeys(props.modelValue));
</script>

<style scoped>
.severities {
  display: grid;
  gap: 0.45rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

li {
  display: grid;
  grid-template-columns: minmax(10rem, 1fr) minmax(13rem, 18rem);
  align-items: center;
  gap: 0.65rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 0.7rem;
  background: #fbfdff;
  color: #14213d;
  font-size: 0.86rem;
  font-weight: 700;
}

.empty {
  margin: 0;
  color: #64748b;
  font-size: 0.86rem;
}

@media (width <= 640px) {
  li {
    grid-template-columns: 1fr;
  }
}
</style>
