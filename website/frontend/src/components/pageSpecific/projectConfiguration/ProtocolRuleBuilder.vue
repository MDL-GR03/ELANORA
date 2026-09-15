<template>
  <div class="rule-builder">
    <section class="builder-section tier-section">
      <header>
        <div>
          <span class="step">1 · Annotation structure</span>
          <h5>Required tiers and relationships</h5>
          <p>Add the tiers every submitted ELAN file must contain.</p>
        </div>
      </header>

      <div v-if="tiers.length" class="tier-workspace">
        <div class="tier-table" role="list" aria-label="Required tiers">
          <article v-for="tier in tiers" :key="tier.name" role="listitem">
            <div class="tier-name">
              <span aria-hidden="true">T</span>
              <strong>{{ tier.name }}</strong>
              <small>Required</small>
            </div>
            <label :for="`protocol-parent-${tier.name}`">
              Parent tier
              <AppSelect
                :id="`protocol-parent-${tier.name}`"
                :model-value="tier.parent"
                size="small"
                :options="parentSelectOptions(tier.name)"
                @change="setTierField(tier.name, 'parent', $event)"
              />
            </label>
            <label>
              Linguistic type
              <input
                :value="tier.type"
                placeholder="Any type"
                @change="setTierField(tier.name, 'type', $event.target.value)"
              />
            </label>
            <button
              class="remove-button"
              type="button"
              :aria-label="`Remove required tier ${tier.name}`"
              @click="removeTier(tier.name)"
            >
              Remove
            </button>
          </article>
        </div>

        <aside class="hierarchy-preview">
          <span class="preview-label">Structure preview</span>
          <ProtocolTierTree :nodes="tierTree" />
          <p v-if="orphanedTiers.length" class="preview-warning">
            Choose an available parent for: {{ orphanedTiers.join(', ') }}.
          </p>
        </aside>
      </div>
      <div v-else class="empty-builder">
        No tiers added yet. Start with one important tier from the project’s
        ELAN template.
      </div>

      <div class="add-tier">
        <label>
          Tier name
          <input
            v-model.trim="newTier.name"
            placeholder="For example: Manual signs"
            @keydown.enter.prevent="addTier"
          />
        </label>
        <label for="new-protocol-tier-parent">
          Parent tier
          <AppSelect
            id="new-protocol-tier-parent"
            v-model="newTier.parent"
            size="small"
            :options="newTierParentOptions"
          />
        </label>
        <label>
          Linguistic type
          <input
            v-model.trim="newTier.type"
            placeholder="Optional"
            @keydown.enter.prevent="addTier"
          />
        </label>
        <button type="button" :disabled="!newTier.name" @click="addTier">
          Add required tier
        </button>
      </div>
      <p v-if="tierError" class="field-error" role="alert">{{ tierError }}</p>
    </section>

    <section class="builder-section">
      <header>
        <div>
          <span class="step">2 · Terminology</span>
          <h5>Required controlled vocabularies</h5>
          <p>Require the shared vocabularies used by this research project.</p>
        </div>
      </header>
      <ul
        v-if="vocabularies.length"
        class="vocabulary-list"
        aria-label="Required controlled vocabularies"
      >
        <li v-for="vocabulary in vocabularies" :key="vocabulary">
          <strong>{{ vocabulary }}</strong>
          <label>
            Values required in languages
            <input
              :value="
                (modelValue.vocabulary_languages?.[vocabulary] || []).join(', ')
              "
              placeholder="Any, or for example: en, fr"
              @change="setVocabularyLanguages(vocabulary, $event.target.value)"
            />
          </label>
          <button
            class="remove-button"
            type="button"
            :aria-label="`Remove ${vocabulary}`"
            @click="removeVocabulary(vocabulary)"
          >
            Remove
          </button>
        </li>
      </ul>
      <div class="inline-add">
        <input
          v-model.trim="newVocabulary"
          aria-label="Controlled vocabulary identifier"
          placeholder="For example: lsfb_vocabulaire"
          @keydown.enter.prevent="addVocabulary"
        />
        <button type="button" :disabled="!newVocabulary" @click="addVocabulary">
          Add vocabulary
        </button>
      </div>
    </section>

    <section class="builder-section">
      <header>
        <div>
          <span class="step">3 · Research media</span>
          <h5>Linked recordings</h5>
          <p>Define whether annotations must reference video or audio.</p>
        </div>
        <label class="switch-label">
          <input
            :checked="modelValue.media_required"
            type="checkbox"
            @change="setMediaRequired($event.target.checked)"
          />
          <span>Require linked media</span>
        </label>
      </header>
      <fieldset :disabled="!modelValue.media_required">
        <legend>Accepted media formats</legend>
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
        aria-label="Other accepted media formats"
      >
        <span v-for="mimeType in customMediaTypes" :key="mimeType">
          {{ mimeType }}
          <button
            type="button"
            :aria-label="`Remove ${mimeType}`"
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
          aria-label="Other media MIME type"
          placeholder="Other format, for example video/webm"
          @keydown.enter.prevent="addMediaType"
        />
        <button
          type="button"
          :disabled="!modelValue.media_required || !newMediaType"
          @click="addMediaType"
        >
          Add format
        </button>
      </div>
    </section>

    <section class="builder-section">
      <header>
        <div>
          <span class="step">4 · Annotation quality</span>
          <h5>Checks on each required tier</h5>
          <p>
            Require tier metadata and complete annotations. Vocabulary checks
            use the vocabulary named by the tier’s linguistic type.
          </p>
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
          <span class="step">5 · Linguistic types</span>
          <h5>Constraint stereotypes</h5>
          <p>
            Require how annotations of a linguistic type relate to a parent.
          </p>
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
          <span class="step">6 · Filenames</span>
          <h5>Filename standard</h5>
          <p>
            A frozen copy of a naming standard. Later changes to the project’s
            naming settings do not alter it.
          </p>
        </div>
      </header>
      <div v-if="filenameStandard" class="filename-standard">
        <div>
          <strong>{{ filenameStandard.name }}</strong>
          <code>{{ filenameStandard.pattern }}</code>
        </div>
        <ul aria-label="Filename components">
          <li
            v-for="component in filenameStandard.components"
            :key="component.name"
          >
            <code>{{ placeholder(component.name) }}</code>
            <span>{{ component.regex || 'Any text' }}</span>
            <small v-if="component.accepted_values?.length">
              Accepted: {{ component.accepted_values.join(', ') }}
            </small>
          </li>
        </ul>
        <button
          class="remove-button"
          type="button"
          @click="update({ filename_standard: null })"
        >
          Remove filename standard
        </button>
      </div>
      <p v-else class="empty-builder">
        No filename standard. Uploads follow the project’s naming settings.
      </p>
    </section>

    <section class="builder-section">
      <header>
        <div>
          <span class="step">7 · Enforcement</span>
          <h5>What happens when a rule is not met</h5>
          <p>
            Refused files never enter the project. Warnings let the file through
            and are shown to reviewers.
          </p>
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
  { value: '', label: 'No parent' },
  ...parentChoices(name).map((candidate) => ({
    value: candidate,
    label: candidate,
  })),
];
const newTierParentOptions = computed(() => [
  { value: '', label: 'No parent' },
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
        tierError.value = 'A tier cannot be placed below one of its children.';
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
    tierError.value = `The tier “${name}” is already required.`;
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
    'video/mp4': 'MP4 video',
    'audio/wav': 'WAV audio',
    'audio/mpeg': 'MP3 audio',
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
  border: 1px solid #dbe3ef;
  border-radius: 0.85rem;
  background: #fff;
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
  color: #14213d;
  font-size: 1rem;
}

.builder-section header p {
  margin-top: 0.2rem;
  color: #64748b;
  font-size: 0.86rem;
}

.step,
.preview-label {
  color: #2563eb;
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
  border: 1px solid #e2e8f0;
  border-radius: 0.7rem;
  background: #fbfdff;
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
  border-radius: 0.5rem;
  background: #eff6ff;
  color: #2563eb;
  font-size: 0.72rem;
  font-weight: 900;
}

.tier-name strong {
  overflow: hidden;
  text-overflow: ellipsis;
}

.tier-name small {
  color: #15803d;
  font-size: 0.72rem;
  font-weight: 750;
}

label {
  display: grid;
  gap: 0.3rem;
  color: #475569;
  font-size: 0.75rem;
  font-weight: 750;
}

input,
select {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  border-radius: 0.55rem;
  padding: 0.6rem 0.7rem;
  background: #fff;
  color: #14213d;
  font: inherit;
  font-size: 0.86rem;
}

.hierarchy-preview {
  display: grid;
  align-content: start;
  gap: 0.75rem;
  min-width: 0;
  padding: 0.9rem;
  border: 1px solid #bfdbfe;
  border-radius: 0.75rem;
  background: #f8fbff;
  overflow: auto;
}

.preview-warning,
.field-error {
  color: #b45309;
  font-size: 0.8rem;
}

.add-tier {
  display: grid;
  grid-template-columns: 1fr 0.8fr 1fr auto;
  align-items: end;
  gap: 0.65rem;
  padding-top: 0.9rem;
  border-top: 1px solid #e2e8f0;
}

button {
  min-height: 2.45rem;
  border: 0;
  border-radius: 0.6rem;
  padding: 0.6rem 0.85rem;
  background: #2563eb;
  color: #fff;
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
  border: 1px solid #fecaca;
  background: #fff;
  color: #b91c1c;
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
  border-radius: 999px;
  padding: 0.35rem 0.5rem 0.35rem 0.7rem;
  background: #eef2ff;
  color: #3730a3;
  font-size: 0.82rem;
  font-weight: 700;
}

.chips button {
  min-height: 1.3rem;
  width: 1.3rem;
  padding: 0;
  border-radius: 50%;
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
  border: 1px solid #e2e8f0;
  border-radius: 0.7rem;
  background: #fbfdff;
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
  color: #475569;
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
  border-radius: 999px;
  padding: 0.55rem 0.75rem;
  background: #eff6ff;
  color: #1e3a8a;
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
  color: #475569;
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
  border: 1px solid #dbe3ef;
  border-radius: 0.65rem;
  background: #f8fafc;
  color: #14213d;
}

fieldset label small {
  grid-column: 2;
  color: #64748b;
  font-size: 0.7rem;
  font-weight: 500;
}

.empty-builder {
  padding: 1rem;
  border: 1px dashed #cbd5e1;
  border-radius: 0.7rem;
  color: #64748b;
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
