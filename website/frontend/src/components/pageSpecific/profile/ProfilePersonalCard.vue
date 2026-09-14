<template>
  <!-- Personal Information Card -->
  <div class="profile-card personal-info-card">
    <div class="profile-card-header">
      <div class="card-title-section">
        <div class="card-icon">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M12 12C14.7614 12 17 9.76142 17 7C17 4.23858 14.7614 2 12 2C9.23858 2 7 4.23858 7 7C7 9.76142 9.23858 12 12 12Z"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
            <path
              d="M20.5899 22C20.5899 18.13 16.7399 15 11.9999 15C7.25991 15 3.40991 18.13 3.40991 22"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </div>
        <h3>{{ t('profile.overview.personal_info.title') }}</h3>
      </div>
      <button
        v-if="!editUsernameMode"
        class="edit-button modern-edit-btn"
        @click="startEditUsername"
      >
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path
            d="M11 4H4C3.46957 4 2.96086 4.21071 2.58579 4.58579C2.21071 4.96086 2 5.46957 2 6V20C2 20.5304 2.21071 21.0391 2.58579 21.4142C2.96086 21.7893 3.46957 22 4 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V13"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <path
            d="M18.5 2.49998C18.8978 2.10216 19.4374 1.87866 20 1.87866C20.5626 1.87866 21.1022 2.10216 21.5 2.49998C21.8978 2.89781 22.1213 3.43737 22.1213 3.99998C22.1213 4.56259 21.8978 5.10216 21.5 5.49998L12 15L8 16L9 12L18.5 2.49998Z"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        {{ t('profile.overview.edit') }}
      </button>
    </div>
    <div class="profile-card-content">
      <div class="profile-field-group">
        <div class="profile-field">
          <span class="profile-field-label">{{
            t('profile.overview.personal_info.full_name')
          }}</span>
          <div class="profile-field-value">
            <div class="field-content">
              <div class="field-icon">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 4.17157 16.1716C3.42143 16.9217 3 17.9391 3 19V21"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                  <circle
                    cx="12"
                    cy="7"
                    r="4"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </div>
              <span class="field-text"
                >{{ userProfile.first_name }} {{ userProfile.last_name }}</span
              >
            </div>
          </div>
        </div>
        <div class="profile-field">
          <span class="profile-field-label">{{
            t('profile.overview.personal_info.username')
          }}</span>
          <div class="profile-field-value">
            <template v-if="editUsernameMode">
              <div class="edit-field-container">
                <div class="input-container">
                  <div class="input-icon">
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        d="M16 7C16 9.20914 14.2091 11 12 11C9.79086 11 8 9.20914 8 7C8 4.79086 9.79086 3 12 3C14.2091 3 16 4.79086 16 7Z"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                      <path
                        d="M12 14C8.13401 14 5 17.134 5 21H19C19 17.134 15.866 14 12 14Z"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                    </svg>
                  </div>
                  <input
                    v-model="editedUsername"
                    class="modern-input"
                    :disabled="saving"
                    placeholder="Nom d'utilisateur"
                    @keyup.enter="saveUsername"
                    @keyup.escape="cancelEditUsername"
                  />
                </div>
                <div class="edit-actions">
                  <button
                    class="save-button modern-save-btn"
                    :disabled="saving"
                    @click="saveUsername"
                  >
                    <svg
                      v-if="!saving"
                      viewBox="0 0 24 24"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        d="M20 6L9 17L4 12"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                    </svg>
                    <div v-else class="mini-spinner"></div>
                    {{ saving ? t('common.saving') : t('common.save') }}
                  </button>
                  <button
                    class="cancel-button modern-cancel-btn"
                    :disabled="saving"
                    @click="cancelEditUsername"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <line
                        x1="18"
                        y1="6"
                        x2="6"
                        y2="18"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                      <line
                        x1="6"
                        y1="6"
                        x2="18"
                        y2="18"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                    </svg>
                    {{ t('common.cancel') }}
                  </button>
                </div>
              </div>
            </template>
            <template v-else>
              <div class="field-content">
                <div class="field-icon">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M16 7C16 9.20914 14.2091 11 12 11C9.79086 11 8 9.20914 8 7C8 4.79086 9.79086 3 12 3C14.2091 3 16 4.79086 16 7Z"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                    <path
                      d="M12 14C8.13401 14 5 17.134 5 21H19C19 17.134 15.866 14 12 14Z"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                </div>
                <span class="field-text">{{ userProfile.username }}</span>
              </div>
            </template>
          </div>
        </div>
        <div class="profile-field">
          <span class="profile-field-label">{{
            t('profile.overview.personal_info.email')
          }}</span>
          <div class="profile-field-value">
            <div class="field-content">
              <div class="field-icon">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M4 4H20C21.1 4 22 4.9 22 6V18C22 19.1 21.1 20 20 20H4C2.9 20 2 19.1 2 18V6C2 4.9 2.9 4 4 4Z"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                  <polyline
                    points="22,6 12,13 2,6"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </div>
              <span class="field-text">{{ userProfile.email }}</span>
              <div class="verification-section">
                <span
                  v-if="userProfile.is_verified_account"
                  class="verification-badge verified"
                >
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M9 12L11 14L15 10"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                    <circle
                      cx="12"
                      cy="12"
                      r="9"
                      stroke="currentColor"
                      stroke-width="2"
                    />
                  </svg>
                  {{ t('profile.overview.personal_info.verified') }}
                </span>
                <span v-else class="verification-badge unverified">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <circle
                      cx="12"
                      cy="12"
                      r="9"
                      stroke="currentColor"
                      stroke-width="2"
                    />
                    <line
                      x1="12"
                      y1="8"
                      x2="12"
                      y2="12"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                    />
                    <line
                      x1="12"
                      y1="16"
                      x2="12.01"
                      y2="16"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                    />
                  </svg>
                  {{ t('profile.overview.personal_info.unverified') }}
                </span>
              </div>
            </div>
          </div>
        </div>
        <div v-if="userProfile.phone_number" class="profile-field">
          <span class="profile-field-label">{{
            t('profile.overview.personal_info.phone')
          }}</span>
          <div class="profile-field-value">
            <div class="field-content">
              <div class="field-icon">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M22 16.92V19.92C22.0011 20.1985 21.9441 20.4742 21.8325 20.7293C21.7209 20.9845 21.5573 21.2136 21.3521 21.4019C21.1468 21.5901 20.9046 21.7335 20.6407 21.8227C20.3769 21.9119 20.0974 21.9451 19.82 21.92C16.7428 21.5856 13.787 20.5341 11.19 18.85C8.77382 17.3147 6.72533 15.2662 5.18999 12.85C3.49997 10.2412 2.44824 7.27099 2.11999 4.18C2.095 3.90347 2.12787 3.62476 2.21649 3.36162C2.30512 3.09849 2.44756 2.85669 2.63476 2.65162C2.82196 2.44655 3.0498 2.28271 3.30379 2.17052C3.55777 2.05833 3.83233 2.00026 4.10999 2H7.10999C7.59344 1.99522 8.06544 2.16708 8.43945 2.48351C8.81346 2.79993 9.06681 3.23198 9.15999 3.71C9.33652 4.66443 9.61631 5.59478 9.99999 6.48C10.1018 6.74 10.1445 7.02274 10.1237 7.30405C10.1029 7.58535 10.0193 7.85678 9.87999 8.1L8.61999 9.36C10.1897 11.8135 12.2865 13.9103 14.74 15.48L16 14.22C16.2432 14.0806 16.5146 13.997 16.7959 13.9762C17.0772 13.9555 17.36 13.9982 17.62 14.1C18.5052 14.4837 19.4356 14.7635 20.39 14.94C20.8747 15.0336 21.3119 15.2904 21.6271 15.6684C21.9423 16.0464 22.1103 16.5221 22.1 17.01L22 16.92Z"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </div>
              <span class="field-text">{{ userProfile.phone_number }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n';

defineProps({
  userProfile: { type: Object, required: true },
  editUsernameMode: { type: Boolean, required: true },
  saving: { type: Boolean, required: true },
  startEditUsername: { type: Function, required: true },
  cancelEditUsername: { type: Function, required: true },
  saveUsername: { type: Function, required: true },
});
const editedUsername = defineModel('editedUsername', {
  type: String,
  required: true,
});
const { t } = useI18n();
</script>
