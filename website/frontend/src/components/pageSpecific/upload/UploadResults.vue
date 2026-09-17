<template>
  <section
    class="upload-results"
    aria-labelledby="upload-results-heading"
    aria-live="polite"
  >
    <div class="upload-results-heading">
      <div>
        <span>{{ t('uploadPage.complete') }}</span>
        <h2 id="upload-results-heading">{{ t('uploadPage.uploadResults') }}</h2>
      </div>
      <strong>{{ successCount }}/{{ results.length }}</strong>
    </div>
    <ul class="results-list">
      <li
        v-for="result in results"
        :key="result.filename"
        class="result-item"
        :class="{ success: result.success, error: !result.success }"
      >
        <font-awesome-icon
          :icon="
            result.success
              ? 'fa-solid fa-circle-check'
              : 'fa-solid fa-circle-xmark'
          "
        />
        <span class="result-filename">{{ result.filename }}</span>
        <span class="result-status">
          {{
            result.success
              ? t('uploadPage.resultSuccess')
              : t('uploadPage.resultFailed')
          }}
        </span>
        <span v-if="result.error" class="result-error">{{ result.error }}</span>
      </li>
    </ul>
    <router-link
      v-if="uploadId && correctionCaseId"
      class="finish-correction-link"
      :to="{
        name: 'PendingUpload',
        query: {
          project: projectId,
          view: 'reviews',
          case: correctionCaseId,
          resubmission: uploadId,
        },
      }"
    >
      {{ t('uploadPage.correction.finishLink') }}
      <font-awesome-icon icon="fa-solid fa-arrow-right" />
    </router-link>
    <router-link
      v-else-if="uploadId"
      class="finish-correction-link"
      :to="{
        name: 'PendingUpload',
        query: {
          project: projectId,
          view: 'queue',
          workspace: 'details',
          upload: uploadId,
        },
      }"
    >
      {{ t('uploadPage.context.viewContribution', { id: uploadId }) }}
      <font-awesome-icon icon="fa-solid fa-arrow-right" />
    </router-link>
  </section>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

const props = defineProps({
  results: { type: Array, required: true },
  projectId: { type: [Number, String], required: true },
  uploadId: { type: [Number, String], default: null },
  correctionCaseId: { type: String, default: null },
});

const { t } = useI18n();
const successCount = computed(
  () => props.results.filter((result) => result.success).length
);
</script>
