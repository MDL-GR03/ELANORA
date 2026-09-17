<template>
  <div class="rule-builder">
    <section class="builder-section tier-section">
      <header>
        <div>
          <span class="step">{{ t('protocolRules.tiers.step') }}</span>
          <h5>{{ t('protocolRules.tiers.title') }}</h5>
          <p>{{ t('protocolRules.tiers.description') }}</p>
        </div>
      </header>

      <div v-if="tiers.length" class="tier-workspace">
        <div
          class="tier-table"
          role="list"
          :aria-label="t('protocolRules.tiers.list')"
        >
          <article v-for="tier in tiers" :key="tier.name" role="listitem">
            <div class="tier-name">
              <span aria-hidden="true">T</span>
              <strong>{{ tier.name }}</strong>
              <small>{{ t('protocolRules.tiers.required') }}</small>
            </div>
            <label :for="`protocol-parent-${tier.name}`">
              {{ t('protocolRules.tiers.parent') }}
              <AppSelect
                :id="`protocol-parent-${tier.name}`"
                :model-value="tier.parent"
                size="small"
                :options="parentSelectOptions(tier.name)"
                @change="setTierField(tier.name, 'parent', $event)"
              />
            </label>
            <label>
              {{ t('protocolRules.tiers.type') }}
              <input
                :value="tier.type"
                :placeholder="t('protocolRules.tiers.any_type')"
                @change="setTierField(tier.name, 'type', $event.target.value)"
              />
            </label>
            <button
              class="remove-button"
              type="button"
              :aria-label="t('protocolRules.tiers.remove', { name: tier.name })"
              @click="removeTier(tier.name)"
            >
              {{ t('protocolRules.remove') }}
            </button>
          </article>
        </div>

        <aside class="hierarchy-preview">
          <span class="preview-label">{{
            t('protocolRules.tiers.preview')
          }}</span>
          <ProtocolTierTree :nodes="tierTree" />
          <p v-if="orphanedTiers.length" class="preview-warning">
            {{
              t('protocolRules.tiers.orphaned', {
                tiers: orphanedTiers.join(', '),
              })
            }}
          </p>
        </aside>
      </div>
      <div v-else class="empty-builder">
        {{ t('protocolRules.tiers.empty') }}
      </div>

      <div class="add-tier">
        <label>
          {{ t('protocolRules.tiers.name') }}
          <input
            v-model.trim="newTier.name"
            :placeholder="t('protocolRules.tiers.name_placeholder')"
            @keydown.enter.prevent="addTier"
          />
        </label>
        <label for="new-protocol-tier-parent">
          {{ t('protocolRules.tiers.parent') }}
          <AppSelect
            id="new-protocol-tier-parent"
            v-model="newTier.parent"
            size="small"
            :options="newTierParentOptions"
          />
        </label>
        <label>
          {{ t('protocolRules.tiers.type') }}
          <input
            v-model.trim="newTier.type"
            :placeholder="t('protocolRules.optional')"
            @keydown.enter.prevent="addTier"
          />
        </label>
        <button type="button" :disabled="!newTier.name" @click="addTier">
          {{ t('protocolRules.tiers.add') }}
        </button>
      </div>
      <p v-if="tierError" class="field-error" role="alert">{{ tierError }}</p>
    </section>

    <section class="builder-section">
      <header>
        <div>
          <span class="step">{{ t('protocolRules.vocabularies.step') }}</span>
          <h5>{{ t('protocolRules.vocabularies.title') }}</h5>
          <p>{{ t('protocolRules.vocabularies.description') }}</p>
        </div>
      </header>
      <ul
        v-if="vocabularies.length"
        class="vocabulary-list"
        :aria-label="t('protocolRules.vocabularies.title')"
      >
        <li v-for="vocabulary in vocabularies" :key="vocabulary">
          <strong>{{ vocabulary }}</strong>
          <label>
            {{ t('protocolRules.vocabularies.languages') }}
            <input
              :value="
                (modelValue.vocabulary_languages?.[vocabulary] || []).join(', ')
              "
              :placeholder="
                t('protocolRules.vocabularies.languages_placeholder')
              "
              @change="setVocabularyLanguages(vocabulary, $event.target.value)"
            />
          </label>
          <button
            class="remove-button"
            type="button"
            :aria-label="t('protocolRules.remove_named', { name: vocabulary })"
            @click="removeVocabulary(vocabulary)"
          >
            {{ t('protocolRules.remove') }}
          </button>
        </li>
      </ul>
      <div class="inline-add">
        <input
          v-model.trim="newVocabulary"
          :aria-label="t('protocolRules.vocabularies.identifier')"
          :placeholder="t('protocolRules.vocabularies.identifier_placeholder')"
          @keydown.enter.prevent="addVocabulary"
        />
        <button type="button" :disabled="!newVocabulary" @click="addVocabulary">
          {{ t('protocolRules.vocabularies.add') }}
        </button>
      </div>
    </section>

    <section class="builder-section">
      <header>
        <div>
          <span class="step">{{ t('protocolRules.media.step') }}</span>
          <h5>{{ t('protocolRules.media.title') }}</h5>
          <p>{{ t('protocolRules.media.description') }}</p>
        </div>
        <label class="switch-label">
          <input
            :checked="modelValue.media_required"
            type="checkbox"
            @change="setMediaRequired($event.target.checked)"
          />
          <span>{{ t('protocolRules.media.required') }}</span>
        </label>
      </header>
      <fieldset :disabled="!modelValue.media_required">
        <legend>{{ t('protocolRules.media.formats') }}</legend>
        <label v-for="mimeType in commonMediaTypes" :key="mimeType">
          <input
            type="checkbox"
            :checked="mediaTypes.includes(mimeType)"
            @change="toggleMediaType(mimeType, $event.target.checked)"
          />
          {{ mediaTypeLabel(mimeType) }}
          <small>{{ mimeType }}</small>
        </label>
      </fieldset>
      <div
        v-if="customMediaTypes.length"
        class="chips"
        :aria-label="t('protocolRules.media.other_formats')"
      >
        <span v-for="mimeType in customMediaTypes" :key="mimeType">
          {{ mimeType }}
          <button
            type="button"
            :aria-label="t('protocolRules.remove_named', { name: mimeType })"
            @click="toggleMediaType(mimeType, false)"
          >
            ×
          </button>
        </span>
      </div>
      <div class="inline-add">
        <input
          v-model.trim="newMediaType"
          :disabled="!modelValue.media_required"
          :aria-label="t('protocolRules.media.other_type')"
          :placeholder="t('protocolRules.media.other_placeholder')"
          @keydown.enter.prevent="addMediaType"
        />
        <button
          type="button"
          :disabled="!modelValue.media_required || !newMediaType"
          @click="addMediaType"
        >
          {{ t('protocolRules.media.add') }}
        </button>
      </div>
    </section>

    <section class="builder-section">
      <header>
        <div>
          <span class="step">{{ t('protocolRules.quality.step') }}</span>
          <h5>{{ t('protocolRules.quality.title') }}</h5>
          <p>{{ t('protocolRules.quality.description') }}</p>
        </div>
      </header>
      <ProtocolTierChecks
        :model-value="modelValue"
        @update:model-value="emit('update:modelValue', $event)"
      />
    </section>

    <section class="builder-section">
      <header>
        <div>
          <span class="step">{{ t('protocolRules.types.step') }}</span>
          <h5>{{ t('protocolRules.types.title') }}</h5>
          <p>{{ t('protocolRules.types.description') }}</p>
        </div>
      </header>
      <ProtocolTypeConstraints
        :model-value="modelValue"
        @update:model-value="emit('update:modelValue', $event)"
      />
    </section>

    <section class="builder-section">
      <header>
        <div>
          <span class="step">{{ t('protocolRules.filenames.step') }}</span>
          <h5>{{ t('protocolRules.filenames.title') }}</h5>
          <p>{{ t('protocolRules.filenames.description') }}</p>
        </div>
      </header>
      <div v-if="filenameStandard" class="filename-standard">
        <div>
          <strong>{{ filenameStandard.name }}</strong>
          <code>{{ filenameStandard.pattern }}</code>
        </div>
        <ul :aria-label="t('protocolRules.filenames.components')">
          <li
            v-for="component in filenameStandard.components"
            :key="component.name"
          >
            <code>{{ placeholder(component.name) }}</code>
            <span>{{
              component.regex || t('protocolRules.filenames.any_text')
            }}</span>
            <small v-if="component.accepted_values?.length">
              {{
                t('protocolRules.filenames.accepted', {
                  values: component.accepted_values.join(', '),
                })
              }}
            </small>
          </li>
        </ul>
        <button
          class="remove-button"
          type="button"
          @click="update({ filename_standard: null })"
        >
          {{ t('protocolRules.filenames.remove') }}
        </button>
      </div>
      <p v-else class="empty-builder">
        {{ t('protocolRules.filenames.empty') }}
      </p>
    </section>

    <section class="builder-section">
      <header>
        <div>
          <span class="step">{{ t('protocolRules.enforcement.step') }}</span>
          <h5>{{ t('protocolRules.enforcement.title') }}</h5>
          <p>{{ t('protocolRules.enforcement.description') }}</p>
        </div>
      </header>
      <ProtocolRuleSeverities
        :model-value="modelValue"
        @update:model-value="emit('update:modelValue', $event)"
      />
    </section>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n';
