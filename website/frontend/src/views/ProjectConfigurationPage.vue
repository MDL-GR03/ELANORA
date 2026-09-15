<template>
  <div>
    <div class="project-standards-page">
      <WorkspaceHeader
        :context="projectName"
        :title="t('projectSettings.pageTitle')"
        :description="t('projectSettings.subtitle')"
      />

      <div
        v-if="activeSection"
        class="settings-workspace"
        :class="{ 'navigation-collapsed': navigationCollapsed }"
      >
        <aside class="settings-navigation" aria-label="Project settings">
          <div class="settings-navigation-intro">
            <div class="settings-navigation-intro-top">
              <span class="eyebrow">Project settings</span>
              <button
                type="button"
                class="settings-navigation-toggle"
                :aria-label="
                  navigationCollapsed
                    ? 'Expand settings navigation'
                    : 'Collapse settings navigation'
                "
                :title="
                  navigationCollapsed
                    ? 'Expand navigation'
                    : 'Collapse navigation'
                "
                @click="toggleNavigation"
              >
                <font-awesome-icon
                  :icon="
                    navigationCollapsed
                      ? 'fa-solid fa-angles-right'
                      : 'fa-solid fa-angles-left'
                  "
                />
              </button>
            </div>
            <div class="settings-navigation-intro-copy">
              <h2>Configure your workspace</h2>
              <p>Choose an area to manage without losing your place.</p>
            </div>
          </div>

          <nav>
            <section v-for="group in sectionGroups" :key="group.key">
              <h3>{{ t(group.titleKey) }}</h3>
              <button
                v-for="section in group.sections"
                :key="section.key"
                type="button"
                :class="{ active: activeSection.key === section.key }"
                :aria-current="
                  activeSection.key === section.key ? 'page' : undefined
                "
                :title="navigationCollapsed ? t(section.titleKey) : undefined"
                @click="selectSection(section.key)"
              >
                <span class="settings-navigation-icon">
                  <font-awesome-icon :icon="section.icon" />
                </span>
                <span>
                  <strong>{{ t(section.titleKey) }}</strong>
                  <small>{{ section.description }}</small>
                </span>
                <font-awesome-icon
                  class="settings-navigation-chevron"
                  icon="fa-solid fa-chevron-right"
                />
              </button>
            </section>
          </nav>
        </aside>

        <main class="settings-content-panel">
          <header class="settings-content-header">
            <span class="settings-content-icon">
              <font-awesome-icon :icon="activeSection.icon" />
            </span>
            <div>
              <span class="eyebrow">{{ activeGroupTitle }}</span>
              <h2>{{ t(activeSection.titleKey) }}</h2>
              <p>{{ activeSection.description }}</p>
            </div>
          </header>
          <div class="settings-section-body">
            <KeepAlive>
              <component
                :is="activeSection.component"
                :key="activeSection.key"
              />
            </KeepAlive>
          </div>
        </main>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, defineAsyncComponent, watch } from 'vue';
import { useProjectStore } from '@stores/project.js';
import { useUserStore } from '@stores/user.js';
import {
  hasProjectCapability,
  hasProjectPermission,
} from '@/utils/authorization';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';

import '@/assets/css/ProjectConfigurationPage.css';
import WorkspaceHeader from '@/components/layout/WorkspaceHeader.vue';

const ConfigureNamingStandards = defineAsyncComponent(
  () =>
    import(
      '@components/pageSpecific/projectConfiguration/ConfigureNamingStandards.vue'
    )
);
const ConfigureFileTypes = defineAsyncComponent(
  () =>
    import(
      '@components/pageSpecific/projectConfiguration/ConfigureFileTypes.vue'
    )
);
const ConfigureProjectMembers = defineAsyncComponent(
  () =>
    import(
      '@components/pageSpecific/projectConfiguration/ConfigureProjectMembers.vue'
    )
);
const ConfigurePendingInvitations = defineAsyncComponent(
  () =>
    import(
      '@components/pageSpecific/projectConfiguration/ConfigurePendingInvitations.vue'
    )
);
const ConfigureEffectiveStandards = defineAsyncComponent(
  () =>
    import(
      '@components/pageSpecific/projectConfiguration/ConfigureEffectiveStandards.vue'
    )
);
const ConfigureProtocols = defineAsyncComponent(
  () =>
    import(
      '@components/pageSpecific/projectConfiguration/ConfigureProtocols.vue'
    )
);
const ConfigureDataGovernance = defineAsyncComponent(
  () =>
    import(
      '@components/pageSpecific/projectConfiguration/ConfigureDataGovernance.vue'
    )
);
const ConfigureContributionAutomation = defineAsyncComponent(
  () =>
    import(
      '@components/pageSpecific/projectConfiguration/ConfigureContributionAutomation.vue'
    )
);

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const projectStore = useProjectStore();
const userStore = useUserStore();
const projectId = computed(() => Number(route.params.projectId));
const navigationCollapsed = ref(false);
const projectName = computed(() => {
  const project = projectStore.projects.find(
    (p) => p.project_id === projectId.value
  );
  return project ? project.project_name : '';
});

