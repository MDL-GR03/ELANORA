<template>
  <span ref="root" class="help-tooltip" :class="{ open: isOpen }">
    <button
      type="button"
      class="help-trigger"
      :aria-label="label"
      :aria-describedby="tooltipId"
      @click.prevent.stop="isOpen = !isOpen"
      @keydown.esc.prevent.stop="isOpen = false"
    >
      ?
    </button>
    <span :id="tooltipId" class="help-content" role="tooltip">
      <strong v-if="title">{{ title }}</strong>
      {{ text }}
    </span>
  </span>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, useId } from 'vue';

defineProps({
  label: {
    type: String,
    default: 'More information',
  },
  title: {
    type: String,
    default: '',
  },
  text: {
    type: String,
    required: true,
  },
});

const tooltipId = `help-${useId()}`;
const root = ref(null);
const isOpen = ref(false);

function closeFromOutside(event) {
  if (!root.value?.contains(event.target)) isOpen.value = false;
}

onMounted(() => document.addEventListener('pointerdown', closeFromOutside));
onBeforeUnmount(() =>
  document.removeEventListener('pointerdown', closeFromOutside)
);
</script>

<style scoped>
.help-tooltip {
  position: relative;
  display: inline-flex;
  flex: 0 0 auto;
  vertical-align: middle;
}

.help-trigger {
  display: inline-grid;
  width: 1.15rem;
  min-height: 1.15rem;
  place-items: center;
  padding: 0;
  border: 1px solid var(--color-info);
  border-radius: var(--radius-full);
  background: var(--color-info-bg);
  color: var(--color-primary-dark);
  font: inherit;
  font-size: 0.7rem;
  font-weight: 850;
  line-height: 1;
  cursor: help;
}

.help-trigger:hover,
.help-trigger:focus-visible {
  border-color: var(--color-info-light);
  background: var(--color-info-bg);
  outline: none;
  box-shadow: 0 0 0 3px rgb(59 130 246 / 15%);
}

.help-content {
  position: absolute;
  z-index: 20;
  bottom: calc(100% + 0.55rem);
  left: 50%;
  width: max-content;
  max-width: min(19rem, calc(100vw - 2rem));
  padding: 0.65rem 0.75rem;
  border: 1px solid var(--color-gray-800);
  border-radius: var(--radius-md);
  background: var(--color-text);
  color: var(--color-surface-subtle);
  box-shadow: 0 0.6rem 1.4rem rgb(15 23 42 / 22%);
  font-size: 0.76rem;
  font-weight: 500;
  line-height: 1.4;
  text-align: left;
  transform: translate(-50%, 0.2rem);
  visibility: hidden;
  opacity: 0;
  pointer-events: none;
  transition:
    opacity 0.15s ease,
    transform 0.15s ease,
    visibility 0.15s;
}

.help-content::after {
  position: absolute;
  top: 100%;
  left: 50%;
  border: 0.35rem solid transparent;
  border-top-color: var(--color-text);
  content: '';
  transform: translateX(-50%);
}

.help-content strong {
  display: block;
  margin-bottom: 0.15rem;
  color: var(--color-info);
}

.help-tooltip:hover .help-content,
.help-tooltip:focus-within .help-content,
.help-tooltip.open .help-content {
  transform: translate(-50%, 0);
  visibility: visible;
  opacity: 1;
  pointer-events: auto;
}

@media (width <= 640px) {
  .help-content {
    position: fixed;
    right: 1rem;
    bottom: 1rem;
    left: 1rem;
    width: auto;
    max-width: none;
    transform: translateY(0.2rem);
  }

  .help-tooltip:hover .help-content,
  .help-tooltip:focus-within .help-content,
  .help-tooltip.open .help-content {
    transform: translateY(0);
  }

  .help-content::after {
    display: none;
  }
}
</style>
