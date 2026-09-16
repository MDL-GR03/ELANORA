import { ref, toValue } from 'vue';

/** How long the researcher reads the "you already have an account" notice. */
export const EXISTING_ACCOUNT_REDIRECT_DELAY = 2000;

/** Turn the form's address into the payload the API expects, or null. */
export function addressPayload(address, countries) {
  if (
    !address?.streetName ||
    !address?.cityName ||
    !address?.postalCode ||
    !address?.countryId
  ) {
    return null;
  }
  const country = countries.find(
    (candidate) => candidate.country_id === address.countryId
  );
  return {
    street_name: address.streetName,
    street_number: address.streetNumber || null,
    city_name: address.cityName,
    country_code: address.countryId,
    country_name: country?.country_name || '',
    postal_code: address.postalCode,
    address_line_2: address.addressLine2 || null,
  };
}

/**
 * Validate an invitation and create the account it was issued for.
 *
 * Registration on ELANORA is by invitation only: an account exists because
 * someone already in the institution asked for it. Validating a code never
 * grants project access by itself, and someone who already has an account is
 * sent to sign in instead, where the invitation can be reviewed as themselves.
 */
export function useInvitationRegistration({
  form,
  countries,
  translate,
  invitationApi,
  authApi,
  eventMessages,
  router,
  validateAllFields,
  validationErrors,
  usernameAvailable,
  emailAvailable,
  reportError,
}) {
  const invitationCode = ref('');
  const invitationValid = ref(false);
  const invitationValidating = ref(false);
  const invitationError = ref('');
  const invitationInfo = ref(null);
  const loading = ref(false);

  async function validateInvitationCode() {
    if (!invitationCode.value) {
      invitationError.value = translate('register.invitation_code_required');
      invitationValid.value = false;
      return;
    }

    invitationValidating.value = true;
    invitationError.value = '';

    try {
      const response = await invitationApi.validateInvitation(
        invitationCode.value
      );
      if (!response.data.valid) {
        invitationValid.value = false;
        invitationError.value =
          response.data.message || translate('register.invitation_invalid');
        return;
      }

      if (response.data.user_exists) {
        eventMessages.addMessage(
          translate('register.invitation_existing_user'),
          'info'
        );
        setTimeout(() => {
          router.push({ name: 'LoginPage' });
        }, EXISTING_ACCOUNT_REDIRECT_DELAY);
        return;
      }

      invitationValid.value = true;
      invitationInfo.value = response.data.invitation;

      // The invitation decides which address the account is created for, so
      // the researcher cannot register a different one by editing the field.
      const invitedEmail = invitationInfo.value?.receiver_email || '';
      toValue(form).email = invitedEmail;
      toValue(form).confirmEmail = invitedEmail;

      eventMessages.addMessage(
        translate('register.invitation_valid'),
        'success'
      );
    } catch (error) {
      invitationValid.value = false;
      invitationError.value =
        error.response?.data?.detail ||
        translate('register.invitation_validation_error');
    } finally {
      invitationValidating.value = false;
    }
  }

  /** What stops this form from being submitted, or an empty string. */
  function submissionRefusal() {
    validateAllFields();
    if (Object.values(toValue(validationErrors)).some(Boolean)) {
      return 'register.please_fix_errors';
    }
    const fields = toValue(form);
    if (fields.password !== fields.confirmPassword) {
      return 'register.passwords_no_match';
    }
    if (fields.email !== fields.confirmEmail) {
      return 'register.emails_no_match';
    }
    if (toValue(usernameAvailable) === false) return 'register.username_taken';
    if (toValue(emailAvailable) === false) return 'register.email_taken';
    return '';
  }

  async function register() {
    const refusal = submissionRefusal();
    if (refusal) {
      eventMessages.addMessage(translate(refusal), 'error');
      return;
    }

    loading.value = true;
    const fields = toValue(form);
    try {
      const response = await authApi.registerWithInvitation({
        invitation_code: invitationCode.value,
        first_name: fields.firstName,
        last_name: fields.lastName,
        username: fields.username,
        email: fields.email,
        password: fields.password,
        phone_number: fields.phoneNumber || null,
        affiliation: fields.affiliation,
        department: fields.department,
        address: addressPayload(fields.address, toValue(countries)),
      });

      if (response.data?.requires_activation) {
        eventMessages.addMessage(
          translate('register.success_needs_verification'),
          'success'
        );
        router.push({
          name: 'EmailVerificationPage',
          query: { email: fields.email, freshCode: 'true' },
        });
        return;
      }

      eventMessages.addMessage(translate('register.success'), 'success');
      router.push({ name: 'LoginPage' });
    } catch (error) {
      reportError('Registration error', error);
      eventMessages.addMessage(
        error?.response?.data?.detail || translate('register.error'),
        'error'
      );
    } finally {
      loading.value = false;
    }
  }

  return {
    invitationCode,
    invitationValid,
    invitationValidating,
    invitationError,
    invitationInfo,
    loading,
    validateInvitationCode,
    register,
  };
}
