<template>
  <section class="suggestion-panel" aria-labelledby="suggestion-title">
    <header>
      <div>
        <span class="eyebrow">Corpus-assisted setup</span>
        <div class="title-line">
          <h4 id="suggestion-title">Suggested protocol structure</h4>
          <HelpTooltip
            title="Evidence, not automatic decisions"
            text="ELANora compares the latest accepted revision of every file. Suggestions only enter your editable draft when you select them."
          />
        </div>
        <p>
          Based on {{ suggestion.analyzed_files }} of
          {{ suggestion.total_files }} latest accepted ELAN file revisions.
          Review every choice before creating a draft.
        </p>
      </div>
      <button class="close-button" type="button" @click="$emit('close')">
        Close
      </button>
    </header>

    <div v-if="!suggestion.analyzed_files" class="empty-analysis">
      <strong>No accepted ELAN revisions could be analyzed.</strong>
      <p>Upload and accept at least one valid EAF file, then try again.</p>
    </div>
    <template v-else>
      <div class="analysis-summary">
        <div>
          <strong>{{ suggestedTierCount }}</strong>
          <span class="metric-label"
            >tiers found in every file
            <HelpTooltip
              label="Explain universal tiers"
              text="These tier identifiers occur in every analyzed file and are the strongest candidates for a shared required baseline."
          /></span>
        </div>
        <div>
          <strong>{{ recurringTierCount }}</strong>
          <span class="metric-label"
            >tiers found in at least half
            <HelpTooltip
              label="Explain common tiers"
              text="These tiers are common but not universal. Selecting one will cause files without it to fail the protocol check."
          /></span>
        </div>
        <div>
          <strong>{{ conflictCount }}</strong>
          <span class="metric-label"
            >relationships to review
            <HelpTooltip
              label="Explain relationships to review"
              text="At least two files disagree about a tier's parent or linguistic type. ELANora will not apply that relationship automatically."
          /></span>
        </div>
        <div>
          <strong>{{ suggestion.files_with_media }}</strong>
          <span class="metric-label"
            >files linked to media
            <HelpTooltip
              label="Explain linked media count"
              text="The number of analyzed EAF files containing at least one ELAN media descriptor."
          /></span>
        </div>
      </div>

      <div v-if="!suggestedTierCount" class="analysis-note">
        <strong>No single tier appears in every file.</strong>
        Your corpus likely contains more than one annotation template. Common
        candidates are shown below, but none are selected automatically.
      </div>

      <div v-if="suggestion.skipped_files.length" class="analysis-warning">
        {{ suggestion.skipped_files.length }} file(s) were skipped because their
        latest revisions could not be validated.
      </div>

      <div class="suggestion-tools">
        <label class="search-control">
          <span>Find a tier</span>
          <input v-model.trim="query" placeholder="Search tier names" />
        </label>
        <label class="filter-control">
          <span>Show</span>
          <AppSelect
            id="protocol-tier-evidence-filter"
            v-model="filter"
            size="small"
            :options="filterOptions"
          />
        </label>
      </div>

      <div
        class="evidence-guide"
        aria-label="Explanation of suggestion evidence"
      >
        <span>
          Coverage
          <HelpTooltip
            label="Explain tier coverage"
            text="Coverage is the percentage of analyzed files in which a tier identifier appears at least once."
          />
        </span>
        <span>
          Consistency
          <HelpTooltip
            label="Explain relationship consistency"
            text="Consistency is calculated only among files containing that tier. It measures how often those files agree on the same parent or linguistic type."
          />
        </span>
        <span>
          Evidence label
          <HelpTooltip
            label="Explain evidence labels"
            text="Evidence labels describe how widely a tier occurs. They do not decide whether a convention is scientifically correct."
          />
        </span>
      </div>

      <div class="candidate-list">
        <label
          v-for="tier in visibleTiers"
          :key="tier.tier_id"
          class="candidate"
        >
          <input
            type="checkbox"
            :checked="selectedTiers.has(tier.tier_id)"
            @change="toggleTier(tier.tier_id, $event.target.checked)"
          />
          <span class="candidate-copy">
            <strong>{{ tier.tier_id }}</strong>
            <small class="evidence-line">
              Coverage: {{ tier.occurrence_count }} of
              {{ suggestion.analyzed_files }} files ·
              {{ tier.coverage_percent }}%
            </small>
            <small v-if="tier.parent_ref">
              Parent: {{ tier.parent_ref }}
              <template v-if="tier.parent_consistency_percent !== null">
                · {{ tier.parent_consistency_percent }}% consistent
              </template>
            </small>
            <small v-if="tier.linguistic_type_ref">
              Type: {{ tier.linguistic_type_ref }}
              <template
                v-if="tier.linguistic_type_consistency_percent !== null"
              >
                · {{ tier.linguistic_type_consistency_percent }}% consistent
              </template>
            </small>
          </span>
          <span :class="['confidence', confidenceClass(tier)]">
            {{ confidenceLabel(tier) }}
          </span>
        </label>
        <p v-if="!visibleTiers.length" class="no-results">
          No tiers match this view.
        </p>
      </div>

      <details v-if="suggestion.vocabulary_suggestions.length" class="extras">
        <summary>
          <span>Controlled vocabularies</span>
          <small>{{ suggestion.vocabulary_suggestions.length }} observed</small>
        </summary>
        <div class="extra-options">
          <label
            v-for="item in suggestion.vocabulary_suggestions"
            :key="item.vocabulary_id"
          >
            <input
              type="checkbox"
              :checked="selectedVocabularies.has(item.vocabulary_id)"
              @change="
                toggleVocabulary(item.vocabulary_id, $event.target.checked)
              "
            />
            <span>
              <strong>{{ item.vocabulary_id }}</strong>
              <small>{{ item.coverage_percent }}% of files</small>
            </span>
          </label>
        </div>
      </details>

      <footer>
        <p>
          {{ selectedTiers.size }} tier(s) selected. This will only populate the
          draft editor.
        </p>
        <button type="button" :disabled="!hasSelections" @click="apply">
          Add selected suggestions
        </button>
      </footer>
    </template>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue';
