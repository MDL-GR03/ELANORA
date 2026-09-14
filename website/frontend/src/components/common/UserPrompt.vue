<template>
  <div
    v-if="visible"
    class="prompt-backdrop"
    role="presentation"
    @mousedown.self="cancel"
  >
    <div
      ref="dialogElement"
      class="prompt-dialog"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="titleId"
    >
      <header class="prompt-header">
        <span class="prompt-icon"
          ><FontAwesomeIcon :icon="faPenToSquare"
        /></span>
        <div>
          <span class="prompt-eyebrow">Information required</span>
          <h2 :id="titleId">{{ title }}</h2>
        </div>
        <button
          type="button"
          class="prompt-close"
          aria-label="Cancel and close"
          @click="cancel"
        >
          <FontAwesomeIcon :icon="faXmark" />
        </button>
      </header>

      <form class="prompt-form" @submit.prevent="submit">
        <label :for="inputId">{{ message }}</label>
        <input
          :id="inputId"
          ref="inputElement"
          v-model="inputValue"
          :type="type"
          class="prompt-input"
          :aria-invalid="Boolean(warning)"
          :aria-describedby="warning ? warningId : undefined"
        />
        <div v-if="warning" :id="warningId" class="prompt-warning" role="alert">
          <FontAwesomeIcon :icon="faTriangleExclamation" />
          {{ warning }}
        </div>
        <footer class="prompt-actions">
          <button type="button" class="prompt-button secondary" @click="cancel">
            Cancel
          </button>
          <button type="submit" class="prompt-button primary">
            Save value
          </button>
        </footer>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, useId, watch } from 'vue';
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';
import {
  faPenToSquare,
  faTriangleExclamation,
  faXmark,
} from '@fortawesome/free-solid-svg-icons';
import { useModalDialog } from '@/composables/useModalDialog';

const props = defineProps({
  modelValue: Boolean,
  message: { type: String, default: '' },
  defaultValue: { type: [String, Number], default: '' },
  type: { type: String, default: 'number' },
  validator: { type: Function, default: null },
  title: { type: String, default: 'Enter a value' },
});
const emit = defineEmits(['update:modelValue', 'submit', 'cancel']);
const visible = ref(props.modelValue);
const inputValue = ref(props.defaultValue ?? '');
const warning = ref('');
const dialogElement = ref(null);
const inputElement = ref(null);
const generatedId = useId();
const titleId = `prompt-title-${generatedId}`;
const inputId = `user-prompt-value-${generatedId}`;
const warningId = `prompt-warning-${generatedId}`;

let wasVisible = false;
watch(
  () => props.modelValue,
  (value) => {
    visible.value = value;
    if (value && !wasVisible) {
      inputValue.value = props.defaultValue ?? '';
      validate(inputValue.value);
    }
    wasVisible = value;
  },
  { immediate: true }
);

watch(inputValue, (value) => {
  validate(value);
});

function validate(value) {
  const message = props.validator?.(value);
  warning.value = typeof message === 'string' ? message : '';
  return !warning.value;
}

function submit() {
  if (!validate(inputValue.value)) {
    inputElement.value?.focus();
    return;
  }
  const trimmed = (inputValue.value ?? '').toString().trim();
  emit('submit', trimmed);
  emit('update:modelValue', false);
}

function cancel() {
  emit('cancel');
  emit('update:modelValue', false);
}

useModalDialog(dialogElement, {
  onClose: cancel,
  isOpen: () => props.modelValue,
  initialFocus: inputElement,
});

defineExpose({ inputValue });
</script>

<style scoped>
.prompt-backdrop {
  position: fixed;
  z-index: 10000;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgb(18 35 64 / 58%);
  backdrop-filter: blur(3px);
}

.prompt-dialog {
  width: min(500px, 100%);
  overflow: hidden;
  background: #fff;
  border: 1px solid #d7e1f0;
  border-radius: 18px;
  box-shadow: 0 24px 70px rgb(15 35 70 / 28%);
}

.prompt-header {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 14px;
  align-items: center;
  padding: 22px 24px 18px;
  background: linear-gradient(145deg, #fff, #f7faff);
  border-bottom: 1px solid #e2e8f2;
}

.prompt-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  color: #2864e8;
  background: #e8f0ff;
  border-radius: 12px;
}

.prompt-eyebrow {
  display: block;
  color: #2864e8;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.075em;
  text-transform: uppercase;
}

.prompt-header h2 {
  margin: 2px 0 0;
  color: #12213b;
  font-size: 1.18rem;
}

.prompt-close {
  width: 38px;
  height: 38px;
  color: #65748d;
  background: transparent;
  border: 0;
  border-radius: 9px;
  cursor: pointer;
}

.prompt-close:hover {
  color: #17243b;
  background: #eef3f9;
}

.prompt-form {
  display: grid;
  gap: 10px;
  padding: 22px 24px 0;
}

.prompt-form label {
  color: #35445f;
  font-size: 0.9rem;
  font-weight: 700;
  line-height: 1.45;
}

.prompt-input {
  width: 100%;
  min-height: 44px;
  padding: 10px 12px;
  color: #12213b;
  background: #fff;
  border: 1px solid #cdd8e8;
  border-radius: 10px;
  font: inherit;
}

.prompt-input:focus {
  outline: 3px solid rgb(37 99 235 / 15%);
  border-color: #4480ef;
}

.prompt-input[aria-invalid='true'] {
  border-color: #dc4848;
}

.prompt-warning {
  display: flex;
  gap: 7px;
  align-items: center;
  color: #b52626;
  font-size: 0.82rem;
}

.prompt-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin: 12px -24px 0;
  padding: 16px 24px;
  background: #f7f9fc;
  border-top: 1px solid #e2e8f2;
}

.prompt-button {
  min-height: 42px;
  padding: 9px 17px;
  font: inherit;
  font-weight: 700;
  border-radius: 10px;
  cursor: pointer;
}

.prompt-button.secondary {
  color: #35445f;
  background: #fff;
  border: 1px solid #cdd8e8;
}

.prompt-button.primary {
  color: #fff;
  background: #2563eb;
  border: 1px solid #2563eb;
}

@media (width <= 560px) {
  .prompt-backdrop {
    align-items: end;
    padding: 12px;
  }

  .prompt-dialog {
    border-radius: 16px;
  }

  .prompt-actions {
    flex-direction: column-reverse;
  }

  .prompt-button {
    width: 100%;
  }
}
</style>
