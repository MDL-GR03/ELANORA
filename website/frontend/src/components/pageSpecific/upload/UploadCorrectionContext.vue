<template>
  <section class="correction-context" role="status">
    <div class="correction-context-icon">
      <font-awesome-icon icon="fa-solid fa-rotate" />
    </div>
    <div>
      <span>{{ t('uploadPage.correction.title') }}</span>
      <strong>{{ correctionCase.title }}</strong>
      <p>{{ t('uploadPage.correction.description') }}</p>
      <ul v-if="tasks.length" class="correction-file-list">
        <li v-for="task in tasks" :key="task.task_id">
          <font-awesome-icon icon="fa-solid fa-file-circle-exclamation" />
          <span>
            <strong>{{ task.filename }}</strong>
            <small>{{ task.instruction }}</small>
          </span>
        </li>
      </ul>
    </div>
    <router-link
      :to="{
        name: 'PendingUpload',
        query: {
          project: projectId,
          view: 'reviews',
          case: correctionCase.case_id,
        },
      }"
      >{{ t('uploadPage.correction.viewDiscussion') }}</router-link
    >
  </section>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import { activeCorrectionTasks } from '@/utils/correctionFiles';

const props = defineProps({
  correctionCase: { type: Object, required: true },
  projectId: { type: [Number, String], required: true },
});

const { t } = useI18n();
const tasks = computed(() => activeCorrectionTasks(props.correctionCase));
</script>
