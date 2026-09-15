<template>
  <div class="type-constraints">
    <ul v-if="constraints.length" aria-label="Linguistic type constraints">
      <li v-for="[typeId, stereotype] in constraints" :key="typeId">
        <strong>{{ typeId }}</strong>
        <AppSelect
          :id="`protocol-constraint-${typeId}`"
          :model-value="stereotype"
          size="small"
          :aria-label="`Constraint required for ${typeId}`"
          :options="CONSTRAINT_STEREOTYPES"
          @change="setConstraint(typeId, $event)"
        />
        <button
          class="remove-button"
          type="button"
          :aria-label="`Remove constraint rule for ${typeId}`"
          @click="setConstraint(typeId, '')"
        >
          Remove
        </button>
      </li>
    </ul>
    <div class="add-constraint">
      <label>
        Linguistic type
        <input
          v-model.trim="newType"
          placeholder="For example: gloss-type"
          @keydown.enter.prevent="add"
        />
      </label>
      <label for="new-protocol-constraint">
        Required constraint
        <AppSelect
          id="new-protocol-constraint"
          v-model="newStereotype"
          size="small"
          :options="CONSTRAINT_STEREOTYPES"
        />
      </label>
      <button type="button" :disabled="!newType" @click="add">
        Add constraint rule
      </button>
    </div>
    <p v-if="duplicate" class="field-error" role="alert">
      “{{ duplicate }}” already has a constraint rule.
    </p>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import AppSelect from '@/components/common/AppSelect.vue';
import {
  CONSTRAINT_STEREOTYPES,
  withMappingValue,
} from '@/utils/protocolRules';

const props = defineProps({
  modelValue: {
    type: Object,
    required: true,
  },
});
const emit = defineEmits(['update:modelValue']);

const newType = ref('');
const newStereotype = ref('none');
const duplicate = ref('');

const constraints = computed(() =>
  Object.entries(props.modelValue.linguistic_type_constraints || {})
);

const setConstraint = (typeId, stereotype) =>
  emit(
    'update:modelValue',
    withMappingValue(
      props.modelValue,
      'linguistic_type_constraints',
      typeId,
      stereotype
    )
  );

const add = () => {
  const typeId = newType.value.trim();
  if (!typeId) return;
  if (props.modelValue.linguistic_type_constraints?.[typeId]) {
    duplicate.value = typeId;
    return;
  }
  duplicate.value = '';
  setConstraint(typeId, newStereotype.value);
  newType.value = '';
  newStereotype.value = 'none';
};
</script>

<style scoped>
.type-constraints {
  display: grid;
  gap: 0.75rem;
}

ul {
  display: grid;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

li {
  display: grid;
  grid-template-columns: minmax(10rem, 1fr) minmax(12rem, 1fr) auto;
  align-items: center;
  gap: 0.65rem;
  padding: 0.6rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 0.7rem;
  background: #fbfdff;
}

li strong {
  overflow: hidden;
  text-overflow: ellipsis;
}

.add-constraint {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  align-items: end;
  gap: 0.65rem;
}

label {
  display: grid;
  gap: 0.3rem;
  color: #475569;
  font-size: 0.75rem;
  font-weight: 750;
}

input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  border-radius: 0.55rem;
  padding: 0.6rem 0.7rem;
  background: #fff;
  color: #14213d;
  font: inherit;
  font-size: 0.86rem;
}

button {
  min-height: 2.45rem;
  border: 0;
  border-radius: 0.6rem;
  padding: 0.6rem 0.85rem;
  background: #2563eb;
  color: #fff;
  font: inherit;
  font-size: 0.82rem;
  font-weight: 750;
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.remove-button {
  border: 1px solid #fecaca;
  background: #fff;
  color: #b91c1c;
}

.field-error {
  margin: 0;
  color: #b45309;
  font-size: 0.8rem;
}

@media (width <= 640px) {
  li,
  .add-constraint {
    grid-template-columns: 1fr;
    align-items: stretch;
  }
}
</style>
