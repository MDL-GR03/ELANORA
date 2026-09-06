<template>
  <header
    class="workspace-header"
    :class="{ 'workspace-header--embedded': embedded }"
  >
    <div class="workspace-header__copy">
      <span v-if="context" class="workspace-header__context">{{
        context
      }}</span>
      <h1>{{ title }}</h1>
      <p v-if="description">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="workspace-header__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  context: { type: String, default: '' },
  embedded: { type: Boolean, default: false },
});
</script>

<style scoped>
.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  padding: clamp(1.15rem, 3vw, 1.75rem);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.workspace-header--embedded {
  padding: 0 0 1.1rem;
  border: 0;
  border-bottom: 1px solid var(--color-border);
  border-radius: 0;
  box-shadow: none;
}

.workspace-header__copy {
  min-width: 0;
}

.workspace-header__context {
  display: block;
  margin-bottom: 0.2rem;
  color: var(--primary-color);
  font-size: 0.75rem;
  font-weight: 750;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.workspace-header h1 {
  margin: 0;
  font-size: clamp(1.55rem, 3vw, 2rem);
  font-weight: 720;
  line-height: 1.2;
}

.workspace-header p {
  max-width: 48rem;
  margin: 0.35rem 0 0;
  color: var(--color-text-muted);
  font-size: 0.92rem;
  line-height: 1.5;
}

.workspace-header__actions {
  flex: none;
}

@media (width <= 640px) {
  .workspace-header {
    align-items: stretch;
    flex-direction: column;
  }

  .workspace-header__actions :deep(button),
  .workspace-header__actions :deep(a) {
    width: 100%;
  }
}
</style>
