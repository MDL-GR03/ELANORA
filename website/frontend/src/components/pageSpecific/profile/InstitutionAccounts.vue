<template>
  <section class="accounts-panel">
    <div class="accounts-toolbar">
      <label>
        <span>{{ t('profile.accounts.search') }}</span>
        <input
          v-model.trim="query"
          type="search"
          :placeholder="t('profile.accounts.search_placeholder')"
        />
      </label>
      <span class="account-count">{{ filteredAccounts.length }}</span>
    </div>

    <p v-if="loading" class="state-message">
      {{ t('profile.accounts.loading') }}
    </p>
    <p v-else-if="error" class="state-message error" role="alert">
      {{ error }}
    </p>
    <p v-else-if="!filteredAccounts.length" class="state-message">
      {{ t('profile.accounts.empty') }}
    </p>

    <div v-else class="account-list">
      <article
        v-for="account in filteredAccounts"
        :key="account.user_id"
        class="account-row"
      >
        <div class="account-avatar" aria-hidden="true">
          {{ account.first_name?.[0] }}{{ account.last_name?.[0] }}
        </div>
        <div class="account-identity">
          <strong>{{ account.first_name }} {{ account.last_name }}</strong>
          <span>@{{ account.username }} · {{ account.email }}</span>
        </div>
        <span class="role-badge">{{
          t(`profile.accounts.roles.${account.role}`)
        }}</span>
        <span
          class="status-badge"
          :class="account.is_active ? 'active' : 'suspended'"
        >
          <FontAwesomeIcon
            :icon="account.is_active ? faCircleCheck : faCirclePause"
          />
          {{
            t(
              account.is_active
                ? 'profile.accounts.active'
                : 'profile.accounts.suspended'
            )
          }}
        </span>
        <span v-if="account.user_id === currentUserId" class="current-user">
          {{ t('profile.accounts.you') }}
        </span>
        <button
          v-else
          type="button"
          class="status-action"
          :class="{ restore: !account.is_active }"
          @click="beginStatusChange(account)"
        >
          <FontAwesomeIcon
            :icon="account.is_active ? faUserLock : faUserCheck"
          />
          {{
            t(
              account.is_active
                ? 'profile.accounts.suspend'
                : 'profile.accounts.restore'
            )
          }}
        </button>
      </article>
    </div>

    <div
      v-if="selectedAccount"
      class="dialog-backdrop"
      @mousedown.self="closeDialog"
    >
      <form
        class="status-dialog"
        role="dialog"
        aria-modal="true"
        @submit.prevent="saveStatus"
      >
        <div
          class="dialog-icon"
          :class="{ restore: !selectedAccount.is_active }"
        >
          <FontAwesomeIcon
            :icon="selectedAccount.is_active ? faUserLock : faUserCheck"
          />
        </div>
        <div>
          <p class="dialog-eyebrow">{{ t('profile.accounts.confirmation') }}</p>
          <h2>
            {{
              t(
                selectedAccount.is_active
                  ? 'profile.accounts.suspend_title'
                  : 'profile.accounts.restore_title',
                { name: selectedAccount.username }
              )
            }}
          </h2>
        </div>
        <p>
          {{
            t(
              selectedAccount.is_active
                ? 'profile.accounts.suspend_effect'
                : 'profile.accounts.restore_effect'
            )
          }}
        </p>
        <label>
          {{ t('profile.accounts.reason') }}
          <textarea
            v-model.trim="reason"
            minlength="3"
            maxlength="500"
            required
          ></textarea>
        </label>
        <p v-if="dialogError" class="dialog-error" role="alert">
          {{ dialogError }}
        </p>
        <div class="dialog-actions">
          <button type="button" class="cancel" @click="closeDialog">
            {{ t('profile.accounts.cancel') }}
          </button>
          <button
            type="submit"
            class="confirm"
            :disabled="saving || reason.length < 3"
          >
            {{
              saving
                ? t('profile.accounts.saving')
                : t(
                    selectedAccount.is_active
                      ? 'profile.accounts.suspend'
                      : 'profile.accounts.restore'
                  )
            }}
          </button>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';
import {
  faCircleCheck,
  faCirclePause,
  faUserCheck,
  faUserLock,
} from '@fortawesome/free-solid-svg-icons';
import {
  fetchInstitutionAccounts,
  setInstitutionAccountStatus,
} from '@/api/service/userService';
import { useUserStore } from '@/stores/user';
import { reportClientError } from '@/utils/errorDiagnostics';

const emit = defineEmits(['show-message']);
const { t } = useI18n();
const userStore = useUserStore();
const accounts = ref([]);
const loading = ref(true);
const error = ref('');
const query = ref('');
const selectedAccount = ref(null);
const reason = ref('');
const saving = ref(false);
const dialogError = ref('');
const currentUserId = computed(() => userStore.user?.user_id);
const filteredAccounts = computed(() => {
  const needle = query.value.toLocaleLowerCase();
  if (!needle) return accounts.value;
  return accounts.value.filter((account) =>
    [account.first_name, account.last_name, account.username, account.email]
      .join(' ')
      .toLocaleLowerCase()
      .includes(needle)
  );
});

