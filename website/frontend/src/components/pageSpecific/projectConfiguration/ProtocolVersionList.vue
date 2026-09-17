<template>
  <div class="protocol-list">
    <div v-if="archivedCount" class="archive-toolbar">
      <span>
        {{
          showArchived
            ? t('protocols.archived_shown', archivedCount)
            : t('protocols.archived_hidden', archivedCount)
        }}
      </span>
      <button
        class="text-button"
        type="button"
        @click="showArchived = !showArchived"
      >
        {{
          showArchived
            ? t('protocols.hide_archived')
            : t('protocols.show_archived')
        }}
      </button>
    </div>
    <article
      v-for="protocol in visibleProtocols"
      :key="protocol.protocol_id"
      class="protocol-card"
    >
      <div class="protocol-title">
        <span class="eyebrow">{{ t('protocols.protocol') }}</span>
        <h4>{{ protocol.name }}</h4>
        <p>{{ protocol.description || t('protocols.no_description') }}</p>
      </div>
      <div
        v-for="version in protocol.versions"
        :key="version.protocol_version_id"
        :class="['version-row', { archived: version.archived_at }]"
      >
        <div class="version-info">
          <span>
            <strong>{{
              t('protocols.version', { number: version.version_number })
            }}</strong>
            <i :class="['status', stateOf(version)]">{{
              t(`protocols.status.${stateOf(version)}`)
            }}</i>
          </span>
          <small>{{ summarizeRules(version.rules) }}</small>
          <small v-if="version.archive_reason">{{
            t('protocols.archive_reason', { reason: version.archive_reason })
          }}</small>
          <small v-if="version.archived_at" class="archived-copy">
            {{ t('protocols.withdrawn') }}
          </small>
        </div>
        <div class="row-actions">
          <template v-if="version.status === 'draft'">
            <button
              class="secondary"
              type="button"
              @click="emit('edit-draft', protocol, version)"
            >
              {{ t('protocols.edit_draft') }}
            </button>
            <button type="button" @click="emit('publish', protocol, version)">
              {{ t('protocols.publish') }}
            </button>
            <button
              class="danger"
              type="button"
              @click="emit('remove-draft', protocol, version)"
            >
              {{ t('protocols.delete_draft') }}
            </button>
          </template>
          <template v-else>
            <button
              class="secondary"
              type="button"
              @click="emit('create-version', protocol, version)"
            >
              {{ t('protocols.new_draft_from_version') }}
            </button>
            <template v-if="version.archived_at">
              <button
                class="danger"
                type="button"
                @click="emit('purge', protocol, version)"
              >
                {{ t('protocols.delete_permanently') }}
              </button>
            </template>
            <template v-else>
              <button
                class="secondary"
                type="button"
                :disabled="scanning"
                @click="emit('scan', protocol, version)"
              >
                {{ t('protocols.preview_impact') }}
              </button>
              <button type="button" @click="emit('pin', protocol, version)">
                {{ t('protocols.use_for_project') }}
              </button>
              <button
                class="danger"
                type="button"
                @click="emit('archive', protocol, version)"
              >
                {{ t('protocols.archive') }}
              </button>
            </template>
          </template>
        </div>
      </div>
    </article>
    <div v-if="!loading && !protocols.length" class="empty-state">
      <strong>{{ t('protocols.empty.title') }}</strong>
      <p>{{ t('protocols.empty.description') }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { countRules } from '@/utils/protocolRules';

const props = defineProps({
  protocols: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  scanning: { type: Boolean, default: false },
});
const emit = defineEmits([
  'edit-draft',
  'publish',
  'remove-draft',
  'create-version',
  'scan',
  'purge',
  'pin',
  'archive',
]);

const { t } = useI18n();
const showArchived = ref(false);

const archivedCount = computed(() =>
  props.protocols.reduce(
    (total, protocol) =>
      total + protocol.versions.filter((version) => version.archived_at).length,
    0
  )
);
const visibleProtocols = computed(() =>
  props.protocols
    .map((protocol) => ({
      ...protocol,
      versions: showArchived.value
        ? protocol.versions
        : protocol.versions.filter((version) => !version.archived_at),
    }))
    .filter((protocol) => protocol.versions.length)
);

function stateOf(version) {
  return version.archived_at ? 'archived' : version.status;
}

function summarizeRules(rules) {
  const summary = t('protocols.rule_count', countRules(rules));
  const warnings = Object.keys(rules.severities || {}).length;
  return warnings
    ? `${summary}, ${t('protocols.warning_count', warnings)}`
    : summary;
}
</script>

<style scoped src="@/assets/css/protocol-workspace.css"></style>

<style scoped>
.protocol-list {
  display: grid;
  gap: 0.8rem;
}

.archive-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.35rem;
  min-height: 2rem;
  color: #64748b;
  font-size: 0.85rem;
}

.archived-copy {
  max-width: 42rem;
  margin-top: 0.2rem;
  color: #475569;
  font-size: 0.82rem;
  line-height: 1.4;
}

.protocol-card {
  border: 1px solid #dbe3ef;
  border-radius: 0.9rem;
  background: #fff;
  overflow: hidden;
}

.protocol-title {
  padding: 1rem 1.1rem;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.version-row {
  display: grid;
  grid-template-columns: minmax(16rem, 1fr) auto;
  align-items: center;
  padding: 0.9rem 1.1rem;
  border-bottom: 1px solid #edf2f7;
}

.version-row.archived {
  background: #fafbfc;
  box-shadow: inset 3px 0 #cbd5e1;
}

.version-row:last-child {
  border-bottom: 0;
}

.version-info {
  display: grid;
  gap: 0.25rem;
}

.version-info > span {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

@media (width <= 760px) {
  .version-row {
    display: flex;
  }

  .row-actions button {
    flex: 1;
  }
}
</style>
