<template>
  <transition name="slide-fade">
    <!-- A live region, not a control. The pointer and focus handlers only pause the auto-dismiss timer so the message can be read. -->
    <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
    <div
      v-if="visible"
      :class="['event-message', typeClasses[type]]"
      :role="type === 'error' ? 'alert' : 'status'"
      aria-live="polite"
      @mouseenter="onMouseEnter"
      @mouseleave="onMouseLeave"
      @focusin="onMouseEnter"
      @focusout="onMouseLeave"
    >
      <div class="event-message-icon">
        <span aria-hidden="true">{{ typeIcons[type] }}</span>
      </div>
      <div class="event-message-text">
        {{ displayText }}
      </div>
      <button
        class="event-message-close"
        :aria-label="t('notifications.close')"
        @click="closeMessage"
      >
        <span aria-hidden="true">×</span>
      </button>
    </div>
  </transition>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';

const props = defineProps({
  translationKey: {
    type: String,
    required: true,
  },
  type: {
    type: String,
    default: 'info',
    validator: (value) =>
      ['info', 'warning', 'error', 'success'].includes(value),
  },
  duration: {
    type: Number,
    default: 6000, // 6 seconds
  },
  show: {
    type: Boolean,
    default: true,
  },
  id: {
    type: Number,
    required: true,
  },
  params: {
    type: Object,
    default: () => ({}),
  },
});

const { t, te } = useI18n();
const emit = defineEmits(['close']);
const visible = ref(props.show);
const timer = ref(null);
const hover = ref(false);
let fadeOutTimer = null;

const typeClasses = computed(() => ({
  error: 'event-message-error',
  warning: 'event-message-warning',
  info: 'event-message-info',
  success: 'event-message-success',
}));
const displayText = computed(() =>
  te(props.translationKey)
    ? t(props.translationKey, props.params || {})
    : props.translationKey
);
const typeIcons = { error: '!', warning: '!', info: 'i', success: '✓' };

const closeMessage = () => {
  visible.value = false;
  if (timer.value) {
    clearTimeout(timer.value);
  }
  if (fadeOutTimer) {
    clearTimeout(fadeOutTimer);
  }
  // Allow time for animation to complete before emitting close event
  setTimeout(() => {
    emit('close', props.id);
  }, 500);
};

const setupAutoClose = () => {
  if (timer.value) {
    clearTimeout(timer.value);
  }

  if (props.duration > 0) {
    timer.value = setTimeout(() => {
      if (!hover.value) {
        closeMessage();
      }
      // If hovering, do not close; will close on mouseleave
    }, props.duration);
  }
};

function onMouseEnter() {
  hover.value = true;
  if (timer.value) {
    clearTimeout(timer.value);
  }
  if (fadeOutTimer) {
    clearTimeout(fadeOutTimer);
  }
}

function onMouseLeave() {
  hover.value = false;
  // Start fade out after 2 seconds if not already closed
  fadeOutTimer = setTimeout(() => {
    closeMessage();
  }, 2000);
}

watch(
  () => props.show,
  (newValue) => {
    visible.value = newValue;
    if (newValue && props.duration > 0) {
      setupAutoClose();
    }
  }
);

onMounted(() => {
  if (visible.value && props.duration > 0) {
    setupAutoClose();
  }
});

onBeforeUnmount(() => {
  if (timer.value) {
    clearTimeout(timer.value);
  }
  if (fadeOutTimer) {
    clearTimeout(fadeOutTimer);
  }
});
</script>

<style scoped>
.slide-fade-enter-active {
  transition:
    transform 0.25s ease,
    opacity 0.25s ease;
}

.slide-fade-leave-active {
  transition:
    transform 0.2s ease,
    opacity 0.2s ease;
}

.slide-fade-enter-from {
  transform: translateX(1.25rem);
  opacity: 0;
}

.slide-fade-leave-to {
  transform: translateX(1.25rem);
  opacity: 0;
}

.event-message {
  --toast-accent: var(--color-primary);
  --toast-soft: var(--color-blue-50-subtle);

  width: min(24rem, calc(100vw - 2rem));
  display: grid;
  grid-template-columns: 2rem minmax(0, 1fr) 1.75rem;
  align-items: start;
  padding: 0.9rem;
  border: 1px solid color-mix(in srgb, var(--toast-accent) 22%, #dbe3ef);
  border-radius: 0.8rem;
  background: rgb(255 255 255 / 97%);
  box-shadow:
    0 1rem 2.5rem rgb(15 23 42 / 14%),
    0 0.15rem 0.45rem rgb(15 23 42 / 8%);
  gap: 0.75rem;
  overflow-wrap: break-word;
  backdrop-filter: blur(12px);
}

.event-message-icon {
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.6rem;
  background: var(--toast-soft);
  color: var(--toast-accent);
  font-size: 0.9rem;
  font-weight: 900;
}

.event-message-text {
  padding-top: 0.28rem;
  color: var(--color-slate-800, #1e293b);
  font-size: 0.92rem;
  font-weight: 650;
  line-height: 1.45;
  text-align: left;
  white-space: pre-line;
  overflow-wrap: break-word;
  min-width: 0;
}

.event-message-close {
  width: 1.75rem;
  height: 1.75rem;
  display: grid;
  place-items: center;
  color: var(--color-slate-500, #6b7280);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  border-radius: 0.45rem;
  font-size: 1.15rem;
  line-height: 1;
  transition:
    color 0.15s,
    background 0.15s;
  justify-self: end;
}

.event-message-close:hover {
  background: var(--color-slate-100, #f1f5f9);
  color: var(--color-slate-700, #374151);
}

.event-message-error {
  --toast-accent: var(--color-error-light);
  --toast-soft: var(--color-error-bg);
}

.event-message-warning {
  --toast-accent: var(--color-accent);
  --toast-soft: var(--color-amber-50);
}

.event-message-info {
  --toast-accent: var(--color-primary);
  --toast-soft: var(--color-blue-50-subtle);
}

.event-message-success {
  --toast-accent: var(--color-emerald-600);
  --toast-soft: var(--color-success-150-bg);
}
</style>