import HelpTooltip from '@/components/common/HelpTooltip.vue';
import AppSelect from '@/components/common/AppSelect.vue';

const filterOptions = [
  { value: 'core', label: 'In every file' },
  { value: 'common', label: 'Common candidates' },
  { value: 'all', label: 'All tiers' },
];

const props = defineProps({
  suggestion: {
    type: Object,
    required: true,
  },
});
const emit = defineEmits(['apply', 'close']);

const query = ref('');
const filter = ref(
  props.suggestion.tier_suggestions.some((item) => item.suggested_required)
    ? 'core'
    : 'common'
);
const selectedTiers = ref(
  new Set(
    props.suggestion.tier_suggestions
      .filter((item) => item.suggested_required)
      .map((item) => item.tier_id)
  )
);
const selectedVocabularies = ref(
  new Set(
    props.suggestion.vocabulary_suggestions
      .filter((item) => item.suggested_required)
      .map((item) => item.vocabulary_id)
  )
);
const suggestedTierCount = computed(
  () =>
    props.suggestion.tier_suggestions.filter((item) => item.suggested_required)
      .length
);
const recurringTierCount = computed(
  () =>
    props.suggestion.tier_suggestions.filter(
      (item) => !item.suggested_required && item.coverage_percent >= 50
    ).length
);
const conflictCount = computed(
  () =>
    props.suggestion.tier_suggestions.filter(
      (item) =>
        Object.keys(item.parent_variants).length > 1 ||
        Object.keys(item.linguistic_type_variants).length > 1
    ).length
);
const hasSelections = computed(
  () =>
    selectedTiers.value.size > 0 ||
    selectedVocabularies.value.size > 0 ||
    props.suggestion.files_with_media > 0
);
const visibleTiers = computed(() => {
  const normalizedQuery = query.value.toLocaleLowerCase();
  return props.suggestion.tier_suggestions.filter((tier) => {
    const matchesQuery = tier.tier_id
      .toLocaleLowerCase()
      .includes(normalizedQuery);
    const matchesFilter =
      filter.value === 'all' ||
      (filter.value === 'core' && tier.suggested_required) ||
      (filter.value === 'common' &&
        !tier.suggested_required &&
        tier.coverage_percent >= 50);
    return matchesQuery && matchesFilter;
  });
});

