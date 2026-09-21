<template>
  <div class="member-card">
    <div class="member-info">
      <div class="member-avatar">
        {{ member.username.charAt(0).toUpperCase() }}
      </div>
      <div class="member-details">
        <div class="member-name">{{ member.username }}</div>
        <div class="member-email">{{ member.email }}</div>
      </div>
    </div>

    <div class="member-permission">
      <template v-if="canManage">
        <div class="member-permission-row">
          <div class="permission-selector">
            <AppSelect
              :id="`member-permission-${member.user_id}`"
              :model-value="member.permission"
              :disabled="busy"
              class="permission-select-control"
              size="small"
              :options="permissionOptions"
              @change="emit('change-permission', $event)"
            />
            <div v-if="busy" class="update-spinner">
              <div class="spinner-small"></div>
            </div>
          </div>
          <button
            type="button"
            class="btn-remove"
            :disabled="busy || removing"
            @click="emit('remove')"
          >
            <font-awesome-icon icon="trash" />
            <span>{{ t('common.remove') }}</span>
          </button>
        </div>
        <label
          class="capability-toggle"
          :title="t('project.users.protocol_manager_help')"
        >
          <input
            type="checkbox"
            :checked="isProtocolManager(member)"
            :disabled="busy"
            @change="emit('toggle-protocol-manager', $event)"
          />
          {{ t('project.users.protocol_manager') }}
        </label>
      </template>
      <span v-else class="permission-badge" :class="member.permission">
        {{ t(`projectSettings.permissions.${member.permission}`) }}
      </span>
    </div>

    <div v-if="!canManage" class="member-actions">
      <div class="no-actions">
        <span v-if="member.permission === 'owner'" class="owner-badge">
          {{ t('projectSettings.permissions.owner') }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import AppSelect from '@/components/common/AppSelect.vue';
import { isProtocolManager } from '@/composables/useProjectMembers';

const props = defineProps({
  member: { type: Object, required: true },
  canManage: { type: Boolean, default: false },
  permissions: { type: Array, default: () => [] },
  busy: { type: Boolean, default: false },
  removing: { type: Boolean, default: false },
});
const emit = defineEmits([
  'change-permission',
  'toggle-protocol-manager',
  'remove',
]);

const { t } = useI18n();
const permissionOptions = computed(() =>
  props.permissions.map((permission) => ({
    value: permission,
    label: t(`projectSettings.permissions.${permission}`),
  }))
);
</script>

<style scoped>
.member-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(12rem, 18rem) auto;
  align-items: center;
  gap: 1rem;
  background: var(--secondary-bg);
  border: 1px solid var(--color-border-subtle);
  border-radius: 12px;
  padding: 1rem;
  transition: all 0.2s ease;
}

.capability-toggle {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.5rem;
  color: var(--color-text-muted);
  font-size: 0.8rem;
  cursor: pointer;
}

.member-card:hover {
  background: var(--color-gray-500-alt);
  border-color: var(--color-gray-300);
}

.member-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.member-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(
    135deg,
    var(--color-indigo-500),
    var(--color-purple-500-alt)
  );
  color: var(--color-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.875rem;
}

.member-details {
  flex: 1;
  min-width: 0;
}

.member-name {
  font-weight: 500;
  color: var(--color-gray-900);
  margin-bottom: 0.125rem;
}

.member-email {
  font-size: 0.875rem;
  color: var(--color-gray-500);
  overflow-wrap: anywhere;
}

.member-permission-row {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.permission-selector {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  width: min(17rem, 100%);
}

.permission-select-control {
  min-width: 8rem;
}

.update-spinner {
  display: flex;
  align-items: center;
}

.spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid var(--color-border-subtle);
  border-top: 2px solid var(--color-indigo-500);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }

  100% {
    transform: rotate(360deg);
  }
}

.permission-badge {
  display: inline-block;
  padding: 0.375rem 0.75rem;
  border-radius: 16px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: capitalize;
}

.permission-badge.read {
  background: var(--color-info-bg);
  color: var(--color-info-dark);
}

.permission-badge.write {
  background: var(--color-success-bg-subtle);
  color: var(--color-success-dark);
}

.permission-badge.admin {
  background: var(--color-warning-bg);
  color: var(--color-warning-dark);
}

.permission-badge.owner {
  background: var(--color-purple-100);
  color: var(--color-purple-700-alt);
}

.btn-remove {
  min-height: 2.35rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.45rem 0.7rem;
  border: 1px solid var(--color-red-200-alt);
  border-radius: 0.5rem;
  background: var(--color-surface);
  color: var(--color-error-light);
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 700;
  transition: all 0.2s ease;
}

.btn-remove:hover:not(:disabled) {
  background: var(--color-error-bg-subtle);
  transform: scale(1.1);
}

@media (width <= 760px) {
  .member-card {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .member-permission-row {
    align-items: stretch;
  }

  .permission-selector {
    width: auto;
    flex: 1;
    min-width: 0;
  }

  .member-actions {
    justify-self: start;
  }
}

@media (width <= 460px) {
  .member-permission-row {
    flex-direction: column;
  }

  .btn-remove {
    width: 100%;
  }
}

.btn-remove:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.no-actions {
  width: 32px;
  text-align: center;
}

.owner-badge {
  font-size: 0.75rem;
  color: var(--color-purple-700-alt);
  font-weight: 500;
}

/* Modal Styles */
</style>
