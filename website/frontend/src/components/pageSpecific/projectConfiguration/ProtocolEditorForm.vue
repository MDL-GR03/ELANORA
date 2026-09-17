<template>
  <form class="protocol-form" @submit.prevent="emit('submit')">
    <div class="wide">
      <h4>{{ t(`protocols.editor.${copy.title}`) }}</h4>
      <p>{{ t(`protocols.editor.${copy.help}`) }}</p>
    </div>
    <label class="wide">
      {{ t('protocols.name') }}
      <input
        v-model.trim="name"
        required
        maxlength="150"
        :disabled="mode !== 'create-protocol'"
      />
    </label>
    <div v-if="suggesting" class="suggestion-loading wide">
      {{ t('protocols.analyzing') }}
    </div>
    <CorpusProtocolSuggestion
      v-else-if="suggestion"
      :suggestion="suggestion"
      class="wide"
      @apply="emit('apply-suggestion', $event)"
      @close="emit('dismiss-suggestion')"
    />
    <ProtocolRuleBuilder v-model="rules" class="wide" />
    <div class="form-actions wide">
      <button :disabled="saving">
        {{
          saving ? t('protocols.saving') : t(`protocols.editor.${copy.submit}`)
        }}
      </button>
    </div>
  </form>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import CorpusProtocolSuggestion from './CorpusProtocolSuggestion.vue';
import ProtocolRuleBuilder from './ProtocolRuleBuilder.vue';

const EDITOR_COPY = {
  'create-protocol': {
    title: 'new_title',
    help: 'new_help',
    submit: 'create_draft',
  },
  'create-version': {
    title: 'version_title',
    help: 'version_help',
    submit: 'create_draft',
  },
  'edit-draft': {
    title: 'edit_title',
    help: 'edit_help',
    submit: 'save_draft',
  },
};

const props = defineProps({
  mode: {
    type: String,
    required: true,
    validator: (value) =>
      ['create-protocol', 'create-version', 'edit-draft'].includes(value),
  },
  saving: { type: Boolean, default: false },
  suggesting: { type: Boolean, default: false },
  suggestion: { type: Object, default: null },
});
const name = defineModel('name', { type: String, required: true });
const rules = defineModel('rules', { type: Object, required: true });
const emit = defineEmits(['submit', 'apply-suggestion', 'dismiss-suggestion']);

const { t } = useI18n();
const copy = computed(() => EDITOR_COPY[props.mode]);
</script>

<style scoped src="@/assets/css/protocol-workspace.css"></style>

<style scoped>
.suggestion-loading {
  padding: 1rem;
  border: 1px solid var(--color-blue-200);
  border-radius: 0.75rem;
  background: var(--color-blue-100);
  color: var(--color-blue-800);
  text-align: center;
}

.protocol-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  padding: 1.25rem;
  border: 1px solid var(--color-blue-200);
  border-radius: 0.9rem;
  background: var(--color-blue-50);
}

.protocol-form label {
  display: grid;
  gap: 0.4rem;
  font-weight: 700;
}

.protocol-form .wide {
  grid-column: 1/-1;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}

@media (width <= 760px) {
  .protocol-form {
    grid-template-columns: 1fr;
  }

  .protocol-form .wide {
    grid-column: auto;
  }
}
</style>
