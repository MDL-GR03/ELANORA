<template>
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
      <template v-if="editAddressMode">
        <div class="edit-form-container">
          <div class="edit-field-group">
            <div class="edit-field">
              <label for="edit-country" class="edit-field-label"
                >{{ t('register.country_label') }}
                <span class="required">*</span></label
              >
              <AppSelect
                id="edit-country"
                v-model="editedAddress.countryId"
                class="modern-input"
                :disabled="savingAddress"
                :placeholder="t('register.country_placeholder')"
                :options="countryOptions"
                @change="onCountryChange"
              />
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
          <div v-if="userProfile.address.address_line_2" class="profile-field">
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
                    <path d="M2 12H22" stroke="currentColor" stroke-width="2" />
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
</template>

<script setup>
import { useI18n } from 'vue-i18n';
import AppSelect from '@/components/common/AppSelect.vue';

defineProps({
  userProfile: { type: Object, required: true },
  editAddressMode: { type: Boolean, required: true },
  savingAddress: { type: Boolean, required: true },
  countryOptions: { type: Array, required: true },
  addressValidation: { type: Object, required: true },
  cityValidationMessage: { type: Object, default: null },
  streetValidationMessage: { type: Object, default: null },
  postalCodeValidationMessage: { type: Object, default: null },
  editAddress: { type: Function, required: true },
  onCountryChange: { type: Function, required: true },
  validateCityField: { type: Function, required: true },
  onCityChange: { type: Function, required: true },
  validatePostalCodeField: { type: Function, required: true },
  onPostalCodeChange: { type: Function, required: true },
  validateStreetNameField: { type: Function, required: true },
  onStreetNameChange: { type: Function, required: true },
  saveAddress: { type: Function, required: true },
  cancelEditAddress: { type: Function, required: true },
});
const editedAddress = defineModel('editedAddress', {
  type: Object,
  required: true,
});
const { t } = useI18n();
</script>
