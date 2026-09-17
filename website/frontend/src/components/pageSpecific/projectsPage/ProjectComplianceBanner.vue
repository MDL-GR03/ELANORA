<template>
  <div class="project-page-files-info-banner" :class="state.banner">
    <font-awesome-icon
      :icon="state.icon"
      :class="['info-banner-icon', state.iconClass]"
    />
    <span class="info-banner-text">
      <template v-if="!hasStandard">
        {{ t('projectsPage.infoBanner.noEffectiveStandard1') }}
        <button class="info-banner-link" @click="emit('configure')">
          {{ t('projectsPage.infoBanner.noEffectiveStandard2') }}
        </button>
        {{ t('projectsPage.infoBanner.noEffectiveStandard3') }}
      </template>
      <template v-else-if="nonCompliantCount > 0">
        {{
          t('projectsPage.infoBanner.nonCompliant', {
            count: nonCompliantCount,
          })
        }}
        <button
          class="info-banner-bulk-rename-link"
          @click="emit('bulk-rename')"
        >
          {{ t('projectsPage.infoBanner.bulkRename') }}
        </button>
      </template>
      <template v-else>
        {{ t('projectsPage.infoBanner.allCompliant') }}
      </template>
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

const props = defineProps({
  hasStandard: { type: Boolean, default: false },
  nonCompliantCount: { type: Number, default: 0 },
});
const emit = defineEmits(['configure', 'bulk-rename']);

const { t } = useI18n();
const state = computed(() => {
  if (!props.hasStandard) {
    return {
      banner: 'info-banner-no-standard',
      icon: 'fa-solid fa-circle-info',
      iconClass: 'icon-no-standard',
    };
  }
  return props.nonCompliantCount > 0
    ? {
        banner: 'info-banner-noncompliant',
        icon: 'fa-solid fa-square-xmark',
        iconClass: 'icon-noncompliant',
      }
    : {
        banner: 'info-banner-compliant',
        icon: 'fa-solid fa-square-check',
        iconClass: 'icon-compliant',
      };
});
</script>
