<template>
  <span class="help-tooltip">
    <button
      type="button"
      class="help-trigger"
      :aria-label="label"
      :aria-describedby="tooltipId"
      @click.prevent.stop
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
import { useId } from 'vue';

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
  border: 1px solid #bfdbfe;
  border-radius: 50%;
  background: #eff6ff;
  color: #1d4ed8;
  font: inherit;
  font-size: 0.7rem;
  font-weight: 850;
  line-height: 1;
  cursor: help;
}

.help-trigger:hover,
.help-trigger:focus-visible {
  border-color: #60a5fa;
  background: #dbeafe;
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
  border: 1px solid #334155;
  border-radius: 0.55rem;
  background: #172033;
  color: #f8fafc;
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
  border-top-color: #172033;
  content: '';
  transform: translateX(-50%);
}

.help-content strong {
  display: block;
  margin-bottom: 0.15rem;
  color: #bfdbfe;
}

.help-trigger:hover + .help-content,
.help-trigger:focus + .help-content,
.help-trigger:focus-visible + .help-content {
  transform: translate(-50%, 0);
  visibility: visible;
  opacity: 1;
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

  .help-trigger:hover + .help-content,
  .help-trigger:focus + .help-content,
  .help-trigger:focus-visible + .help-content {
    transform: translateY(0);
  }

  .help-content::after {
    display: none;
  }
}
</style>
