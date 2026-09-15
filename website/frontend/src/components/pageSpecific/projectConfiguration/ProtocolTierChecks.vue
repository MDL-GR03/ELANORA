<template>
  <div v-if="tiers.length" class="table-scroll">
    <table>
      <caption>
        Checks applied to the annotations of each required tier
      </caption>
      <thead>
        <tr>
          <th scope="col">Tier</th>
          <th v-for="check in TIER_CHECKS" :key="check.key" scope="col">
            {{ check.label }}
          </th>
          <th scope="col">Content language</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="tier in tiers" :key="tier">
          <th scope="row">{{ tier }}</th>
          <td v-for="check in TIER_CHECKS" :key="check.key">
            <input
              type="checkbox"
              :checked="(modelValue[check.key] || []).includes(tier)"
              :aria-label="`${check.label}: ${tier}`"
              @change="
                emit(
                  'update:modelValue',
                  withTierCheck(
                    modelValue,
                    check.key,
                    tier,
                    $event.target.checked
                  )
                )
              "
            />
          </td>
          <td>
            <input
              class="language"
              :value="modelValue.tier_languages?.[tier] || ''"
              :aria-label="`Content language of ${tier}`"
              placeholder="Any"
              @change="
                emit(
                  'update:modelValue',
                  withMappingValue(
                    modelValue,
                    'tier_languages',
                    tier,
                    $event.target.value.trim()
                  )
                )
              "
            />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  <p v-else class="empty">
    Add required tiers above to check the annotations they contain.
  </p>
</template>

<script setup>
import { computed } from 'vue';
import {
  TIER_CHECKS,
  withMappingValue,
  withTierCheck,
} from '@/utils/protocolRules';

const props = defineProps({
  modelValue: {
    type: Object,
    required: true,
  },
});
const emit = defineEmits(['update:modelValue']);

const tiers = computed(() => props.modelValue.required_tiers || []);
</script>

<style scoped>
.table-scroll {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.84rem;
}

caption {
  padding-bottom: 0.5rem;
  color: #475569;
  font-size: 0.78rem;
  font-weight: 750;
  text-align: left;
}

th,
td {
  padding: 0.5rem 0.6rem;
  border-bottom: 1px solid #e2e8f0;
  text-align: center;
}

thead th {
  color: #475569;
  font-size: 0.74rem;
  font-weight: 750;
}

tbody th {
  max-width: 14rem;
  overflow: hidden;
  color: #14213d;
  text-align: left;
  text-overflow: ellipsis;
}

input[type='checkbox'] {
  width: 1.1rem;
  height: 1.1rem;
}

.language {
  width: 6rem;
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  padding: 0.4rem 0.5rem;
  font: inherit;
}

.empty {
  margin: 0;
  padding: 1rem;
  border: 1px dashed #cbd5e1;
  border-radius: 0.7rem;
  color: #64748b;
  text-align: center;
}
</style>
