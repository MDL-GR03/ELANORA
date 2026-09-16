<template>
  <section class="baseline-tier-card">
    <header>
      <span class="topic-card__icon">
        <font-awesome-icon icon="fa-solid fa-shield-halved" />
      </span>
      <div>
        <h3>{{ t('researchScopes.baseline.title') }}</h3>
        <p>{{ t('researchScopes.baseline.description') }}</p>
      </div>
      <button
        v-if="canManage"
        type="button"
        class="topic-action-button"
        :aria-label="
          editing
            ? t('researchScopes.baseline.cancelEditing')
            : t('researchScopes.baseline.edit')
        "
        :title="
          editing ? t('common.cancel') : t('researchScopes.baseline.edit')
        "
        @click="toggleEditor"
      >
        <font-awesome-icon
          :icon="editing ? 'fa-solid fa-xmark' : 'fa-regular fa-pen-to-square'"
        />
      </button>
    </header>
    <div v-if="baselineTiers.length" class="baseline-tier-chips">
      <span v-for="name in baselineTiers" :key="name">{{ name }}</span>
    </div>
    <p v-else class="baseline-tier-empty">
      {{ t('researchScopes.baseline.empty') }}
    </p>
    <form v-if="editing" @submit.prevent="save">
      <p>{{ t('researchScopes.baseline.editorHint') }}</p>
      <TierNamePicker
        :names="allTierNamesOf(tierGroups)"
        :selected="form"
        :tier-groups="tierGroups"
        @toggle="toggleName"
      />
      <footer>
        <span>{{
          t('researchScopes.baseline.selected', { count: form.size })
        }}</span>
        <button type="submit" class="tiers-primary-button" :disabled="pending">
          {{ pending ? t('common.saving') : t('researchScopes.baseline.save') }}
        </button>
      </footer>
    </form>
    <div v-if="error" class="tiers-operation-error" role="alert">
      {{ error }}
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { updateProjectBaselineTiers } from '@/api/service/tierService';
import { useEventMessageStore } from '@/stores/eventMessage';
import { allTierNamesOf } from '@/utils/tierCoverage';
import TierNamePicker from './TierNamePicker.vue';

const props = defineProps({
  projectId: { type: Number, required: true },
  baselineTiers: { type: Array, required: true },
  tierGroups: { type: Array, required: true },
  canManage: { type: Boolean, default: false },
});
const emit = defineEmits(['saved']);

const { t } = useI18n();
const messages = useEventMessageStore();
const editing = ref(false);
const pending = ref(false);
const error = ref('');
const form = ref(new Set());

function toggleEditor() {
  editing.value = !editing.value;
  form.value = new Set(props.baselineTiers);
  error.value = '';
}

function toggleName(name) {
  const next = new Set(form.value);
  if (next.has(name)) next.delete(name);
  else next.add(name);
  form.value = next;
}

async function save() {
  pending.value = true;
  error.value = '';
  try {
    const result = await updateProjectBaselineTiers(props.projectId, [
      ...form.value,
    ]);
    editing.value = false;
    emit('saved', result.tier_names);
    messages.addMessage(t('researchScopes.messages.baselineSaved'), 'success');
  } catch {
    error.value = t('researchScopes.messages.baselineSaveFailed');
  } finally {
    pending.value = false;
  }
}
</script>
