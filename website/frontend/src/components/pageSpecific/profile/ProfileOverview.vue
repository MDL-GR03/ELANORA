<template>
  <div class="profile-overview">
    <!-- Loading State -->
    <div v-if="loading" class="profile-loading">
      <div class="loading-spinner"></div>
      <p>{{ t('profile.overview.loading') }}</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="profile-error">
      <div class="error-icon">⚠️</div>
      <h3>{{ t('profile.overview.error_title') }}</h3>
      <p>{{ error }}</p>
    </div>

    <!-- Profile Content -->
    <div v-else-if="userProfile" class="profile-content">
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
            <svg
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
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
                    >{{ userProfile.first_name }}
                    {{ userProfile.last_name }}</span
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
            <svg
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
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
                    class="modern-input"
                    :class="{
                      error:
                        professionalValidation.affiliation.isValid === false,
                      valid:
                        professionalValidation.affiliation.isValid === true,
                    }"
                    :disabled="savingProfessional"
                    placeholder="Votre affiliation"
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
                      error:
                        professionalValidation.department.isValid === false,
                      valid: professionalValidation.department.isValid === true,
                    }"
                    :disabled="savingProfessional"
                    placeholder="Votre département"
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
                  {{
                    savingProfessional ? t('common.saving') : t('common.save')
                  }}
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
                    <span class="field-text">{{
                      userProfile.affiliation
                    }}</span>
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

      <!-- Address Information Card -->
      <div v-if="userProfile.address" class="profile-card address-info-card">
        <div class="profile-card-header">
          <div class="card-title-section">
            <div class="card-icon">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M21 10C21 17 12 23 12 23S3 17 3 10C3 7.61305 3.94821 5.32387 5.63604 3.63604C7.32387 1.94821 9.61305 1 12 1C14.3869 1 16.6761 1.94821 18.3639 3.63604C20.0518 5.32387 21 7.61305 21 10Z"
                  stroke="currentColor"
                  stroke-width="2"
                />
                <circle
                  cx="12"
                  cy="10"
                  r="3"
                  stroke="currentColor"
                  stroke-width="2"
                />
              </svg>
            </div>
            <h3>{{ t('profile.overview.address_info.title') }}</h3>
          </div>
          <button
            v-if="!editAddressMode"
            class="edit-button modern-edit-btn"
            @click="editAddress"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
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
          <template v-if="editAddressMode">
            <div class="edit-form-container">
              <div class="edit-field-group">
                <div class="edit-field">
                  <label for="edit-country" class="edit-field-label"
                    >{{ t('register.country_label') }}
                    <span class="required">*</span></label
                  >
                  <select
                    id="edit-country"
                    v-model="editedAddress.countryId"
                    class="modern-input"
                    :disabled="savingAddress"
                    @change="onCountryChange"
                  >
                    <option value="">
                      {{ t('register.country_placeholder') }}
                    </option>
                    <option
                      v-for="country in countries"
                      :key="country.country_id"
                      :value="country.country_id"
                    >
                      {{ country.country_name }}
                    </option>
                  </select>
                </div>

                <div class="edit-field">
                  <label for="edit-city" class="edit-field-label"
                    >{{ t('register.city_label') }}
                    <span class="required">*</span></label
                  >
                  <input
                    id="edit-city"
                    v-model="editedAddress.cityName"
                    class="modern-input"
                    :class="{
                      error: addressValidation.city.isValid === false,
                      valid: addressValidation.city.isValid === true,
                      loading: addressValidation.city.loading,
                    }"
                    :disabled="!editedAddress.countryId || savingAddress"
                    placeholder="Nom de la ville"
                    @blur="validateCityField"
                    @input="onCityChange"
                  />
                  <div
                    v-if="cityValidationMessage"
                    :class="`validation-message ${cityValidationMessage.type}`"
                  >
                    {{ cityValidationMessage.text }}
                  </div>
                </div>

                <div class="edit-field">
                  <label for="edit-postal-code" class="edit-field-label"
                    >{{ t('register.postal_code_label') }}
                    <span class="required">*</span></label
                  >
                  <input
                    id="edit-postal-code"
                    v-model="editedAddress.postalCode"
                    class="modern-input"
                    :class="{
                      error: addressValidation.postalCode.isValid === false,
                      valid: addressValidation.postalCode.isValid === true,
                      loading: addressValidation.postalCode.loading,
                    }"
                    :disabled="!editedAddress.countryId || savingAddress"
                    placeholder="Code postal"
                    @blur="validatePostalCodeField"
                    @input="onPostalCodeChange"
                  />
                  <div
                    v-if="postalCodeValidationMessage"
                    :class="`validation-message ${postalCodeValidationMessage.type}`"
                  >
                    {{ postalCodeValidationMessage.text }}
                  </div>
                </div>

                <div class="edit-field">
                  <label for="edit-street-name" class="edit-field-label"
                    >{{ t('register.street_name_label') }}
                    <span class="required">*</span></label
                  >
                  <input
                    id="edit-street-name"
                    v-model="editedAddress.streetName"
                    class="modern-input"
                    :class="{
                      error: addressValidation.streetName.isValid === false,
                      valid: addressValidation.streetName.isValid === true,
                      loading: addressValidation.streetInCity.loading,
                    }"
                    :disabled="savingAddress"
                    placeholder="Nom de rue"
                    @blur="validateStreetNameField"
                    @input="onStreetNameChange"
                  />
                  <div
                    v-if="streetValidationMessage"
                    :class="`validation-message ${streetValidationMessage.type}`"
                  >
                    {{ streetValidationMessage.text }}
                  </div>
                </div>

                <div class="edit-field">
                  <label for="edit-street-number" class="edit-field-label">{{
                    t('register.street_number_label')
                  }}</label>
                  <input
                    id="edit-street-number"
                    v-model="editedAddress.streetNumber"
                    class="modern-input"
                    :disabled="savingAddress"
                    placeholder="Numéro de rue (optionnel)"
                  />
                </div>

                <div class="edit-field">
                  <label for="edit-address-line2" class="edit-field-label">{{
                    t('register.address_line2_label')
                  }}</label>
                  <input
                    id="edit-address-line2"
                    v-model="editedAddress.addressLine2"
                    class="modern-input"
                    :disabled="savingAddress"
                    placeholder="Complément d'adresse (optionnel)"
                  />
                </div>
              </div>
              <div class="edit-actions">
                <button
                  class="save-button modern-save-btn"
                  :disabled="savingAddress"
                  @click="saveAddress"
                >
                  <svg
                    v-if="!savingAddress"
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
                  {{ savingAddress ? t('common.saving') : t('common.save') }}
                </button>
                <button
                  class="cancel-button modern-cancel-btn"
                  :disabled="savingAddress"
                  @click="cancelEditAddress"
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
                  t('profile.overview.address_info.street')
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
                          d="M3 9L12 2L21 9V20C21 20.5304 20.7893 21.0391 20.4142 21.4142C20.0391 21.7893 19.5304 22 19 22H5C4.46957 22 3.96086 21.7893 3.58579 21.4142C3.21071 21.0391 3 20.5304 3 20V9Z"
                          stroke="currentColor"
                          stroke-width="2"
                          stroke-linecap="round"
                          stroke-linejoin="round"
                        />
                        <polyline
                          points="9,22 9,12 15,12 15,22"
                          stroke="currentColor"
                          stroke-width="2"
                          stroke-linecap="round"
                          stroke-linejoin="round"
                        />
                      </svg>
                    </div>
                    <span class="field-text">
                      <span v-if="userProfile.address.street_number">
                        {{ userProfile.address.street_number }}
                      </span>
                      {{ userProfile.address.street_name }}
                    </span>
                  </div>
                </div>
              </div>
              <div
                v-if="userProfile.address.address_line_2"
                class="profile-field"
              >
                <span class="profile-field-label">{{
                  t('profile.overview.address_info.address_line_2')
                }}</span>
                <div class="profile-field-value">
                  <div class="field-content">
                    <div class="field-icon">
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <rect
                          x="3"
                          y="4"
                          width="18"
                          height="16"
                          rx="2"
                          stroke="currentColor"
                          stroke-width="2"
                          stroke-linecap="round"
                          stroke-linejoin="round"
                        />
                        <line
                          x1="7"
                          y1="8"
                          x2="17"
                          y2="8"
                          stroke="currentColor"
                          stroke-width="2"
                          stroke-linecap="round"
                        />
                        <line
                          x1="7"
                          y1="12"
                          x2="17"
                          y2="12"
                          stroke="currentColor"
                          stroke-width="2"
                          stroke-linecap="round"
                        />
                        <line
                          x1="7"
                          y1="16"
                          x2="11"
                          y2="16"
                          stroke="currentColor"
                          stroke-width="2"
                          stroke-linecap="round"
                        />
                      </svg>
                    </div>
                    <span class="field-text">{{
                      userProfile.address.address_line_2
                    }}</span>
                  </div>
                </div>
              </div>
              <div class="profile-field">
                <span class="profile-field-label">{{
                  t('profile.overview.address_info.city_postal')
                }}</span>
                <div class="profile-field-value">
                  <div class="field-content">
                    <div class="field-icon">
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <circle
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          stroke-width="2"
                        />
                        <path
                          d="M2 12H22"
                          stroke="currentColor"
                          stroke-width="2"
                        />
                        <path
                          d="M12 2C14.5013 4.73835 15.9228 8.29203 16 12C15.9228 15.708 14.5013 19.2616 12 22C9.49872 19.2616 8.07725 15.708 8 12C8.07725 8.29203 9.49872 4.73835 12 2Z"
                          stroke="currentColor"
                          stroke-width="2"
                        />
                      </svg>
                    </div>
                    <span class="field-text">
                      {{ userProfile.address.postal_code }}
                      <span v-if="userProfile.address.city">
                        {{ userProfile.address.city.name }},
                        {{ userProfile.address.city.country }}
                      </span>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- Account Information Card -->
      <div class="profile-card account-info-card">
        <div class="profile-card-header">
          <div class="card-title-section">
            <div class="card-icon">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M12 15C15.866 15 19 11.866 19 8C19 4.13401 15.866 1 12 1C8.13401 1 5 4.13401 5 8C5 11.866 8.13401 15 12 15Z"
                  stroke="currentColor"
                  stroke-width="2"
                />
                <path
                  d="M8.21 13.89L7 23L12 20L17 23L15.79 13.88"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </div>
            <h3>{{ t('profile.overview.account_info.title') }}</h3>
          </div>
        </div>
        <div class="profile-card-content">
          <div class="profile-field-group">
            <div class="profile-field">
              <span class="profile-field-label">{{
                t('profile.overview.account_info.member_since')
              }}</span>
              <div class="profile-field-value">
                <div class="field-content">
                  <div class="field-icon">
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <rect
                        x="3"
                        y="4"
                        width="18"
                        height="18"
                        rx="2"
                        ry="2"
                        stroke="currentColor"
                        stroke-width="2"
                      />
                      <line
                        x1="16"
                        y1="2"
                        x2="16"
                        y2="6"
                        stroke="currentColor"
                        stroke-width="2"
                      />
                      <line
                        x1="8"
                        y1="2"
                        x2="8"
                        y2="6"
                        stroke="currentColor"
                        stroke-width="2"
                      />
                      <line
                        x1="3"
                        y1="10"
                        x2="21"
                        y2="10"
                        stroke="currentColor"
                        stroke-width="2"
                      />
                    </svg>
                  </div>
                  <span class="field-text">{{
                    formatDate(userProfile.created_at)
                  }}</span>
                </div>
              </div>
            </div>
            <div class="profile-field">
              <span class="profile-field-label">{{
                t('profile.overview.account_info.last_updated')
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
                        d="M23 4V10H17"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                      <path
                        d="M20.49 15C19.9828 16.8393 18.9228 18.4804 17.4612 19.7006C15.9996 20.9207 14.2019 21.6641 12.2856 21.8281C10.3694 21.9922 8.44444 21.5705 6.77579 20.6123C5.10714 19.6541 3.76781 18.1969 2.915 16.4281C2.06219 14.6593 1.73427 12.6519 1.97979 10.6794C2.22532 8.70689 3.03423 6.8607 4.31198 5.35635C5.58973 3.852 7.27707 2.76321 9.16584 2.22672C11.0546 1.69023 13.0607 1.72429 14.93 2.32"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                      <polyline
                        points="23,4 12,15 9,12"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                    </svg>
                  </div>
                  <span class="field-text">{{
                    formatDate(userProfile.updated_at)
                  }}</span>
                </div>
              </div>
            </div>
            <div v-if="userProfile.last_login" class="profile-field">
              <span class="profile-field-label">{{
                t('profile.overview.account_info.last_login')
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
                        d="M15 3H19C19.5304 3 20.0391 3.21071 20.4142 3.58579C20.7893 3.96086 21 4.46957 21 5V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H15"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                      <polyline
                        points="10,17 15,12 10,7"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                      <line
                        x1="15"
                        y1="12"
                        x2="3"
                        y2="12"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                    </svg>
                  </div>
                  <span class="field-text">{{
                    formatDate(userProfile.last_login)
                  }}</span>
                </div>
              </div>
            </div>
            <div class="profile-field">
              <span class="profile-field-label">{{
                t('profile.overview.account_info.account_status')
              }}</span>
              <div class="profile-field-value">
                <div class="field-content">
                  <div class="field-icon">
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <circle
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        stroke-width="2"
                      />
                      <path
                        v-if="userProfile.is_active"
                        d="M9 12L11 14L15 10"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                      <g v-else>
                        <line
                          x1="15"
                          y1="9"
                          x2="9"
                          y2="15"
                          stroke="currentColor"
                          stroke-width="2"
                          stroke-linecap="round"
                          stroke-linejoin="round"
                        />
                        <line
                          x1="9"
                          y1="9"
                          x2="15"
                          y2="15"
                          stroke="currentColor"
                          stroke-width="2"
                          stroke-linecap="round"
                          stroke-linejoin="round"
                        />
                      </g>
                    </svg>
                  </div>
                  <span
                    class="status-badge modern-status-badge"
                    :class="userProfile.is_active ? 'active' : 'inactive'"
                  >
                    {{
                      userProfile.is_active
                        ? t('profile.overview.account_info.active')
                        : t('profile.overview.account_info.inactive')
                    }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="profile-empty">
      <div class="empty-icon">👤</div>
      <h3>{{ t('profile.overview.empty_title') }}</h3>
      <p>{{ t('profile.overview.empty_message') }}</p>
    </div>
  </div>
</template>
<script setup>
import { ref, watch, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  updateUserProfile,
  updateUserAddress,
} from '@/api/service/userService.js';
import {
  getCountries,
  validateCity,
  validatePostalCode,
  validatePostalCodeInCity,
  validateStreetInCity,
  validateStreetName,
} from '@/api/service/locationService';

const { t } = useI18n();

const props = defineProps({
  userProfile: {
    type: Object,
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: '',
  },
});

const emit = defineEmits(['profile-updated', 'show-message']);

// Username editing
const editUsernameMode = ref(false);
const editedUsername = ref('');
const saving = ref(false);

// Professional info editing
const editProfessionalMode = ref(false);
const editedProfessional = ref({
  affiliation: '',
  department: '',
});
const savingProfessional = ref(false);
const professionalValidation = ref({
  affiliation: { isValid: null, message: '' },
  department: { isValid: null, message: '' },
});

// Address editing
const editAddressMode = ref(false);
const editedAddress = ref({
  streetName: '',
  streetNumber: '',
  addressLine2: '',
  cityName: '',
  postalCode: '',
  countryId: '',
});
const savingAddress = ref(false);
const countries = ref([]);
const addressValidation = ref({
  city: { isValid: null, message: '', loading: false },
  postalCode: { isValid: null, message: '', loading: false },
  streetName: { isValid: null, message: '' },
  streetInCity: { isValid: null, message: '', loading: false },
  postalCodeInCity: { isValid: null, message: '', loading: false },
});

// Validation timeouts
let cityValidationTimeout = null;
let streetValidationTimeout = null;
let postalCodeValidationTimeout = null;

// Computed properties for validation messages
const cityValidationMessage = computed(() => {
  if (addressValidation.value.city.loading) {
    return { type: 'info', text: t('register.validating_city') };
  }
  if (addressValidation.value.city.isValid === false) {
    return { type: 'error', text: addressValidation.value.city.message };
  }
  if (
    addressValidation.value.city.isValid === true &&
    addressValidation.value.city.message
  ) {
    return { type: 'success', text: addressValidation.value.city.message };
  }
  return null;
});

const streetValidationMessage = computed(() => {
  if (addressValidation.value.streetInCity.loading) {
    return { type: 'info', text: t('register.validating_street_in_city') };
  }
  if (addressValidation.value.streetInCity.isValid === false) {
    return {
      type: 'warning',
      text: addressValidation.value.streetInCity.message,
    };
  }
  if (addressValidation.value.streetInCity.isValid === true) {
    return {
      type: 'success',
      text: addressValidation.value.streetInCity.message,
    };
  }
  if (addressValidation.value.streetName.isValid === false) {
    return { type: 'error', text: addressValidation.value.streetName.message };
  }
  if (
    addressValidation.value.streetName.isValid === true &&
    addressValidation.value.streetName.message
  ) {
    return {
      type: 'success',
      text: addressValidation.value.streetName.message,
    };
  }
  return null;
});

const postalCodeValidationMessage = computed(() => {
  if (addressValidation.value.postalCode.loading) {
    return { type: 'info', text: t('register.validating_postal_code') };
  }
  if (addressValidation.value.postalCodeInCity.loading) {
    return { type: 'info', text: t('register.validating_postal_code_in_city') };
  }
  if (addressValidation.value.postalCodeInCity.isValid === false) {
    return {
      type: 'warning',
      text: addressValidation.value.postalCodeInCity.message,
    };
  }
  if (addressValidation.value.postalCodeInCity.isValid === true) {
    return {
      type: 'success',
      text: addressValidation.value.postalCodeInCity.message,
    };
  }
  if (addressValidation.value.postalCode.isValid === false) {
    return { type: 'error', text: addressValidation.value.postalCode.message };
  }
  if (
    addressValidation.value.postalCode.isValid === true &&
    addressValidation.value.postalCode.message
  ) {
    return {
      type: 'success',
      text: addressValidation.value.postalCode.message,
    };
  }
  return null;
});

// Watchers

// Watchers
watch(
  () => props.userProfile,
  (newVal) => {
    if (newVal && !editUsernameMode.value) {
      editedUsername.value = newVal.username;
    }
    if (newVal && !editProfessionalMode.value) {
      editedProfessional.value = {
        affiliation: newVal.affiliation || '',
        department: newVal.department || '',
      };
    }
    if (newVal && !editAddressMode.value) {
      editedAddress.value = {
        streetName: newVal.address?.street_name || '',
        streetNumber: newVal.address?.street_number || '',
        addressLine2: newVal.address?.address_line_2 || '',
        cityName: newVal.address?.city?.name || '',
        postalCode: newVal.address?.postal_code || '',
        countryId: newVal.address?.city?.country || '',
      };
    }
  },
  { immediate: true }
);

// Load countries when component mounts
const loadCountries = async () => {
  try {
    const result = await getCountries();
    if (result.success) {
      countries.value = result.data;
    }
  } catch (error) {
    console.error('Error loading countries:', error);
  }
};

// Professional validation functions
function validateProfessionalField(fieldName) {
  switch (fieldName) {
    case 'affiliation':
      if (!editedProfessional.value.affiliation) {
        professionalValidation.value.affiliation = {
          isValid: false,
          message: t('register.affiliation_required'),
        };
      } else if (editedProfessional.value.affiliation.length < 2) {
        professionalValidation.value.affiliation = {
          isValid: false,
          message: 'Affiliation must be at least 2 characters',
        };
      } else if (editedProfessional.value.affiliation.length > 100) {
        professionalValidation.value.affiliation = {
          isValid: false,
          message: 'Affiliation must be less than 100 characters',
        };
      } else {
        professionalValidation.value.affiliation = {
          isValid: true,
          message: '',
        };
      }
      break;

    case 'department':
      if (!editedProfessional.value.department) {
        professionalValidation.value.department = {
          isValid: false,
          message: t('register.department_required'),
        };
      } else if (editedProfessional.value.department.length < 2) {
        professionalValidation.value.department = {
          isValid: false,
          message: 'Department must be at least 2 characters',
        };
      } else if (editedProfessional.value.department.length > 100) {
        professionalValidation.value.department = {
          isValid: false,
          message: 'Department must be less than 100 characters',
        };
      } else {
        professionalValidation.value.department = {
          isValid: true,
          message: '',
        };
      }
      break;
  }
}

// Address validation functions (matching RegisterPage.vue)
async function validateCityField() {
  if (!editedAddress.value.cityName || !editedAddress.value.countryId) {
    const message = editedAddress.value.cityName
      ? t('register.country_required')
      : t('register.city_required');
    addressValidation.value.city = { isValid: false, message, loading: false };
    return;
  }

  addressValidation.value.city.loading = true;

  try {
    const result = await validateCity(
      editedAddress.value.cityName,
      editedAddress.value.countryId
    );

    await handleCityValidationResult(result);
  } catch (error) {
    console.error('Error validating city:', error);
    addressValidation.value.city = {
      isValid: false,
      message: t('register.city_validation_error'),
      loading: false,
    };
  }
}

async function handleCityValidationResult(result) {
  if (!result.success) {
    addressValidation.value.city = {
      isValid: false,
      message: t('register.city_validation_error'),
      loading: false,
    };
    return;
  }

  const message = result.data.isValid
    ? t('register.city_valid_in_country')
    : result.data.message || t('register.city_not_found_in_country');

  addressValidation.value.city = {
    isValid: result.data.isValid,
    message,
    loading: false,
  };

  if (result.data.isValid) {
    await performCrossValidations();
  } else {
    resetCrossValidations();
  }
}

async function performCrossValidations() {
  if (editedAddress.value.streetName) {
    await validateStreetInCityField();
  }
  if (editedAddress.value.postalCode) {
    await validatePostalCodeInCityField();
  }
}

function resetCrossValidations() {
  addressValidation.value.streetInCity = {
    isValid: null,
    message: '',
    loading: false,
  };
  addressValidation.value.postalCodeInCity = {
    isValid: null,
    message: '',
    loading: false,
  };
}

async function validatePostalCodeField() {
  if (!editedAddress.value.postalCode || !editedAddress.value.countryId) {
    addressValidation.value.postalCode = {
      isValid: false,
      message: t('register.postal_code_required'),
      loading: false,
    };
    return;
  }

  addressValidation.value.postalCode.loading = true;

  try {
    const result = await validatePostalCode(
      editedAddress.value.postalCode,
      editedAddress.value.countryId
    );

    if (result.success) {
      const isFormatValid = result.data.isValid;

      addressValidation.value.postalCode = {
        isValid: isFormatValid,
        message: isFormatValid ? '' : result.data.message,
        loading: false,
      };

      if (
        isFormatValid &&
        editedAddress.value.cityName &&
        addressValidation.value.city.isValid === true
      ) {
        await validatePostalCodeInCityField();
      } else {
        addressValidation.value.postalCodeInCity = {
          isValid: null,
          message: '',
          loading: false,
        };
      }
    } else {
      addressValidation.value.postalCode = {
        isValid: false,
        message: t('register.postal_code_validation_error'),
        loading: false,
      };
    }
  } catch (error) {
    console.error('Error validating postal code:', error);
    addressValidation.value.postalCode = {
      isValid: false,
      message: t('register.postal_code_validation_error'),
      loading: false,
    };
  }
}

async function validateStreetNameField() {
  const result = validateStreetName(editedAddress.value.streetName);

  if (!result.isValid) {
    addressValidation.value.streetName = {
      isValid: false,
      message: result.message,
    };
    addressValidation.value.streetInCity = {
      isValid: null,
      message: '',
      loading: false,
    };
    return;
  }

  addressValidation.value.streetName = {
    isValid: true,
    message: '',
  };

  if (
    editedAddress.value.cityName &&
    editedAddress.value.countryId &&
    addressValidation.value.city.isValid === true
  ) {
    await validateStreetInCityField();
  } else {
    addressValidation.value.streetInCity = {
      isValid: null,
      message: '',
      loading: false,
    };
  }
}

async function validateStreetInCityField() {
  if (
    !editedAddress.value.streetName ||
    !editedAddress.value.cityName ||
    !editedAddress.value.countryId
  ) {
    addressValidation.value.streetInCity = {
      isValid: null,
      message: '',
      loading: false,
    };
    return;
  }

  addressValidation.value.streetInCity.loading = true;

  try {
    const result = await validateStreetInCity(
      editedAddress.value.streetName,
      editedAddress.value.cityName,
      editedAddress.value.countryId
    );

    if (result.success) {
      addressValidation.value.streetInCity = {
        isValid: result.data.isValid,
        message: result.data.message,
        loading: false,
        suggestions: result.data.suggestions || [],
      };
    } else {
      addressValidation.value.streetInCity = {
        isValid: false,
        message: t('register.street_validation_error'),
        loading: false,
      };
    }
  } catch (error) {
    console.error('Error validating street in city:', error);
    addressValidation.value.streetInCity = {
      isValid: false,
      message: t('register.street_validation_error'),
      loading: false,
    };
  }
}

async function validatePostalCodeInCityField() {
  if (
    !editedAddress.value.postalCode ||
    !editedAddress.value.cityName ||
    !editedAddress.value.countryId
  ) {
    addressValidation.value.postalCodeInCity = {
      isValid: null,
      message: '',
      loading: false,
    };
    return;
  }

  addressValidation.value.postalCodeInCity.loading = true;

  try {
    const result = await validatePostalCodeInCity(
      editedAddress.value.postalCode,
      editedAddress.value.cityName,
      editedAddress.value.countryId
    );

    if (result.success) {
      addressValidation.value.postalCodeInCity = {
        isValid: result.data.isValid,
        message: result.data.message,
        loading: false,
        suggestions: result.data.suggestions || [],
      };
    } else {
      addressValidation.value.postalCodeInCity = {
        isValid: false,
        message: t('register.postal_code_city_validation_error'),
        loading: false,
      };
    }
  } catch (error) {
    console.error('Error validating postal code in city:', error);
    addressValidation.value.postalCodeInCity = {
      isValid: false,
      message: t('register.postal_code_city_validation_error'),
      loading: false,
    };
  }
}

// Debounced validation handlers
const onCityChange = async () => {
  addressValidation.value.city = { isValid: null, message: '', loading: false };
  addressValidation.value.streetInCity = {
    isValid: null,
    message: '',
    loading: false,
  };
  addressValidation.value.postalCodeInCity = {
    isValid: null,
    message: '',
    loading: false,
  };

  clearTimeout(cityValidationTimeout);
  cityValidationTimeout = setTimeout(async () => {
    if (editedAddress.value.cityName && editedAddress.value.countryId) {
      await validateCityField();
    }
  }, 500);
};

const onStreetNameChange = async () => {
  addressValidation.value.streetName = { isValid: null, message: '' };
  addressValidation.value.streetInCity = {
    isValid: null,
    message: '',
    loading: false,
  };

  clearTimeout(streetValidationTimeout);
  streetValidationTimeout = setTimeout(async () => {
    if (editedAddress.value.streetName) {
      await validateStreetNameField();
    }
  }, 500);
};

const onPostalCodeChange = async () => {
  addressValidation.value.postalCode = {
    isValid: null,
    message: '',
    loading: false,
  };
  addressValidation.value.postalCodeInCity = {
    isValid: null,
    message: '',
    loading: false,
  };

  clearTimeout(postalCodeValidationTimeout);
  postalCodeValidationTimeout = setTimeout(async () => {
    if (editedAddress.value.postalCode && editedAddress.value.countryId) {
      await validatePostalCodeField();
    }
  }, 500);
};

const onCountryChange = () => {
  addressValidation.value.city = { isValid: null, message: '', loading: false };
  addressValidation.value.postalCode = {
    isValid: null,
    message: '',
    loading: false,
  };
  addressValidation.value.streetInCity = {
    isValid: null,
    message: '',
    loading: false,
  };
  addressValidation.value.postalCodeInCity = {
    isValid: null,
    message: '',
    loading: false,
  };

  if (editedAddress.value.cityName) {
    editedAddress.value.cityName = '';
  }
  if (editedAddress.value.postalCode) {
    editedAddress.value.postalCode = '';
  }
};

// Username editing functions
function startEditUsername() {
  editUsernameMode.value = true;
  editedUsername.value = props.userProfile?.username || '';
}

function cancelEditUsername() {
  editUsernameMode.value = false;
  editedUsername.value = props.userProfile?.username || '';
}

async function saveUsername() {
  if (saving.value) return;

  if (!editedUsername.value.trim()) {
    emit('show-message', {
      text: "Le nom d'utilisateur ne peut pas être vide",
      type: 'error',
    });
    return;
  }

  if (editedUsername.value === props.userProfile?.username) {
    editUsernameMode.value = false;
    return;
  }

  try {
    saving.value = true;

    const response = await updateUserProfile({
      username: editedUsername.value,
    });

    if (response.data) {
      emit('show-message', {
        text: "Nom d'utilisateur mis à jour avec succès",
        type: 'success',
      });
      emit('profile-updated');
      editUsernameMode.value = false;
    }
  } catch (error) {
    console.error('Error updating username:', error);
    let errorMessage = "Erreur lors de la mise à jour du nom d'utilisateur";

    if (error.response?.data?.detail) {
      if (error.response.data.detail.includes('already taken')) {
        errorMessage = "Ce nom d'utilisateur est déjà pris";
      } else {
        errorMessage = error.response.data.detail;
      }
    }

    emit('show-message', { text: errorMessage, type: 'error' });
    editedUsername.value = props.userProfile?.username || '';
  } finally {
    saving.value = false;
  }
}

// Professional info editing functions
async function startEditProfessional() {
  editProfessionalMode.value = true;
  editedProfessional.value = {
    affiliation: props.userProfile?.affiliation || '',
    department: props.userProfile?.department || '',
  };
  professionalValidation.value = {
    affiliation: { isValid: null, message: '' },
    department: { isValid: null, message: '' },
  };
}

function cancelEditProfessional() {
  editProfessionalMode.value = false;
  editedProfessional.value = {
    affiliation: props.userProfile?.affiliation || '',
    department: props.userProfile?.department || '',
  };
  professionalValidation.value = {
    affiliation: { isValid: null, message: '' },
    department: { isValid: null, message: '' },
  };
}

async function saveProfessional() {
  if (savingProfessional.value) return;

  // Validate fields
  validateProfessionalField('affiliation');
  validateProfessionalField('department');

  const hasErrors =
    professionalValidation.value.affiliation.isValid === false ||
    professionalValidation.value.department.isValid === false;

  if (hasErrors) {
    emit('show-message', {
      text: 'Veuillez corriger les erreurs avant de sauvegarder',
      type: 'error',
    });
    return;
  }

  // Check if values have actually changed
  const profileData = {};
  let hasChanges = false;

  if (editedProfessional.value.affiliation !== props.userProfile?.affiliation) {
    profileData.affiliation = editedProfessional.value.affiliation;
    hasChanges = true;
  }

  if (editedProfessional.value.department !== props.userProfile?.department) {
    profileData.department = editedProfessional.value.department;
    hasChanges = true;
  }

  if (!hasChanges) {
    emit('show-message', {
      text: 'Aucune modification détectée',
      type: 'info',
    });
    editProfessionalMode.value = false;
    return;
  }

  try {
    savingProfessional.value = true;

    const response = await updateUserProfile(profileData);

    if (response.data) {
      emit('show-message', {
        text: 'Informations professionnelles mises à jour avec succès',
        type: 'success',
      });
      emit('profile-updated');
      editProfessionalMode.value = false;
    }
  } catch (error) {
    console.error('Error updating professional info:', error);
    let errorMessage =
      'Erreur lors de la mise à jour des informations professionnelles';

    if (error.response?.data?.detail) {
      errorMessage = error.response.data.detail;
    } else if (error.response?.status === 400) {
      errorMessage =
        'Données invalides. Veuillez vérifier les informations saisies.';
    }

    emit('show-message', { text: errorMessage, type: 'error' });
  } finally {
    savingProfessional.value = false;
  }
}

// Address editing functions
async function startEditAddress() {
  editAddressMode.value = true;
  editedAddress.value = {
    streetName: props.userProfile?.address?.street_name || '',
    streetNumber: props.userProfile?.address?.street_number || '',
    addressLine2: props.userProfile?.address?.address_line_2 || '',
    cityName: props.userProfile?.address?.city?.name || '',
    postalCode: props.userProfile?.address?.postal_code || '',
    countryId: props.userProfile?.address?.city?.country || '',
  };

  // Reset validations
  addressValidation.value = {
    city: { isValid: null, message: '', loading: false },
    postalCode: { isValid: null, message: '', loading: false },
    streetName: { isValid: null, message: '' },
    streetInCity: { isValid: null, message: '', loading: false },
    postalCodeInCity: { isValid: null, message: '', loading: false },
  };

  // Load countries if not already loaded
  if (countries.value.length === 0) {
    await loadCountries();
  }
}

function cancelEditAddress() {
  editAddressMode.value = false;
  editedAddress.value = {
    streetName: props.userProfile?.address?.street_name || '',
    streetNumber: props.userProfile?.address?.street_number || '',
    addressLine2: props.userProfile?.address?.address_line_2 || '',
    cityName: props.userProfile?.address?.city?.name || '',
    postalCode: props.userProfile?.address?.postal_code || '',
    countryId: props.userProfile?.address?.city?.country || '',
  };

  addressValidation.value = {
    city: { isValid: null, message: '', loading: false },
    postalCode: { isValid: null, message: '', loading: false },
    streetName: { isValid: null, message: '' },
    streetInCity: { isValid: null, message: '', loading: false },
    postalCodeInCity: { isValid: null, message: '', loading: false },
  };
}

async function saveAddress() {
  if (savingAddress.value) return;

  // Validate required fields
  if (!editedAddress.value.streetName) {
    emit('show-message', { text: 'Le nom de rue est requis', type: 'error' });
    return;
  }

  if (!editedAddress.value.cityName) {
    emit('show-message', { text: 'Le nom de ville est requis', type: 'error' });
    return;
  }

  if (!editedAddress.value.postalCode) {
    emit('show-message', { text: 'Le code postal est requis', type: 'error' });
    return;
  }

  if (!editedAddress.value.countryId) {
    emit('show-message', { text: 'Le pays est requis', type: 'error' });
    return;
  }

  // Check validation states
  if (
    addressValidation.value.city.isValid === false ||
    addressValidation.value.postalCode.isValid === false ||
    addressValidation.value.streetName.isValid === false
  ) {
    emit('show-message', {
      text: 'Veuillez corriger les erreurs de validation avant de sauvegarder',
      type: 'error',
    });
    return;
  }

  // Check cross-validations
  if (
    addressValidation.value.streetInCity.isValid === false ||
    addressValidation.value.postalCodeInCity.isValid === false
  ) {
    emit('show-message', {
      text: "L'adresse ne semble pas correspondre. Veuillez vérifier les informations.",
      type: 'warning',
    });
    // Allow saving but with warning - user choice
  }

  try {
    savingAddress.value = true;

    const selectedCountry = countries.value.find(
      (country) => country.country_id === editedAddress.value.countryId
    );

    // Format address data according to backend schema
    const addressData = {
      street_name: editedAddress.value.streetName,
      street_number: editedAddress.value.streetNumber || null,
      city_name: editedAddress.value.cityName,
      country_code: editedAddress.value.countryId,
      country_name: selectedCountry?.country_name || '',
      postal_code: editedAddress.value.postalCode,
      address_line_2: editedAddress.value.addressLine2 || null,
    };

    const response = await updateUserAddress(addressData);

    if (response.data) {
      emit('show-message', {
        text: 'Adresse mise à jour avec succès',
        type: 'success',
      });
      emit('profile-updated');
      editAddressMode.value = false;
    }
  } catch (error) {
    console.error('Error updating address:', error);
    let errorMessage = "Erreur lors de la mise à jour de l'adresse";

    if (error.response?.data?.detail) {
      errorMessage = error.response.data.detail;
    } else if (error.response?.status === 400) {
      errorMessage =
        "Données d'adresse invalides. Veuillez vérifier les informations saisies.";
    } else if (error.response?.status === 500) {
      errorMessage =
        "Erreur serveur lors de la mise à jour de l'adresse. Veuillez réessayer.";
    }

    emit('show-message', { text: errorMessage, type: 'error' });
  } finally {
    savingAddress.value = false;
  }
}

function formatDate(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('fr-FR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

function editProfessionalInfo() {
  startEditProfessional();
}

function editAddress() {
  startEditAddress();
}
</script>

<style scoped>
@import url('../../../assets/css/profile-overview.css');
</style>
