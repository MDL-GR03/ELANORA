<template>
  <div v-if="visible" class="confirm-backdrop" @mousedown.self="cancel">
    <dialog
      ref="dialogElement"
      class="confirm-dialog"
      :class="`tone-${resolvedTone}`"
      open
      aria-modal="true"
      :aria-labelledby="title ? titleId : undefined"
      :aria-label="title ? undefined : message"
      :aria-describedby="messageId"
      @keydown="handleKeydown"
    >
      <header class="confirm-header">
        <span class="confirm-icon" aria-hidden="true">
          <FontAwesomeIcon :icon="toneIcon" />
        </span>
        <div class="confirm-heading">
          <span class="confirm-eyebrow">Confirmation required</span>
          <h2 v-if="title" :id="titleId">{{ title }}</h2>
        </div>
        <button
          type="button"
          class="confirm-close"
          aria-label="Cancel and close"
          title="Cancel"
          @click="cancel"
        >
          <FontAwesomeIcon :icon="faXmark" />
        </button>
      </header>

      <div class="confirm-content">
        <p :id="messageId">{{ message }}</p>
      </div>

      <footer class="confirm-actions">
        <button
          ref="cancelButton"
          type="button"
          class="confirm-button secondary"
          @click="cancel"
        >
          {{ cancelText }}
        </button>
        <button type="button" class="confirm-button primary" @click="confirm">
          <FontAwesomeIcon :icon="toneIcon" />
          {{ confirmText }}
        </button>
      </footer>
    </dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, useId, watch } from 'vue';
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';
import {
  faCircleCheck,
  faCircleQuestion,
  faTriangleExclamation,
  faXmark,
} from '@fortawesome/free-solid-svg-icons';

const props = defineProps({
  modelValue: Boolean,
  message: { type: String, required: true },
  title: { type: String, default: '' },
  confirmText: { type: String, default: 'Confirm' },
  cancelText: { type: String, default: 'Cancel' },
  tone: {
    type: String,
    default: 'auto',
    validator: (value) =>
      ['auto', 'default', 'success', 'danger'].includes(value),
  },
});
const emit = defineEmits(['update:modelValue', 'confirm', 'cancel']);
const visible = ref(props.modelValue);
const dialogElement = ref(null);
const cancelButton = ref(null);
const generatedId = useId();
const titleId = `confirmation-title-${generatedId}`;
const messageId = `confirmation-message-${generatedId}`;
let previouslyFocused = null;

const resolvedTone = computed(() => {
  if (props.tone !== 'auto') return props.tone;
  const action = `${props.title} ${props.confirmText}`.toLowerCase();
  if (/delete|remove|discard|dismiss|archive|reject/.test(action))
    return 'danger';
  if (/accept|approve|merge|resolve|reopen|restore/.test(action))
    return 'success';
  return 'default';
});
const toneIcon = computed(
  () =>
    ({
      danger: faTriangleExclamation,
      success: faCircleCheck,
      default: faCircleQuestion,
    })[resolvedTone.value]
);

watch(
  () => props.modelValue,
  async (value) => {
    visible.value = value;
    if (value) {
      previouslyFocused =
        document.activeElement instanceof HTMLElement
          ? document.activeElement
          : null;
      await nextTick();
      cancelButton.value?.focus();
    } else if (previouslyFocused?.isConnected) {
      await nextTick();
      previouslyFocused.focus();
      previouslyFocused = null;
    }
  },
  { immediate: true }
);

