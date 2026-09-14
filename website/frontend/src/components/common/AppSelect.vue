<template>
  <div
    ref="root"
    class="app-select"
    :class="[`app-select--${size}`, { open: isOpen, disabled, invalid }]"
  >
    <button
      :id="resolvedId"
      ref="trigger"
      type="button"
      class="app-select-trigger"
      aria-haspopup="listbox"
      role="combobox"
      :aria-expanded="isOpen"
      :aria-controls="`${resolvedId}-options`"
      :aria-activedescendant="activeOptionId"
      :aria-label="ariaLabel"
      :aria-invalid="invalid || undefined"
      :aria-required="required || undefined"
      :aria-describedby="ariaDescribedby"
      :disabled="disabled"
      @click="toggle"
      @keydown="onKeydown"
      @blur="emit('blur', $event)"
    >
      <span :class="{ 'app-select-placeholder': !hasSelection }">{{
        selectedLabel
      }}</span>
      <font-awesome-icon icon="fa-solid fa-chevron-down" />
    </button>
    <ul
      v-if="isOpen"
      :id="`${resolvedId}-options`"
      class="app-select-options"
      role="listbox"
      :aria-labelledby="resolvedId"
    >
      <li
        v-for="(option, index) in options"
        :key="String(option.value)"
        role="presentation"
      >
        <!-- Listbox options are never focused themselves; the active option is moved with the arrow keys handled on the combobox trigger, so @focus could never fire here. -->
        <!-- eslint-disable-next-line vuejs-accessibility/mouse-events-have-key-events -->
        <button
          :id="optionId(index)"
          type="button"
          role="option"
          tabindex="-1"
          :aria-selected="isSelected(option)"
          :disabled="option.disabled"
          :class="{
            selected: isSelected(option),
            active: index === activeIndex,
          }"
          @mouseenter="!option.disabled && (activeIndex = index)"
          @click="select(option)"
        >
          <span class="app-select-option-copy">
            <span class="app-select-option-label" :title="option.label">{{
              option.label
            }}</span>
            <small v-if="option.description">{{ option.description }}</small>
          </span>
          <font-awesome-icon
            v-if="isSelected(option)"
            icon="fa-solid fa-check"
          />
        </button>
      </li>
    </ul>
  </div>
</template>

<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  useId,
  watch,
} from 'vue';

const props = defineProps({
  modelValue: { type: [String, Number, Boolean, null], default: '' },
  options: { type: Array, required: true },
  id: { type: String, default: '' },
  ariaLabel: { type: String, default: undefined },
  ariaDescribedby: { type: String, default: undefined },
  placeholder: { type: String, default: 'Select an option' },
  disabled: { type: Boolean, default: false },
  required: { type: Boolean, default: false },
  invalid: { type: Boolean, default: false },
  size: { type: String, default: 'medium' },
});
const emit = defineEmits(['update:modelValue', 'change', 'blur']);

const root = ref(null);
const trigger = ref(null);
const isOpen = ref(false);
const activeIndex = ref(0);
const generatedId = useId();
const resolvedId = computed(() => props.id || `app-select-${generatedId}`);
let typeahead = '';
let typeaheadTimer;
const hasSelection = computed(() =>
  props.options.some((option) => isSelected(option))
);
const selectedIndex = computed(() =>
  Math.max(
    0,
    props.options.findIndex((option) => isSelected(option))
  )
);
const selectedLabel = computed(() =>
  hasSelection.value
    ? props.options[selectedIndex.value]?.label
    : props.placeholder
);
const activeOptionId = computed(() =>
  isOpen.value && activeIndex.value >= 0
    ? optionId(activeIndex.value)
    : undefined
);

function optionId(index) {
  return `${resolvedId.value}-option-${index}`;
}

function isSelected(option) {
  return String(option.value) === String(props.modelValue ?? '');
}

function nextEnabledIndex(start, step) {
  if (!props.options.length) return -1;
  let index = start;
  for (let count = 0; count < props.options.length; count += 1) {
    index = (index + step + props.options.length) % props.options.length;
    if (!props.options[index]?.disabled) return index;
  }
  return -1;
}

function open() {
  if (props.disabled || !props.options.length) return;
  activeIndex.value = selectedIndex.value;
  if (props.options[activeIndex.value]?.disabled) {
    activeIndex.value = nextEnabledIndex(activeIndex.value, 1);
  }
  isOpen.value = true;
  void nextTick(() => {
    document.getElementById(activeOptionId.value)?.scrollIntoView?.({
      block: 'nearest',
    });
  });
}

function close() {
  isOpen.value = false;
}

function toggle() {
  if (isOpen.value) close();
  else open();
}

function select(option) {
  if (!option || option.disabled) return;
  emit('update:modelValue', option.value);
  emit('change', option.value);
  close();
  void nextTick(() => trigger.value?.focus());
}

