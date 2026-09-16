<template>
  <!-- Professional Information Card -->
  <div class="profile-card professional-info-card">
    <div class="profile-card-header">
      <div class="card-title-section">
        <div class="card-icon">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <rect
              x="2"
              y="3"
              width="20"
              height="14"
              rx="2"
              ry="2"
              stroke="currentColor"
              stroke-width="2"
            />
            <line
              x1="8"
              y1="21"
              x2="16"
              y2="21"
              stroke="currentColor"
              stroke-width="2"
            />
            <line
              x1="12"
              y1="17"
              x2="12"
              y2="21"
              stroke="currentColor"
              stroke-width="2"
            />
          </svg>
        </div>
        <h3>{{ t('profile.overview.professional_info.title') }}</h3>
      </div>
      <button
        v-if="!editProfessionalMode"
        class="edit-button modern-edit-btn"
        @click="editProfessionalInfo"
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
      <template v-if="editProfessionalMode">
        <div class="edit-form-container">
          <div class="edit-field-group">
            <div class="edit-field">
              <label for="edit-affiliation" class="edit-field-label">{{
                t('profile.overview.professional_info.affiliation')
              }}</label>
              <input
                id="edit-affiliation"
                v-model="editedProfessional.affiliation"
                :class="{
                  error: professionalValidation.affiliation.isValid === false,
                  valid: professionalValidation.affiliation.isValid === true,
                }"
                :disabled="savingProfessional"
                :placeholder="t('register.affiliation_placeholder')"
                @blur="validateProfessionalField('affiliation')"
              />
              <div
                v-if="professionalValidation.affiliation.message"
                class="validation-message"
                :class="
                  professionalValidation.affiliation.isValid
                    ? 'success'
                    : 'error'
                "
              >
                {{ professionalValidation.affiliation.message }}
              </div>
            </div>
            <div class="edit-field">
              <label for="edit-department" class="edit-field-label">{{
                t('profile.overview.professional_info.department')
              }}</label>
              <input
                id="edit-department"
                v-model="editedProfessional.department"
                class="modern-input"
                :class="{
                  error: professionalValidation.department.isValid === false,
                  valid: professionalValidation.department.isValid === true,
                }"
                :disabled="savingProfessional"
                :placeholder="t('register.department_placeholder')"
                @blur="validateProfessionalField('department')"
              />
              <div
                v-if="professionalValidation.department.message"
                class="validation-message"
                :class="
                  professionalValidation.department.isValid
                    ? 'success'
                    : 'error'
                "
              >
                {{ professionalValidation.department.message }}
              </div>
            </div>
          </div>
          <div class="edit-actions">
            <button
              class="save-button modern-save-btn"
              :disabled="savingProfessional"
              @click="saveProfessional"
            >
              <svg
                v-if="!savingProfessional"
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
              {{ savingProfessional ? t('common.saving') : t('common.save') }}
            </button>
            <button
              class="cancel-button modern-cancel-btn"
              :disabled="savingProfessional"
              @click="cancelEditProfessional"
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
        <div class="profile-field-group">
          <div class="profile-field">
            <span class="profile-field-label">{{
              t('profile.overview.professional_info.affiliation')
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
                      d="M3 21H21M5 21V7L13 2L21 7V21M9 9H10M14 9H15M9 13H10M14 13H15M9 17H10M14 17H15"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                </div>
                <span class="field-text">{{ userProfile.affiliation }}</span>
              </div>
            </div>
          </div>
          <div class="profile-field">
            <span class="profile-field-label">{{
              t('profile.overview.professional_info.department')
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
                      d="M17 21V19C17 17.9391 16.5786 16.9217 15.8284 16.1716C15.0783 15.4214 14.0609 15 13 15H5C3.93913 15 2.92172 15.4214 2.17157 16.1716C1.42143 16.9217 1 17.9391 1 19V21"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                    <circle
                      cx="9"
                      cy="7"
                      r="4"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                    <path
                      d="M23 21V19C22.9993 18.1137 22.7044 17.2528 22.1614 16.5523C21.6184 15.8519 20.8581 15.3516 20 15.13"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                    <path
                      d="M16 3.13C16.8604 3.35031 17.623 3.85071 18.1676 4.55232C18.7122 5.25392 19.0078 6.11683 19.0078 7.005C19.0078 7.89318 18.7122 8.75608 18.1676 9.45769C17.623 10.1593 16.8604 10.6597 16 10.88"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                </div>
                <span class="field-text">{{ userProfile.department }}</span>
              </div>
            </div>
          </div>
          <div class="profile-field">
            <span class="profile-field-label">{{
              t('profile.overview.professional_info.role')
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
                      d="M12 6.253V16.64"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                    />
                    <path
                      d="M18 9V21C18 21.6 17.6 22 17 22H7C6.4 22 6 21.6 6 21V9"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                    <path
                      d="M4 9H20L18.5 2H5.5L4 9Z"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                </div>
                <span
                  class="role-badge modern-role-badge"
                  :class="userProfile.role.toLowerCase()"
                >
                  {{
                    t(
                      `profile.overview.professional_info.roles.${userProfile.role.toLowerCase()}`
                    )
                  }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n';

defineProps({
  userProfile: { type: Object, required: true },
  editProfessionalMode: { type: Boolean, required: true },
  savingProfessional: { type: Boolean, required: true },
  professionalValidation: { type: Object, required: true },
  editProfessionalInfo: { type: Function, required: true },
  validateProfessionalField: { type: Function, required: true },
  saveProfessional: { type: Function, required: true },
  cancelEditProfessional: { type: Function, required: true },
});
const editedProfessional = defineModel('editedProfessional', {
  type: Object,
  required: true,
});
const { t } = useI18n();
</script>