const replaceSetValue = (source, value, checked) => {
  const next = new Set(source.value);
  if (checked) next.add(value);
  else next.delete(value);
  source.value = next;
};
const toggleTier = (tierId, checked) =>
  replaceSetValue(selectedTiers, tierId, checked);
const toggleVocabulary = (vocabularyId, checked) =>
  replaceSetValue(selectedVocabularies, vocabularyId, checked);
const confidenceClass = (tier) => {
  if (tier.suggested_required) return 'strong';
  if (tier.coverage_percent >= 50) return 'recurring';
  return 'limited';
};
const confidenceLabel = (tier) => {
  if (tier.suggested_required) return 'In every file';
  if (tier.coverage_percent >= 50) return 'Recurring';
  return 'Limited evidence';
};
const apply = () => {
  const selected = selectedTiers.value;
  const selectedSuggestions = props.suggestion.tier_suggestions.filter((item) =>
    selected.has(item.tier_id)
  );
  const reliableParent = (item) =>
    item.parent_ref &&
    selected.has(item.parent_ref) &&
    item.parent_consistency_percent === 100;
  const reliableType = (item) =>
    item.linguistic_type_ref &&
    item.linguistic_type_consistency_percent === 100;
  emit('apply', {
    required_tiers: selectedSuggestions.map((item) => item.tier_id),
    tier_parents: Object.fromEntries(
      selectedSuggestions
        .filter(reliableParent)
        .map((item) => [item.tier_id, item.parent_ref])
    ),
    tier_linguistic_types: Object.fromEntries(
      selectedSuggestions
        .filter(reliableType)
        .map((item) => [item.tier_id, item.linguistic_type_ref])
    ),
    required_controlled_vocabularies: props.suggestion.vocabulary_suggestions
      .filter((item) => selectedVocabularies.value.has(item.vocabulary_id))
      .map((item) => item.vocabulary_id),
    media_required:
      props.suggestion.analyzed_files > 0 &&
      props.suggestion.files_with_media === props.suggestion.analyzed_files,
    allowed_media_mime_types: Object.keys(props.suggestion.media_type_counts),
  });
};
</script>

