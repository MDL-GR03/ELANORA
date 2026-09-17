<template>
  <section
    class="project-selected-overview"
    :aria-labelledby="`selected-project-${project.project_id}`"
  >
    <div class="project-selected-overview-icon" aria-hidden="true">
      <font-awesome-icon icon="fa-diagram-project" />
    </div>
    <div class="project-selected-overview-content">
      <span class="project-selected-overview-context">
        {{ t('projectsPage.selectedProject') }}
      </span>
      <h2 :id="`selected-project-${project.project_id}`">
        {{ project.project_name }}
      </h2>
      <p
        class="project-selected-description"
        :class="{
          'project-selected-description--collapsed': isLong && !expanded,
        }"
      >
        {{ description || t('projectsPage.noDescription') }}
      </p>
      <button
        v-if="isLong"
        type="button"
        class="project-description-toggle"
        :aria-expanded="expanded"
        @click="expanded = !expanded"
      >
        {{
          expanded
            ? t('projectsPage.showLessDescription')
            : t('projectsPage.readFullDescription')
        }}
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

const LONG_DESCRIPTION = 180;

/** Keyed by project in the page, so the description starts collapsed. */
const props = defineProps({
  project: { type: Object, required: true },
});

const { t } = useI18n();
const expanded = ref(false);
const description = computed(
  () => props.project.project_description?.trim() || ''
);
const isLong = computed(() => description.value.length > LONG_DESCRIPTION);
</script>
