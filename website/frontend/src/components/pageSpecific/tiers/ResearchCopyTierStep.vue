<template>
  <section class="research-step research-step--tiers">
    <div class="research-step__heading">
      <ResearchStepTitle
        number="3"
        :title="t('researchScopes.prepare.tierStepTitle')"
        :text="t('researchScopes.prepare.tierStepText')"
      />
      <div class="tier-export-selection__shortcuts">
        <button type="button" @click="selectAllTiers">
          {{ t('researchScopes.selectAll') }}
        </button>
        <button type="button" @click="clearSelectedTiers">
          {{ t('researchScopes.clear') }}
        </button>
      </div>
    </div>
    <section v-if="availableBaselineTiers.length" class="copy-baseline-options">
      <header>
        <font-awesome-icon icon="fa-solid fa-shield-halved" />
        <div>
          <strong>{{ t('researchScopes.baseline.copyTitle') }}</strong>
          <span>{{ t('researchScopes.baseline.copyText') }}</span>
        </div>
        <button type="button" @click="toggleAllBaselineContext">
          {{
            allBaselineIncluded
              ? t('researchScopes.baseline.removeAll')
              : t('researchScopes.baseline.includeAll')
          }}
        </button>
      </header>
      <div class="copy-baseline-list">
        <div v-for="name in availableBaselineTiers" :key="name">
          <label>
            <input
              type="checkbox"
              :checked="includedBaselineNames.has(name)"
              @change="toggleIncludedBaseline(name)"
            />
            <span>{{ name }}</span>
          </label>
          <label class="baseline-correction-choice">
            <input
              type="checkbox"
              :checked="editableBaselineNames.has(name)"
              @change="toggleEditableBaseline(name)"
            />
            {{ t('researchScopes.baseline.proposeCorrection') }}
          </label>
        </div>
      </div>
      <p v-if="editableBaselineNames.size" class="baseline-edit-warning">
        <font-awesome-icon icon="fa-solid fa-circle-info" />
        {{ t('researchScopes.baseline.correctionWarning') }}
      </p>
    </section>
    <div class="tier-export-tree-panel">
      <TierSelectionTree
        v-if="selectedGroup"
        root
        :tiers="selectedGroup.tiers"
        :selected-names="selectedTierNames"
        :automatic-names="automaticParents"
        :context-names="protectedBaselineNames"
        :correction-names="editableBaselineNames"
        @toggle="toggleTier"
      />
    </div>
    <footer class="tier-export-footer">
      <div>
        <strong>{{
          t('researchScopes.selectedResearchTiers', {
            count: selectedTierNames.size,
          })
        }}</strong>
        <span>{{
          selectedTopic
            ? t('researchScopes.usingTopic', { topic: selectedTopic.name })
            : t('researchScopes.customWorkingScope')
        }}</span>
      </div>
      <button
        type="button"
        class="tiers-primary-button"
        :disabled="!canDownload || pending"
        @click="emit('download')"
      >
        <font-awesome-icon icon="fa-solid fa-download" />{{
          pending ? t('researchScopes.preparing') : t('researchScopes.download')
        }}
      </button>
    </footer>
  </section>
</template>

<script setup>
import { useI18n } from 'vue-i18n';

import ResearchStepTitle from './ResearchStepTitle.vue';
import TierSelectionTree from './TierSelectionTree.vue';
import { useResearchCopyContext } from './researchCopyContext';

defineProps({ pending: { type: Boolean, default: false } });
const emit = defineEmits(['download']);

const { t } = useI18n();
const {
  selectedGroup,
  selectedTopic,
  selectedTierNames,
  includedBaselineNames,
  editableBaselineNames,
  protectedBaselineNames,
  availableBaselineTiers,
  allBaselineIncluded,
  automaticParents,
  canDownload,
  toggleTier,
  selectAllTiers,
  clearSelectedTiers,
  toggleIncludedBaseline,
  toggleEditableBaseline,
  toggleAllBaselineContext,
} = useResearchCopyContext();
</script>