async function loadAccounts() {
  loading.value = true;
  error.value = '';
  try {
    accounts.value = (await fetchInstitutionAccounts()).data.users || [];
  } catch (requestError) {
    reportClientError('Unable to load institution accounts', requestError);
    error.value = t('profile.accounts.load_error');
  } finally {
    loading.value = false;
  }
}
function beginStatusChange(account) {
  selectedAccount.value = account;
  reason.value = '';
  dialogError.value = '';
}
function closeDialog() {
  if (!saving.value) selectedAccount.value = null;
}
async function saveStatus() {
  if (!selectedAccount.value || reason.value.length < 3) return;
  saving.value = true;
  dialogError.value = '';
  try {
    const nextActive = !selectedAccount.value.is_active;
    const response = await setInstitutionAccountStatus(
      selectedAccount.value.user_id,
      nextActive,
      reason.value
    );
    const index = accounts.value.findIndex(
      (item) => item.user_id === response.data.user_id
    );
    if (index >= 0) accounts.value[index] = response.data;
    selectedAccount.value = null;
    emit('show-message', {
      text: t(
        nextActive
          ? 'profile.accounts.restored_message'
          : 'profile.accounts.suspended_message'
      ),
      type: 'success',
    });
  } catch (requestError) {
    dialogError.value =
      requestError.response?.data?.detail || t('profile.accounts.save_error');
  } finally {
    saving.value = false;
  }
}
onMounted(loadAccounts);
</script>

<style scoped>
.accounts-panel {
  padding: clamp(1rem, 4vw, 2rem);
  display: grid;
  gap: 1rem;
}

.accounts-toolbar {
  display: flex;
  align-items: end;
  gap: 1rem;
}

.accounts-toolbar label {
  flex: 1;
  display: grid;
  gap: 0.4rem;
  font-weight: 700;
  color: #334155;
}

.accounts-toolbar input,
textarea {
  width: 100%;
  min-height: 2.8rem;
  padding: 0.7rem 0.85rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.65rem;
  background: white;
}

.account-count {
  padding: 0.65rem 0.85rem;
  border-radius: 999px;
  color: #1d4ed8;
  background: #eff6ff;
  font-weight: 750;
}

.account-list {
  display: grid;
  border: 1px solid #dbe4f0;
  border-radius: 0.85rem;
  overflow: hidden;
}

.account-row {
  display: grid;
  grid-template-columns: auto minmax(12rem, 1fr) auto auto auto;
  align-items: center;
  gap: 0.85rem;
  padding: 1rem;
  background: white;
}

.account-row + .account-row {
  border-top: 1px solid #e5eaf2;
}

.account-avatar {
  width: 2.7rem;
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #4338ca;
  background: #eef2ff;
  font-weight: 800;
}

.account-identity {
  min-width: 0;
  display: grid;
  gap: 0.2rem;
}

.account-identity span {
  overflow: hidden;
  color: #64748b;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.role-badge,
.status-badge,
.current-user {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.38rem 0.65rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 750;
}

.role-badge {
  color: #475569;
  background: #f1f5f9;
}

.status-badge.active {
  color: #166534;
  background: #ecfdf3;
}

.status-badge.suspended {
  color: #9a3412;
  background: #fff7ed;
}

.current-user {
  color: #1d4ed8;
  background: #eff6ff;
}

.status-action {
  min-height: 2.65rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  padding: 0.6rem 0.85rem;
  border: 1px solid #fecaca;
  border-radius: 0.6rem;
  color: #b91c1c;
  background: #fff;
  font-weight: 750;
}

.status-action.restore {
  border-color: #bbf7d0;
  color: #166534;
}

.dialog-backdrop {
  position: fixed;
  z-index: 10000;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: rgb(15 23 42 / 58%);
  backdrop-filter: blur(3px);
}

.status-dialog {
  width: min(32rem, 100%);
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 1rem;
  padding: 1.5rem;
  border-radius: 1rem;
  background: white;
  box-shadow: 0 24px 70px rgb(15 23 42 / 25%);
}

.dialog-icon {
  width: 3rem;
  height: 3rem;
  display: grid;
  place-items: center;
  border-radius: 0.8rem;
  color: #b91c1c;
  background: #fef2f2;
}

.dialog-icon.restore {
  color: #166534;
  background: #ecfdf3;
}

.dialog-eyebrow {
  margin: 0 0 0.2rem;
  color: #64748b;
  font-size: 0.75rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.status-dialog h2,
.status-dialog p {
  margin: 0;
}

.status-dialog > p,
.status-dialog > label,
.dialog-error,
.dialog-actions {
  grid-column: 1 / -1;
}

.status-dialog label {
  display: grid;
  gap: 0.4rem;
  font-weight: 700;
}

.status-dialog textarea {
  min-height: 6rem;
  resize: vertical;
}

.dialog-error,
.state-message.error {
  color: #b91c1c;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.65rem;
}

.dialog-actions button {
  min-height: 2.75rem;
  padding: 0.65rem 1rem;
  border-radius: 0.65rem;
  font-weight: 750;
}

.dialog-actions .cancel {
  border: 1px solid #cbd5e1;
  background: white;
}

.dialog-actions .confirm {
  border: 0;
  color: white;
  background: #2563eb;
}

.dialog-actions .confirm:disabled {
  opacity: 0.55;
}

@media (width <= 760px) {
  .account-row {
    grid-template-columns: auto 1fr;
  }

  .account-identity {
    grid-column: 2;
  }

  .role-badge,
  .status-badge,
  .current-user,
  .status-action {
    grid-column: 2;
    justify-self: start;
  }

  .status-action {
    width: 100%;
  }
}
</style>