import { computed, reactive, ref } from 'vue';
import AppSelect from '@/components/common/AppSelect.vue';
import {
  parseLanguages,
  withMappingValue,
  withoutTier,
  withoutVocabulary,
} from '@/utils/protocolRules';
import ProtocolRuleSeverities from './ProtocolRuleSeverities.vue';
import ProtocolTierChecks from './ProtocolTierChecks.vue';
import ProtocolTierTree from './ProtocolTierTree.vue';
import ProtocolTypeConstraints from './ProtocolTypeConstraints.vue';

const { t } = useI18n();

const props = defineProps({
  modelValue: {
    type: Object,
    required: true,
  },
});
const emit = defineEmits(['update:modelValue']);

const newTier = reactive({ name: '', parent: '', type: '' });
const newVocabulary = ref('');
const newMediaType = ref('');
const tierError = ref('');
const commonMediaTypes = ['video/mp4', 'audio/wav', 'audio/mpeg'];

const tiers = computed(() =>
  (props.modelValue.required_tiers || []).map((name) => ({
    name,
    parent: props.modelValue.tier_parents?.[name] || '',
    type: props.modelValue.tier_linguistic_types?.[name] || '',
  }))
);
const vocabularies = computed(
  () => props.modelValue.required_controlled_vocabularies || []
);
const filenameStandard = computed(() => props.modelValue.filename_standard);
const placeholder = (name) => `{${name}}`;
const mediaTypes = computed(
  () => props.modelValue.allowed_media_mime_types || []
);
const customMediaTypes = computed(() =>
  mediaTypes.value.filter((mimeType) => !commonMediaTypes.includes(mimeType))
);
const orphanedTiers = computed(() =>
  tiers.value
    .filter(
      (tier) =>
        tier.parent && !props.modelValue.required_tiers.includes(tier.parent)
    )
    .map((tier) => tier.name)
);
const tierTree = computed(() => {
  const nodes = new Map(
    tiers.value.map((tier) => [tier.name, { ...tier, children: [] }])
  );
  const roots = [];
  nodes.forEach((node) => {
    const parent = nodes.get(node.parent);
    if (parent && parent !== node) parent.children.push(node);
    else roots.push(node);
  });
  return roots;
});

