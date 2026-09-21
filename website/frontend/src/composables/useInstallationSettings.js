/**
 * Composable for managing installation settings.
 *
 * This composable provides methods for:
 * - Loading instance configuration
 * - Updating branding settings
 * - Updating general system settings
 * - Tracking changes and validation
 */

import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { useApi } from '@api';

/**
 * Default branding colors matching CSS variables.
 */
export const DEFAULT_BRANDING = {
  primary_color: '#2563eb',
  secondary_color: '#0f766e',
  accent_color: '#d97706',
};

/**
 * Main composable for installation settings.
 */
export function useInstallationSettings() {
  const { t } = useI18n();
  const api = useApi();

  // Reactive state
  const instanceSettings = ref(null);
  const brandingSettings = ref(null);
  const isLoading = ref(false);
  const error = ref(null);
  const changes = ref({});

  // Computed properties
  const hasChanges = computed(() => {
    return Object.keys(changes.value).length > 0;
  });

  const isBrandingChanged = computed(() => {
    return Object.keys(changes.value).some((key) =>
      ['primary_color', 'secondary_color', 'accent_color'].includes(key)
    );
  });

  const isGeneralSettingsChanged = computed(() => {
    return Object.keys(changes.value).some(
      (key) =>
        !['primary_color', 'secondary_color', 'accent_color'].includes(key)
    );
  });

  // Methods
  /**
   * Load the current instance configuration.
   */
  const loadInstanceSettings = async () => {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await api.get('/api/v1/instance');
      instanceSettings.value = response.data;
      brandingSettings.value = {
        instance_name: response.data.instance_name,
        institution_name: response.data.institution_name,
        contact_email: response.data.contact_email,
        primary_color: response.data.primary_color,
        secondary_color: response.data.secondary_color,
        accent_color: response.data.accent_color,
      };
      return response.data;
    } catch (err) {
      error.value = err;
      console.error('Failed to load instance settings:', err);
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  /**
   * Update branding settings.
   */
  const updateBranding = async (brandingData) => {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await api.patch(
        '/api/v1/instance/branding',
        brandingData
      );
      brandingSettings.value = {
        ...brandingSettings.value,
        ...brandingData,
      };
      changes.value = {};
      return response.data;
    } catch (err) {
      error.value = err;
      console.error('Failed to update branding:', err);
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  /**
   * Update general system settings.
   */
  const updateGeneralSettings = async (settingsData) => {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await api.patch(
        '/api/v1/instance/settings',
        settingsData
      );
      instanceSettings.value = {
        ...instanceSettings.value,
        ...settingsData,
      };
      changes.value = {};
      return response.data;
    } catch (err) {
      error.value = err;
      console.error('Failed to update general settings:', err);
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  /**
   * Track a change to a setting.
   */
  const trackChange = (key, value) => {
    changes.value[key] = value;
  };

  /**
   * Clear all tracked changes.
   */
  const clearChanges = () => {
    changes.value = {};
  };

  /**
   * Get the value of a setting, falling back to defaults.
   */
  const getSetting = (key) => {
    if (instanceSettings.value && key in instanceSettings.value) {
      return instanceSettings.value[key];
    }
    if (brandingSettings.value && key in brandingSettings.value) {
      return brandingSettings.value[key];
    }
    if (DEFAULT_BRANDING[key]) {
      return DEFAULT_BRANDING[key];
    }
    return null;
  };

  /**
   * Validate a hex color.
   */
  const isValidHexColor = (color) => {
    return /^#[0-9A-Fa-f]{6}$/.test(color);
  };

  /**
   * Validate all branding colors.
   */
  const validateBrandingColors = () => {
    const colors = [
      changes.value.primary_color,
      changes.value.secondary_color,
      changes.value.accent_color,
    ].filter((c) => c !== undefined);

    return colors.every((color) => isValidHexColor(color));
  };

  return {
    // State
    instanceSettings,
    brandingSettings,
    isLoading,
    error,
    changes,

    // Computed
    hasChanges,
    isBrandingChanged,
    isGeneralSettingsChanged,

    // Methods
    loadInstanceSettings,
    updateBranding,
    updateGeneralSettings,
    trackChange,
    clearChanges,
    getSetting,
    isValidHexColor,
    validateBrandingColors,
  };
}
