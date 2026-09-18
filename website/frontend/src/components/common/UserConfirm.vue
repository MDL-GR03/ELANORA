<template>
  <div
    v-if="visible"
    class="confirm-backdrop"
    role="presentation"
    @mousedown.self="cancel"
  >
    <dialog
      ref="dialogElement"
      class="confirm-dialog"
      :class="`tone-${resolvedTone}`"
      open
      aria-modal="true"
      :aria-labelledby="title ? titleId : undefined"
      :aria-label="title ? undefined : message"
      :aria-describedby="messageId"
    >
      <header class="confirm-header">
        <span class="confirm-icon" aria-hidden="true">
          <FontAwesomeIcon :icon="toneIcon" />
        </span>
        <div class="confirm-heading">
          <span class="confirm-eyebrow">{{
            t('dialogs.confirmationRequired')
          }}</span>
          <h2 v-if="title" :id="titleId">{{ title }}</h2>
        </div>
        <button
          type="button"
          class="confirm-close"
          :aria-label="t('dialogs.cancelAndClose')"
          :title="t('common.cancel')"
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
          {{ cancelText || t('common.cancel') }}
        </button>
        <button type="button" class="confirm-button primary" @click="confirm">
          <FontAwesomeIcon :icon="toneIcon" />
          {{ confirmText || t('common.confirm') }}
        </button>
      </footer>
    </dialog>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n';
import { computed, ref, useId, watch } from 'vue';
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';
import {
  faCircleCheck,
  faCircleQuestion,
  faTriangleExclamation,
  faXmark,
} from '@fortawesome/free-solid-svg-icons';
import { useModalDialog } from '@/composables/useModalDialog';

const { t } = useI18n();

const props = defineProps({
  modelValue: Boolean,
  message: { type: String, required: true },
  title: { type: String, default: '' },
  confirmText: { type: String, default: '' },
  cancelText: { type: String, default: '' },
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
  (value) => {
    visible.value = value;
  },
  { immediate: true }
);

function confirm() {
  emit('confirm');
  emit('update:modelValue', false);
}
function cancel() {
  emit('cancel');
  emit('update:modelValue', false);
}

useModalDialog(dialogElement, {
  onClose: cancel,
  isOpen: () => props.modelValue,
  initialFocus: cancelButton,
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
  background: color-mix(in srgb, var(--color-slate-900) 58%, transparent);
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
  color: var(--color-text);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 18px;
  box-shadow: 0 24px 70px color-mix(in srgb, var(--color-slate-800) 28%, transparent);
  animation: dialog-in 170ms cubic-bezier(0.2, 0.8, 0.2, 1);
}

.confirm-header {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 14px;
  align-items: center;
  padding: 24px 24px 18px;
  border-bottom: 1px solid var(--color-border);
}

.confirm-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  color: var(--color-info-dark);
  background: var(--color-info-bg);
  border-radius: var(--radius-lg);
  font-size: 1.05rem;
}

.tone-success .confirm-icon {
  color: var(--color-success-dark);
  background: var(--color-success-bg-subtle);
}

.tone-danger .confirm-icon {
  color: var(--color-error);
  background: var(--color-error-bg-subtle);
}

.confirm-heading {
  min-width: 0;
}

.confirm-eyebrow {
  display: block;
  margin-bottom: 3px;
  color: var(--color-text-muted);
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.075em;
  text-transform: uppercase;
}

.confirm-heading h2 {
  margin: 0;
  color: var(--color-text);
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
  color: var(--color-text-muted);
  background: transparent;
  border: 0;
  border-radius: var(--radius-md);
  cursor: pointer;
}

.confirm-close:hover {
  color: var(--color-text);
  background: var(--color-surface-subtle);
}

.confirm-content {
  padding: 22px 24px 24px;
}

.confirm-content p {
  margin: 0;
  color: var(--color-gray-700);
  font-size: 0.98rem;
  line-height: 1.65;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  background: var(--color-canvas);
  border-top: 1px solid var(--color-border);
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
  border-radius: var(--radius-md);
  cursor: pointer;
  transition:
    transform 120ms ease,
    box-shadow 120ms ease,
    background 120ms ease;
}

.confirm-button.secondary {
  color: var(--color-gray-800);
  background: var(--color-surface);
  border-color: var(--color-border);
}

.confirm-button.primary {
  color: var(--color-text-inverse);
  background: var(--color-primary);
  box-shadow: 0 4px 12px var(--primary-20);
}

.tone-success .confirm-button.primary {
  background: var(--color-success);
  box-shadow: 0 4px 12px color-mix(in srgb, var(--color-emerald-700) 20%, transparent);
}

.tone-danger .confirm-button.primary {
  background: var(--color-error);
  box-shadow: 0 4px 12px color-mix(in srgb, var(--color-red-600) 20%, transparent);
}

.confirm-button:hover {
  transform: translateY(-1px);
}

.confirm-button:focus-visible,
.confirm-close:focus-visible {
  outline: 3px solid var(--primary-28);
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