const update = (changes) =>
  emit('update:modelValue', { ...props.modelValue, ...changes });
const parentChoices = (name) =>
  tiers.value.filter((tier) => tier.name !== name).map((tier) => tier.name);
const parentSelectOptions = (name) => [
  { value: '', label: t('protocolRules.tiers.no_parent') },
  ...parentChoices(name).map((candidate) => ({
    value: candidate,
    label: candidate,
  })),
];
const newTierParentOptions = computed(() => [
  { value: '', label: t('protocolRules.tiers.no_parent') },
  ...tiers.value.map((tier) => ({ value: tier.name, label: tier.name })),
]);
const setTierField = (name, field, rawValue) => {
  const value = rawValue.trim();
  const key = field === 'parent' ? 'tier_parents' : 'tier_linguistic_types';
  const mapping = { ...(props.modelValue[key] || {}) };
  if (field === 'parent' && value) {
    let ancestor = value;
    while (ancestor) {
      if (ancestor === name) {
        tierError.value = t('protocolRules.tiers.cycle');
        return;
      }
      ancestor = mapping[ancestor];
    }
  }
  tierError.value = '';
  if (value) mapping[name] = value;
  else delete mapping[name];
  update({ [key]: mapping });
};
const addTier = () => {
  const name = newTier.name.trim();
  if (!name) return;
  if (props.modelValue.required_tiers.includes(name)) {
    tierError.value = t('protocolRules.tiers.duplicate', { name });
    return;
  }
  tierError.value = '';
  const requiredTiers = [...props.modelValue.required_tiers, name];
  const parents = { ...(props.modelValue.tier_parents || {}) };
  const types = { ...(props.modelValue.tier_linguistic_types || {}) };
  if (newTier.parent) parents[name] = newTier.parent;
  if (newTier.type) types[name] = newTier.type;
  update({
    required_tiers: requiredTiers,
    tier_parents: parents,
    tier_linguistic_types: types,
  });
  Object.assign(newTier, { name: '', parent: '', type: '' });
};
const removeTier = (name) => update(withoutTier(props.modelValue, name));
const addVocabulary = () => {
  const value = newVocabulary.value.trim();
  if (!value || vocabularies.value.includes(value)) return;
  update({
    required_controlled_vocabularies: [...vocabularies.value, value],
  });
  newVocabulary.value = '';
};
const removeVocabulary = (value) =>
  update(withoutVocabulary(props.modelValue, value));