function onKeydown(event) {
  if (event.key === 'Escape') {
    close();
    return;
  }
  if (event.key === 'Tab') {
    close();
    return;
  }
  if (event.key.length === 1 && !event.ctrlKey && !event.metaKey) {
    typeahead += event.key.toLocaleLowerCase();
    clearTimeout(typeaheadTimer);
    typeaheadTimer = setTimeout(() => (typeahead = ''), 500);
    const match = props.options.findIndex(
      (option) =>
        !option.disabled &&
        option.label.toLocaleLowerCase().startsWith(typeahead)
    );
    if (match >= 0) {
      if (!isOpen.value) open();
      activeIndex.value = match;
    }
    return;
  }
  if (
    !['ArrowDown', 'ArrowUp', 'Home', 'End', 'Enter', ' '].includes(event.key)
  ) {
    return;
  }
  event.preventDefault();
  if (!isOpen.value) {
    open();
    return;
  }
  if (event.key === 'ArrowDown') {
    activeIndex.value = nextEnabledIndex(activeIndex.value, 1);
  } else if (event.key === 'ArrowUp') {
    activeIndex.value = nextEnabledIndex(activeIndex.value, -1);
  } else if (event.key === 'Home') {
    activeIndex.value = nextEnabledIndex(-1, 1);
  } else if (event.key === 'End') {
    activeIndex.value = nextEnabledIndex(0, -1);
  } else {
    select(props.options[activeIndex.value]);
  }
}

function closeFromOutside(event) {
  if (!root.value?.contains(event.target)) close();
}

watch(
  () => [props.modelValue, props.options],
  () => {
    if (!isOpen.value) activeIndex.value = selectedIndex.value;
  }
);

onMounted(() => document.addEventListener('pointerdown', closeFromOutside));
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', closeFromOutside);
  clearTimeout(typeaheadTimer);
});
</script>

<style scoped>
.app-select {
  position: relative;
  width: 100%;
  color: var(--color-text);
}

.app-select-trigger {
  width: 100%;
  min-height: 2.85rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.65rem 0.8rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: #fff;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.app-select-trigger > span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-select--small .app-select-trigger {
  min-height: 2.35rem;
  padding: 0.45rem 0.65rem;
}

.app-select.disabled .app-select-trigger {
  cursor: not-allowed;
  opacity: 0.62;
  background: #f3f6fa;
}

.app-select.invalid .app-select-trigger {
  border-color: var(--color-error, #dc2626);
}

.app-select-placeholder {
  color: #8491a5;
}

.app-select-trigger:hover {
  border-color: #9bbcf7;
  background: #f8fbff;
}

.app-select-trigger:focus-visible,
.open .app-select-trigger {
  border-color: #2563eb;
  outline: 0;
  box-shadow: 0 0 0 3px rgb(37 99 235 / 14%);
}

.app-select-trigger svg {
  flex: none;
  color: #64748b;
  transition: transform 140ms ease;
}

.open .app-select-trigger svg {
  transform: rotate(180deg);
}

.app-select-options {
  position: absolute;
  z-index: 40;
  inset: calc(100% + 0.35rem) 0 auto;
  max-height: min(18rem, 45vh);
  overflow-y: auto;
  margin: 0;
  padding: 0.35rem;
  border: 1px solid #bfd0ea;
  border-radius: var(--radius-sm);
  box-shadow: 0 12px 30px rgb(15 23 42 / 16%);
  background: #fff;
  list-style: none;
  overscroll-behavior: contain;
}

.app-select-options li + li {
  border-top: 1px solid #edf1f6;
}

.app-select-options button {
  width: 100%;
  min-height: 2.6rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.6rem 0.7rem;
  border: 0;
  border-radius: 0.4rem;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.app-select-options button:hover,
.app-select-options button.active {
  background: #edf4ff;
  color: #174ea6;
}

.app-select-options button.selected {
  color: #1558c0;
  font-weight: 700;
}

.app-select-options button:disabled {
  cursor: not-allowed;
  color: #94a3b8;
  background: transparent;
}

.app-select-option-copy {
  display: grid;
  gap: 0.15rem;
  min-width: 0;
}

.app-select-option-label,
.app-select-option-copy small {
  overflow-wrap: anywhere;
}

.app-select-option-copy small {
  color: #64748b;
  font-size: 0.78em;
  font-weight: 400;
}

.app-select-options svg {
  color: #2563eb;
}

@media (width <= 480px) {
  .app-select-options {
    max-width: calc(100vw - 1rem);
    max-height: min(18rem, 55vh);
  }

  .app-select-options button {
    min-height: 2.75rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .app-select-trigger svg {
    transition: none;
  }
}
</style>