function handleKeydown(event) {
  if (event.key === 'Escape') {
    event.stopPropagation();
    cancel();
    return;
  }
  if (event.key !== 'Tab') return;
  const controls = [
    ...dialogElement.value.querySelectorAll('button:not(:disabled)'),
  ];
  if (!controls.length) return;
  const first = controls[0];
  const last = controls.at(-1);
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

function confirm() {
  emit('confirm');
  emit('update:modelValue', false);
}
function cancel() {
  emit('cancel');
  emit('update:modelValue', false);
}

onBeforeUnmount(() => {
  if (previouslyFocused?.isConnected) previouslyFocused.focus();
});

defineExpose({ confirm, cancel });
</script>

<style scoped>
.confirm-backdrop {
  position: fixed;
  z-index: 10000;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgb(18 35 64 / 58%);
  backdrop-filter: blur(3px);
  animation: backdrop-in 140ms ease-out;
}

.confirm-dialog {
  position: static;
  width: min(560px, 100%);
  max-width: none;
  max-height: min(720px, calc(100vh - 48px));
  margin: 0;
  padding: 0;
  overflow: hidden auto;
  color: #12213b;
  background: #fff;
  border: 1px solid #d7e1f0;
  border-radius: 18px;
  box-shadow: 0 24px 70px rgb(15 35 70 / 28%);
  animation: dialog-in 170ms cubic-bezier(0.2, 0.8, 0.2, 1);
}

.confirm-header {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 14px;
  align-items: center;
  padding: 24px 24px 18px;
  border-bottom: 1px solid #e2e8f2;
}

.confirm-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  color: #205ee8;
  background: #eaf1ff;
  border-radius: 12px;
  font-size: 1.05rem;
}

.tone-success .confirm-icon {
  color: #08783f;
  background: #e7f8ef;
}

.tone-danger .confirm-icon {
  color: #c62828;
  background: #fff0f0;
}

.confirm-heading {
  min-width: 0;
}

.confirm-eyebrow {
  display: block;
  margin-bottom: 3px;
  color: #5e7191;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.075em;
  text-transform: uppercase;
}

.confirm-heading h2 {
  margin: 0;
  color: #12213b;
  font-size: 1.2rem;
  font-weight: 700;
  line-height: 1.3;
}

.confirm-close {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  padding: 0;
  color: #65748d;
  background: transparent;
  border: 0;
  border-radius: 10px;
  cursor: pointer;
}

.confirm-close:hover {
  color: #17243b;
  background: #eef3f9;
}

.confirm-content {
  padding: 22px 24px 24px;
}

.confirm-content p {
  margin: 0;
  color: #50617e;
  font-size: 0.98rem;
  line-height: 1.65;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  background: #f7f9fc;
  border-top: 1px solid #e2e8f2;
}

.confirm-button {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 9px 17px;
  font: inherit;
  font-weight: 700;
  border: 1px solid transparent;
  border-radius: 10px;
  cursor: pointer;
  transition:
    transform 120ms ease,
    box-shadow 120ms ease,
    background 120ms ease;
}

.confirm-button.secondary {
  color: #35445f;
  background: #fff;
  border-color: #cdd8e8;
}

.confirm-button.primary {
  color: #fff;
  background: #2563eb;
  box-shadow: 0 4px 12px rgb(37 99 235 / 20%);
}

.tone-success .confirm-button.primary {
  background: #12824a;
  box-shadow: 0 4px 12px rgb(18 130 74 / 20%);
}

.tone-danger .confirm-button.primary {
  background: #d52b2b;
  box-shadow: 0 4px 12px rgb(213 43 43 / 20%);
}

.confirm-button:hover {
  transform: translateY(-1px);
}

.confirm-button:focus-visible,
.confirm-close:focus-visible {
  outline: 3px solid rgb(37 99 235 / 28%);
  outline-offset: 2px;
}

@keyframes backdrop-in {
  from {
    opacity: 0;
  }
}

@keyframes dialog-in {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.985);
  }
}

@media (width <= 560px) {
  .confirm-backdrop {
    align-items: end;
    padding: 12px;
  }

  .confirm-dialog {
    width: 100%;
    border-radius: 16px;
  }

  .confirm-header,
  .confirm-content,
  .confirm-actions {
    padding-right: 18px;
    padding-left: 18px;
  }

  .confirm-actions {
    flex-direction: column-reverse;
  }

  .confirm-button {
    width: 100%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .confirm-backdrop,
  .confirm-dialog {
    animation: none;
  }
}
</style>