const allSectionGroups = [
  {
    key: 'technical',
    titleKey: 'projectSettings.sectionNames.sections.technical',
    sections: [
      {
        key: 'protocols',
        titleKey: 'projectSettings.sectionNames.sections.subsections.protocols',
        component: ConfigureProtocols,
        icon: 'fa-solid fa-file-code',
        description:
          'Define and validate the linguistic structure expected across ELAN files.',
      },
      {
        key: 'filetypes',
        titleKey: 'projectSettings.sectionNames.sections.subsections.fileTypes',
        component: ConfigureFileTypes,
        icon: 'fa-solid fa-file',
        description:
          'Manage the kinds of research files accepted by this project.',
      },
      {
        key: 'naming',
        titleKey:
          'projectSettings.sectionNames.sections.subsections.namingStandards',
        component: ConfigureNamingStandards,
        icon: 'fa-solid fa-tag',
        description:
          'Create readable filename conventions for consistent corpus organization.',
      },
      {
        key: 'effectiveStandards',
        titleKey:
          'projectSettings.sectionNames.sections.subsections.effectiveStandards',
        component: ConfigureEffectiveStandards,
        icon: 'fa-solid fa-gears',
        description:
          'Choose which naming convention applies to each file type and location.',
      },
    ],
  },
  {
    key: 'workflow',
    titleKey: 'projectSettings.sectionNames.sections.workflow',
    sections: [
      {
        key: 'contributionAutomation',
        titleKey:
          'projectSettings.sectionNames.sections.subsections.contributionAutomation',
        component: ConfigureContributionAutomation,
        icon: 'fa-solid fa-code-merge',
        description:
          'Control when safe new-file contributions may be merged without manual review.',
      },
    ],
  },
  {
    key: 'governance',
    titleKey: 'dataGovernance.group',
    sections: [
      {
        key: 'dataGovernance',
        titleKey: 'dataGovernance.section',
        component: ConfigureDataGovernance,
        icon: 'fa-solid fa-shield-halved',
        description: t('dataGovernance.sectionDescription'),
      },
    ],
  },
  {
    key: 'collaborators',
    titleKey: 'projectSettings.sectionNames.sections.collaborators',
    sections: [
      {
        key: 'members',
        titleKey: 'projectSettings.sectionNames.sections.subsections.members',
        component: ConfigureProjectMembers,
        icon: 'fa-solid fa-circle-user',
        description:
          'Manage collaborators, access levels, and delegated responsibilities.',
      },
      {
        key: 'invitations',
        titleKey:
          'projectSettings.sectionNames.sections.subsections.invitations',
        component: ConfigurePendingInvitations,
        icon: 'fa-solid fa-inbox',
        description:
          'Invite researchers and follow invitations that are awaiting a response.',
      },
    ],
  },
];

const sectionGroups = computed(() => {
  if (userStore.user?.role === 'admin') return allSectionGroups;
  const groups = [];
  const project = projectStore.projects.find(
    (item) => item.project_id === projectId.value
  );
  if (hasProjectCapability(userStore.user, project, 'manage_protocols')) {
    groups.push({
      key: 'technical',
      titleKey: 'projectSettings.sectionNames.sections.technical',
      sections: allSectionGroups
        .find((group) => group.key === 'technical')
        .sections.filter((section) => section.key === 'protocols'),
    });
  }
  if (hasProjectPermission(userStore.user, project, 'admin')) {
    groups.push(allSectionGroups.find((group) => group.key === 'workflow'));
    groups.push(allSectionGroups.find((group) => group.key === 'governance'));
    groups.push({
      key: 'collaborators',
      titleKey: 'projectSettings.sectionNames.sections.collaborators',
      sections: allSectionGroups
        .find((group) => group.key === 'collaborators')
        .sections.filter((section) => section.key === 'members'),
    });
  }
  return groups;
});

const availableSections = computed(() =>
  sectionGroups.value.flatMap((group) =>
    group.sections.map((section) => ({ ...section, group }))
  )
);
const selectedSectionKey = ref(String(route.query.setting || ''));
const activeSection = computed(
  () =>
    availableSections.value.find(
      (section) => section.key === selectedSectionKey.value
    ) || availableSections.value[0]
);
const activeGroupTitle = computed(() =>
  activeSection.value ? t(activeSection.value.group.titleKey) : ''
);

function selectSection(key) {
  selectedSectionKey.value = key;
  void router.replace({ query: { ...route.query, setting: key } });
}

function toggleNavigation() {
  navigationCollapsed.value = !navigationCollapsed.value;
  window.localStorage.setItem(
    'elanora-project-settings-navigation-collapsed',
    String(navigationCollapsed.value)
  );
}

watch(
  () => route.query.setting,
  (setting) => {
    if (setting) selectedSectionKey.value = String(setting);
  }
);

onMounted(() => {
  projectStore.initBroadcastChannel();
  navigationCollapsed.value =
    window.localStorage.getItem(
      'elanora-project-settings-navigation-collapsed'
    ) === 'true';
});
</script>
