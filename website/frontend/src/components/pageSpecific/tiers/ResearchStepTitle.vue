<template>
  <div class="research-step__title">
    <span>{{ number }}</span>
    <div>
      <h3>{{ title }}</h3>
      <p>{{ text }}</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  number: { type: String, required: true },
  title: { type: String, required: true },
  text: { type: String, required: true },
});
</script>