<style scoped>
.suggestion-panel {
  display: grid;
  gap: 1rem;
  padding: 1.15rem;
  border: 1px solid #93c5fd;
  border-radius: 0.9rem;
  background: linear-gradient(145deg, #f8fbff, #fff);
  box-shadow: 0 0.5rem 1.5rem rgb(37 99 235 / 7%);
}

.suggestion-panel > header,
.suggestion-panel > footer,
.suggestion-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

h4,
p {
  margin: 0;
}

h4 {
  margin-top: 0.2rem;
  font-size: 1.1rem;
}

header p,
footer p,
.empty-analysis p {
  margin-top: 0.2rem;
  color: #64748b;
  font-size: 0.86rem;
}

.eyebrow {
  color: #2563eb;
  font-size: 0.7rem;
  font-weight: 850;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

button {
  border: 0;
  border-radius: 0.6rem;
  padding: 0.65rem 0.85rem;
  background: #2563eb;
  color: #fff;
  font: inherit;
  font-size: 0.84rem;
  font-weight: 750;
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.close-button {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #334155;
}

.analysis-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.65rem;
}

.analysis-summary div {
  display: grid;
  gap: 0.15rem;
  padding: 0.8rem;
  border-radius: 0.7rem;
  background: #eff6ff;
}

.analysis-summary strong {
  color: #1d4ed8;
  font-size: 1.25rem;
}

.analysis-summary span {
  color: #64748b;
  font-size: 0.75rem;
}

.analysis-warning {
  padding: 0.7rem 0.8rem;
  border: 1px solid #fde68a;
  border-radius: 0.65rem;
  background: #fffbeb;
  color: #92400e;
  font-size: 0.84rem;
}

.analysis-note {
  padding: 0.75rem 0.85rem;
  border: 1px solid #bfdbfe;
  border-radius: 0.65rem;
  background: #eff6ff;
  color: #334155;
  font-size: 0.84rem;
  line-height: 1.45;
}

.analysis-note strong {
  color: #1e3a8a;
}

.suggestion-tools {
  justify-content: flex-start;
}

.title-line,
.metric-label,
.evidence-guide,
.evidence-guide > span {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.metric-label {
  justify-content: space-between;
}

.evidence-guide {
  flex-wrap: wrap;
  gap: 0.55rem 1rem;
  color: #64748b;
  font-size: 0.75rem;
  font-weight: 700;
}

.suggestion-tools label {
  display: grid;
  gap: 0.25rem;
  color: #475569;
  font-size: 0.74rem;
  font-weight: 750;
}

.search-control {
  flex: 1;
  max-width: 30rem;
}

input,
select {
  border: 1px solid #cbd5e1;
  border-radius: 0.55rem;
  padding: 0.6rem 0.7rem;
  background: #fff;
  color: #14213d;
  font: inherit;
}

.candidate-list {
  display: grid;
  gap: 0.45rem;
  max-height: 28rem;
  overflow: auto;
}

.candidate {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border: 1px solid #dbe3ef;
  border-radius: 0.7rem;
  background: #fff;
  cursor: pointer;
}

.candidate:hover {
  border-color: #93c5fd;
  background: #f8fbff;
}

.candidate-copy {
  display: grid;
  gap: 0.1rem;
  min-width: 0;
}

.candidate-copy strong {
  overflow-wrap: anywhere;
}

.candidate-copy small {
  color: #64748b;
  font-size: 0.75rem;
}

.confidence {
  border-radius: 999px;
  padding: 0.25rem 0.5rem;
  font-size: 0.7rem;
  font-weight: 800;
  white-space: nowrap;
}

.confidence.strong {
  background: #dcfce7;
  color: #166534;
}

.confidence.recurring {
  background: #fef3c7;
  color: #92400e;
}

.confidence.limited {
  background: #f1f5f9;
  color: #64748b;
}

.extras {
  border: 1px solid #dbe3ef;
  border-radius: 0.7rem;
  background: #fff;
}

.extras summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem;
  font-weight: 750;
  cursor: pointer;
}

.extras summary small {
  color: #64748b;
  font-size: 0.75rem;
  font-weight: 600;
}

.extra-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr));
  gap: 0.5rem;
  padding: 0 0.75rem 0.75rem;
}

.extra-options label {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: start;
  gap: 0.55rem;
  min-width: 0;
  padding: 0.65rem 0.7rem;
  border: 1px solid #e2e8f0;
  border-radius: 0.6rem;
  background: #f8fafc;
}

.extra-options label > span {
  display: grid;
  min-width: 0;
}

.extra-options strong {
  overflow-wrap: anywhere;
  line-height: 1.25;
}

.extra-options small {
  color: #64748b;
}

.no-results,
.empty-analysis {
  padding: 1rem;
  color: #64748b;
  text-align: center;
}

.suggestion-panel > footer {
  padding-top: 0.9rem;
  border-top: 1px solid #dbe3ef;
}

@media (width <= 700px) {
  .suggestion-panel > header,
  .suggestion-panel > footer,
  .suggestion-tools {
    align-items: stretch;
    flex-direction: column;
  }

  .analysis-summary {
    grid-template-columns: repeat(2, 1fr);
  }

  .candidate {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .confidence {
    grid-column: 2;
    justify-self: start;
  }
}
</style>
