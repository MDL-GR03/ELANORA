<template>
  <div class="page-loader" role="status" aria-live="polite">
    <span class="page-loader-mark" aria-hidden="true"></span
    ><span>{{ $t('pageLoader.loading') }}</span>
  </div>
</template>
<style scoped>
.page-loader {
  min-height: 18rem;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 0.8rem;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.page-loader-mark {
  width: 2rem;
  height: 2rem;
  border: 3px solid var(--color-border);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .page-loader-mark {
    animation-duration: 1.8s;
  }
}
</style>
