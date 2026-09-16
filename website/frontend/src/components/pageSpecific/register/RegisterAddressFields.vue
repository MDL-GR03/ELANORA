<template>
  <div class="address-section">
    <h3 class="section-title">{{ t('register.address_section') }}</h3>

    <div class="form-row">
      <div class="form-group">
        <label for="country" class="form-label">
          {{ t('register.country_label') }}
          <span class="required">*</span>
        </label>
        <AppSelect
          id="country"
          v-model="address.countryId"
          :invalid="Boolean(countryError)"
          :required="true"
          :placeholder="t('register.country_placeholder')"
          :options="countryOptions"
          aria-describedby="country-message"
          @change="emit('country-change')"
          @blur="emit('validate-country')"
        />
        <div id="country-message" class="validation-messages">
          <div v-if="countryError" class="error-message" role="alert">
            {{ countryError }}
          </div>
        </div>
      </div>

      <div class="form-group">
        <label for="city" class="form-label">
          {{ t('register.city_label') }}
          <span class="required">*</span>
        </label>
        <input
          id="city"
          v-model="address.cityName"
          type="text"
          class="form-input"
          :class="{
            error: checks.city.isValid === false,
            valid: isConfirmed(cityMessage),
            loading: checks.city.loading,
          }"
          :placeholder="t('register.city_placeholder')"
          :aria-invalid="checks.city.isValid === false"
          aria-describedby="city-message"
          :disabled="!address.countryId"
          required
          @blur="verification.validateCity()"
          @input="verification.onCityChange()"
        />
        <FieldMessage id="city-message" :message="cityMessage" />
      </div>
    </div>

    <div class="form-row">
      <div class="form-group">
        <label for="streetName" class="form-label">
          {{ t('register.street_name_label') }}
          <span class="required">*</span>
        </label>
        <input
          id="streetName"
          v-model="address.streetName"
          type="text"
          class="form-input"
          :class="{
            error: checks.streetName.isValid === false,
            valid: isConfirmed(streetMessage),
          }"
          :placeholder="t('register.street_name_placeholder')"
          :aria-invalid="checks.streetName.isValid === false"
          aria-describedby="street-name-message"
          required
          @blur="verification.validateStreetName()"
          @input="verification.onStreetNameChange()"
        />
        <FieldMessage id="street-name-message" :message="streetMessage" />
      </div>

      <div class="form-group">
        <label for="streetNumber" class="form-label">
          {{ t('register.street_number_label') }}
        </label>
        <input
          id="streetNumber"
          v-model="address.streetNumber"
          type="text"
          class="form-input"
          :placeholder="t('register.street_number_placeholder')"
        />
      </div>
    </div>

    <div class="form-row">
      <div class="form-group">
        <label for="postalCode" class="form-label">
          {{ t('register.postal_code_label') }}
          <span class="required">*</span>
        </label>
        <input
          id="postalCode"
          v-model="address.postalCode"
          type="text"
          class="form-input"
          :class="{
            error: checks.postalCode.isValid === false,
            valid: isConfirmed(postalCodeMessage),
            loading: checks.postalCode.loading,
          }"
          :placeholder="t('register.postal_code_placeholder')"
          :aria-invalid="checks.postalCode.isValid === false"
          aria-describedby="postal-code-message"
          :disabled="!address.countryId"
          required
          @blur="verification.validatePostalCode()"
          @input="verification.onPostalCodeChange()"
        />
        <FieldMessage id="postal-code-message" :message="postalCodeMessage" />
      </div>

      <div class="form-group">
        <label for="addressLine2" class="form-label">
          {{ t('register.address_line2_label') }}
        </label>
        <input
          id="addressLine2"
          v-model="address.addressLine2"
          type="text"
          class="form-input"
          :class="{ valid: Boolean(address.addressLine2) }"
          :placeholder="t('register.address_line2_placeholder')"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import AppSelect from '@/components/common/AppSelect.vue';
import FieldMessage from '@/components/common/FieldMessage.vue';

const address = defineModel({ type: Object, required: true });

const props = defineProps({
  /** The running address checks, as returned by useAddressVerification. */
  verification: { type: Object, required: true },
  countryOptions: { type: Array, required: true },
  countryError: { type: String, default: '' },
});

const emit = defineEmits(['country-change', 'validate-country']);

const { t } = useI18n();

const checks = computed(() => props.verification.validation.value);
const cityMessage = computed(() => props.verification.cityMessage.value);
const streetMessage = computed(() => props.verification.streetMessage.value);
const postalCodeMessage = computed(
  () => props.verification.postalCodeMessage.value
);

/** A field is marked valid only once the service has confirmed it. */
const isConfirmed = (message) => message?.type === 'success';
</script>
