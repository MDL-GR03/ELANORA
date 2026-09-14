<template>
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
</template>

<script setup>
import { useI18n } from 'vue-i18n';

defineProps({
  userProfile: { type: Object, required: true },
});

const { t } = useI18n();

function formatDate(dateString) {
  if (!dateString) return '';
  return new Date(dateString).toLocaleDateString('fr-FR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}
</script>
