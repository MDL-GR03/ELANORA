import axiosInstance from '@api/apiClient.js';

/**
 * Fetch current user info.
 * @returns {Promise<import('axios').AxiosResponse>}
 */
export async function fetchUser() {
  return await axiosInstance.get('/user/me');
}

/**
 * Fetch current user's complete profile including address.
 * @returns {Promise<import('axios').AxiosResponse>}
 */
export async function fetchUserProfile() {
  return await axiosInstance.get('/user/me/profile');
}

/**
 * Fetch all active users.
 * @returns {Promise<import('axios').AxiosResponse>}
 */
export async function fetchActiveUsers() {
  return await axiosInstance.get('/user/active');
}

/** Fetch every institution account for administrator lifecycle management. */
export async function fetchInstitutionAccounts() {
  return await axiosInstance.get('/user/admin/accounts');
}

/** Suspend or restore an institution account. */
export async function setInstitutionAccountStatus(userId, isActive, reason) {
  return await axiosInstance.patch(`/user/admin/accounts/${userId}/status`, {
    is_active: isActive,
    reason,
  });
}

/**
 * Check if a username is available for registration.
 * @param {string} username
 * @returns {Promise<{ available: boolean, message: string }>}
 */
export async function checkUsernameAvailability(username) {
  const response = await axiosInstance.get(
    `/auth/check-username/${encodeURIComponent(username)}`
  );
  return response.data;
}

/**
 * Check if an email is available for registration.
 * @param {string} email
 * @returns {Promise<{ available: boolean, message: string }>}
 */
export async function checkEmailAvailability(email) {
  const response = await axiosInstance.get(
    `/auth/check-email/${encodeURIComponent(email)}`
  );
  return response.data;
}

/**
 * Update current user's profile.
 * @param {Object} profileData - Profile data to update
 * @returns {Promise<import('axios').AxiosResponse>}
 */
export async function updateUserProfile(profileData) {
  return await axiosInstance.put('/user/me/profile', profileData);
}

export async function updateUserAddress(addressData) {
  return await axiosInstance.put('/user/me/address', addressData);
}

/**
 * Change user password.
 * @param {Object} passwordData - Password data with current_password and new_password
 * @returns {Promise<import('axios').AxiosResponse>}
 */
export async function changePassword(passwordData) {
  return await axiosInstance.put('/user/me/password', passwordData);
}
