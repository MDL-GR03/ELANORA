<template>
  <form class="topic-editor" @submit.prevent="submit">
    <header>
      <div>
        <span class="tier-export-eyebrow">{{
          topic
            ? t('researchScopes.topics.editEyebrow')
            : t('researchScopes.topics.newEyebrow')
        }}</span>
        <h3>{{ t('researchScopes.topics.editorTitle') }}</h3>
      </div>
      <button type="button" class="topic-link-button" @click="emit('cancel')">
        {{ t('common.cancel') }}
      </button>
    </header>
    <div class="topic-fields">
      <label>
        <span>{{ t('researchScopes.topics.name') }}</span>
        <input
          v-model.trim="name"
          required
          maxlength="100"
          :placeholder="t('researchScopes.topics.namePlaceholder')"
        />
      </label>
      <label>
        <span>{{ t('researchScopes.topics.explanation') }}</span>
        <textarea
          v-model.trim="description"
          maxlength="1000"
          rows="2"
          :placeholder="t('researchScopes.topics.explanationPlaceholder')"
        />
      </label>
    </div>
    <label class="topic-search">
      <span>{{ t('researchScopes.topics.findTiers') }}</span>
      <input
        v-model="tierSearch"
        :placeholder="t('researchScopes.topics.findTiersPlaceholder')"
      />
    </label>
    <TierNamePicker
      :names="filteredTierNames"
      :selected="tierNames"
      :tier-groups="tierGroups"
      @toggle="toggleTier"
    />
    <label class="topic-new-tier-policy">
      <input v-model="allowNewTiers" type="checkbox" />
      <span>
        <strong>{{ t('researchScopes.topics.allowNew') }}</strong>
        <small>{{ t('researchScopes.topics.allowNewHint') }}</small>
      </span>
    </label>
    <footer>
      <span>{{
        t('researchScopes.topics.selected', { count: tierNames.size })
      }}</span>
      <button
        class="tiers-primary-button"
        type="submit"
        :disabled="!name || !tierNames.size || pending"
      >
        {{ pending ? t('common.saving') : t('researchScopes.topics.save') }}
      </button>
    </footer>
  </form>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { allTierNamesOf } from '@/utils/tierCoverage';
import TierNamePicker from './TierNamePicker.vue';

/** Mounted afresh for each topic, so the form starts from `topic`. */
const props = defineProps({
  topic: { type: Object, default: null },
  tierGroups: { type: Array, required: true },
  pending: { type: Boolean, default: false },
});
const emit = defineEmits(['save', 'cancel']);

const { t } = useI18n();
const name = ref(props.topic?.name ?? '');
const description = ref(props.topic?.description ?? '');
const tierNames = ref(new Set(props.topic?.tier_names ?? []));
const allowNewTiers = ref(props.topic?.allow_new_tiers ?? false);
const tierSearch = ref('');

const filteredTierNames = computed(() => {
  const query = tierSearch.value.toLowerCase();
  return allTierNamesOf(props.tierGroups).filter((tierName) =>
    tierName.toLowerCase().includes(query)
  );
});

function toggleTier(tierName) {
  const next = new Set(tierNames.value);
  if (next.has(tierName)) next.delete(tierName);
  else next.add(tierName);
  tierNames.value = next;
}

function submit() {
  emit('save', {
    name: name.value,
    description: description.value || null,
    tier_names: [...tierNames.value],
    allow_new_tiers: allowNewTiers.value,
  });
}
</script>
