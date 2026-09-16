<template>
  <div :id="id" class="validation-messages">
    <div
      v-if="message"
      :class="`${message.type}-message`"
      :role="message.type === 'error' ? 'alert' : undefined"
    >
      <i v-if="message.type === 'success'" class="success-icon-small">✓</i>
      <i v-else-if="message.type === 'error'" class="error-icon-small">⚠</i>
      {{ message.text }}
    </div>
  </div>
</template>

<script setup>
/**
 * One field's message, whatever kind it is.
 *
 * The element exists even when there is nothing to say, so the input can point
 * at it with aria-describedby and a screen reader announces the message as
 * soon as it appears.
 */
defineProps({
  id: { type: String, required: true },
  message: {
    type: Object,
    default: null,
    validator: (value) =>
      value === null ||
      ['error', 'success', 'info', 'warning'].includes(value.type),
  },
});
</script>
