<template>
  <ul
    v-if="ruleKeys.length"
    class="severities"
    :aria-label="t('protocolRules.enforcement.list')"
  >
    <li v-for="key in ruleKeys" :key="key">
      <span>{{ t(`protocolRules.labels.${key}`) }}</span>
      <AppSelect
        :id="`protocol-severity-${key}`"
        :model-value="severityOf(modelValue, key)"
        size="small"
        :aria-label="
          t('protocolRules.enforcement.when_not_met', {
            rule: t(`protocolRules.labels.${key}`),
          })
        "
        :options="options"
        @change="
          emit('update:modelValue', withSeverity(modelValue, key, $event))
        "
      />
    </li>
  </ul>
  <p v-else class="empty">{{ t('protocolRules.enforcement.empty') }}</p>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import AppSelect from '@/components/common/AppSelect.vue';
import {
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

const { t } = useI18n();

const options = computed(() => [
  { value: 'error', label: t('protocolRules.enforcement.refuse') },
  { value: 'warning', label: t('protocolRules.enforcement.warn') },
]);

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
  border: 1px solid var(--color-gray-200);
  border-radius: 0.7rem;
  background: var(--color-gray-50-alt);
  color: var(--color-slate-900);
  font-size: 0.86rem;
  font-weight: 700;
}

.empty {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 0.86rem;
}

@media (width <= 640px) {
  li {
    grid-template-columns: 1fr;
  }
}
</style>