const setVocabularyLanguages = (vocabulary, text) =>
  update(
    withMappingValue(
      props.modelValue,
      'vocabulary_languages',
      vocabulary,
      parseLanguages(text)
    )
  );
const setMediaRequired = (required) => update({ media_required: required });
const toggleMediaType = (mimeType, checked) =>
  update({
    allowed_media_mime_types: checked
      ? [...new Set([...mediaTypes.value, mimeType])]
      : mediaTypes.value.filter((item) => item !== mimeType),
  });
const addMediaType = () => {
  const value = newMediaType.value.trim().toLowerCase();
  if (!value || mediaTypes.value.includes(value)) return;
  update({ allowed_media_mime_types: [...mediaTypes.value, value] });
  newMediaType.value = '';
};
const mediaTypeLabel = (mimeType) =>
  ({
    'video/mp4': t('protocolRules.media.mp4'),
    'audio/wav': t('protocolRules.media.wav'),
    'audio/mpeg': t('protocolRules.media.mp3'),
  })[mimeType];
</script>

<style scoped>
.rule-builder {
  display: grid;
  gap: 1rem;
}

.builder-section {
  display: grid;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.builder-section > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.builder-section h5,
.builder-section p {
  margin: 0;
}

.builder-section h5 {
  margin-top: 0.15rem;
  color: var(--color-text);
  font-size: 1rem;
}

.builder-section header p {
  margin-top: 0.2rem;
  color: var(--color-text-muted);
  font-size: 0.86rem;
}

.step,
.preview-label {
  color: var(--color-primary);
  font-size: 0.7rem;
  font-weight: 850;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}

.tier-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(16rem, 0.75fr);
  gap: 1rem;
}

.tier-table {
  display: grid;
  gap: 0.55rem;
}

.tier-table article {
  display: grid;
  grid-template-columns:
    minmax(10rem, 1fr) minmax(9rem, 0.8fr) minmax(11rem, 1fr)
    auto;
  align-items: end;
  gap: 0.65rem;
  padding: 0.75rem;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-primary-bg);
}

.tier-name {
  display: grid;
  grid-template-columns: 1.7rem 1fr;
  align-items: center;
  gap: 0 0.55rem;
  min-width: 0;
}

.tier-name > span {
  display: grid;
  grid-row: 1 / span 2;
  width: 1.7rem;
  height: 1.7rem;
  place-items: center;
  border-radius: var(--radius-sm);
  background: var(--color-primary-subtle);
  color: var(--color-primary);
  font-size: 0.72rem;
  font-weight: 900;
}

