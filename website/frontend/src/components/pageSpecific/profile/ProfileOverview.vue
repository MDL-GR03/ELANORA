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
      <ProfilePersonalCard
        v-model:edited-username="editedUsername"
        :user-profile="userProfile"
        :edit-username-mode="editUsernameMode"
        :saving="saving"
        :start-edit-username="startEditUsername"
        :cancel-edit-username="cancelEditUsername"
        :save-username="saveUsername"
      />
      <ProfileProfessionalCard
        v-model:edited-professional="editedProfessional"
        :user-profile="userProfile"
        :edit-professional-mode="editProfessionalMode"
        :saving-professional="savingProfessional"
        :professional-validation="professionalValidation"
        :edit-professional-info="editProfessionalInfo"
        :validate-professional-field="validateProfessionalField"
        :save-professional="saveProfessional"
        :cancel-edit-professional="cancelEditProfessional"
      />
      <ProfileAddressCard
        v-if="userProfile.address"
        v-model:edited-address="editedAddress"
        :user-profile="userProfile"
        :edit-address-mode="editAddressMode"
        :saving-address="savingAddress"
        :country-options="countryOptions"
        :address-validation="addressValidation"
        :city-validation-message="cityValidationMessage"
        :street-validation-message="streetValidationMessage"
        :postal-code-validation-message="postalCodeValidationMessage"
        :edit-address="editAddress"
        :on-country-change="onCountryChange"
        :validate-city-field="validateCityField"
        :on-city-change="onCityChange"
        :validate-postal-code-field="validatePostalCodeField"
        :on-postal-code-change="onPostalCodeChange"
        :validate-street-name-field="validateStreetNameField"
        :on-street-name-change="onStreetNameChange"
        :save-address="saveAddress"
        :cancel-edit-address="cancelEditAddress"
      />
      <ProfileAccountCard :user-profile="userProfile" />
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
import { watch, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import ProfileAccountCard from '@/components/pageSpecific/profile/ProfileAccountCard.vue';
import ProfileAddressCard from '@/components/pageSpecific/profile/ProfileAddressCard.vue';
import ProfilePersonalCard from '@/components/pageSpecific/profile/ProfilePersonalCard.vue';
import ProfileProfessionalCard from '@/components/pageSpecific/profile/ProfileProfessionalCard.vue';
import { useProfessionalProfileEditor } from '@/composables/useProfessionalProfileEditor';
import { useUsernameProfileEditor } from '@/composables/useUsernameProfileEditor';
import { useAddressProfileEditor } from '@/composables/useAddressProfileEditor';
import {
  updateUserProfile,
  updateUserAddress,
} from '@/api/service/userService.js';
import * as locationService from '@/api/service/locationService';

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

const {
  editUsernameMode,
  editedUsername,
  savingUsername: saving,
  syncUsername,
  startEditUsername,
  cancelEditUsername,
  saveUsername,
} = useUsernameProfileEditor({
  profile: computed(() => props.userProfile),
  updateProfile: updateUserProfile,
  emit,
  translate: t,
});

const {
  editProfessionalMode,
  editedProfessional,
  savingProfessional,
  professionalValidation,
  validateProfessionalField,
  startEditProfessional,
  cancelEditProfessional,
  saveProfessional,
} = useProfessionalProfileEditor({
  profile: computed(() => props.userProfile),
  updateProfile: updateUserProfile,
  emit,
  translate: t,
});

const {
  editAddressMode,
  editedAddress,
  savingAddress,
  countryOptions,
  addressValidation,
  cityValidationMessage,
  streetValidationMessage,
  postalCodeValidationMessage,
  syncAddress,
  validateCityField,
  validatePostalCodeField,
  validateStreetNameField,
  onCityChange,
  onStreetNameChange,
  onPostalCodeChange,
  onCountryChange,
  startEditAddress,
  cancelEditAddress,
  saveAddress,
} = useAddressProfileEditor({
  profile: computed(() => props.userProfile),
  updateAddress: updateUserAddress,
  location: locationService,
  emit,
  translate: t,
});

// Watchers

// Watchers
watch(
  () => props.userProfile,
  (newVal) => {
    if (newVal && !editUsernameMode.value) {
      syncUsername();
    }
    if (newVal && !editProfessionalMode.value) {
      editedProfessional.value = {
        affiliation: newVal.affiliation || '',
        department: newVal.department || '',
      };
    }
    if (newVal && !editAddressMode.value) {
      syncAddress();
    }
  },
  { immediate: true }
);

function editProfessionalInfo() {
  startEditProfessional();
}

function editAddress() {
  startEditAddress();
}
</script>

<style>
@import url('../../../assets/css/profile-overview.css');
</style>