.tier-name strong {
  overflow: hidden;
  text-overflow: ellipsis;
}

.tier-name small {
  color: var(--color-success-dark);
  font-size: 0.72rem;
  font-weight: 750;
}

label {
  display: grid;
  gap: 0.3rem;
  color: var(--color-gray-700);
  font-size: 0.75rem;
  font-weight: 750;
}

input,
select {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  padding: 0.6rem 0.7rem;
  background: var(--color-surface);
  color: var(--color-text);
  font: inherit;
  font-size: 0.86rem;
}

.hierarchy-preview {
  display: grid;
  align-content: start;
  gap: 0.75rem;
  min-width: 0;
  padding: 0.9rem;
  border: 1px solid var(--color-info-bg);
  border-radius: var(--radius-lg);
  background: var(--color-info-bg);
  overflow: auto;
}

.preview-warning,
.field-error {
  color: var(--color-error-dark);
  font-size: 0.8rem;
}

.add-tier {
  display: grid;
  grid-template-columns: 1fr 0.8fr 1fr auto;
  align-items: end;
  gap: 0.65rem;
  padding-top: 0.9rem;
  border-top: 1px solid var(--color-border-strong);
}

button {
  min-height: 2.45rem;
  border: 0;
  border-radius: var(--radius-md);
  padding: 0.6rem 0.85rem;
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font: inherit;
  font-size: 0.82rem;
  font-weight: 750;
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.remove-button {
  border: 1px solid var(--color-error-bg);
  background: var(--color-surface);
  color: var(--color-error);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.chips > span {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  border-radius: var(--radius-full);
  padding: 0.35rem 0.5rem 0.35rem 0.7rem;
  background: var(--color-info-bg);
  color: var(--color-primary-dark);
  font-size: 0.82rem;
  font-weight: 700;
}

.chips button {
  min-height: 1.3rem;
  width: 1.3rem;
  padding: 0;
  border-radius: var(--radius-full);
  background: rgb(255 255 255 / 70%);
  color: inherit;
}

.vocabulary-list {
  display: grid;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.vocabulary-list li {
  display: grid;
  grid-template-columns: minmax(10rem, 1fr) minmax(14rem, 1.4fr) auto;
  align-items: end;
  gap: 0.65rem;
  padding: 0.6rem 0.75rem;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-primary-bg);
}

.vocabulary-list strong {
  align-self: center;
  overflow: hidden;
  text-overflow: ellipsis;
}

.filename-standard {
  display: grid;
  gap: 0.6rem;
  justify-items: start;
}

.filename-standard > div {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem;
}

.filename-standard ul {
  display: grid;
  gap: 0.35rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.filename-standard li {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  color: var(--color-gray-700);
  font-size: 0.84rem;
}

.inline-add {
  display: grid;
  grid-template-columns: minmax(12rem, 24rem) auto;
  justify-content: start;
  gap: 0.6rem;
}

.switch-label {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  border-radius: var(--radius-full);
  padding: 0.55rem 0.75rem;
  background: var(--color-primary-subtle);
  color: var(--color-primary-dark);
}

.switch-label input,
fieldset input {
  width: auto;
}

fieldset {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  padding: 0;
  border: 0;
}

fieldset legend {
  margin-bottom: 0.55rem;
  color: var(--color-gray-700);
  font-size: 0.78rem;
  font-weight: 750;
}

fieldset label {
  display: grid;
  grid-template-columns: auto auto;
  align-items: center;
  gap: 0 0.45rem;
  min-width: 10rem;
  padding: 0.65rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
  color: var(--color-text);
}

fieldset label small {
  grid-column: 2;
  color: var(--color-text-muted);
  font-size: 0.7rem;
  font-weight: 500;
}

.empty-builder {
  padding: 1rem;
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-lg);
  color: var(--color-text-muted);
  text-align: center;
}

@media (width <= 1000px) {
  .tier-workspace {
    grid-template-columns: 1fr;
  }

  .tier-table article,
  .add-tier {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (width <= 640px) {
  .builder-section > header,
  .vocabulary-list li,
  .tier-table article,
  .add-tier {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .builder-section > header {
    display: grid;
  }

  .inline-add {
    grid-template-columns: 1fr;
  }
}
</style>
