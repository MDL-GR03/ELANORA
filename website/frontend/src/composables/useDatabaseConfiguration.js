/**
 * Composable for managing database configuration settings.
 * 
 * This composable provides methods for:
 * - Loading database configuration
 * - Updating configuration with safeguards
 * - Validating changes
 * - Checking which changes require restart
 */

import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { useApi } from '@api';

/**
 * Settings that require application restart to take effect.
 */
export const RESTART_REQUIRED_SETTINGS = [
  'max_file_size_mb',
  'max_users',
];

/**
 * Default database configuration values.
 */
export const DEFAULT_DATABASE_CONFIG = {
  max_file_size_mb: 100.00,
  max_users: 1000,
  timezone: 'UTC',
  default_language: 'en',
};

/**
 * Main composable for database configuration.
 */
export function useDatabaseConfiguration() {
  const { t } = useI18n();
  const api = useApi();

  // Reactive state
  const databaseConfig = ref(null);
  const isLoading = ref(false);
  const error = ref(null);
  const changes = ref({});
  const restartRequired = ref(false);

  // Computed properties
  const hasChanges = computed(() => {
    return Object.keys(changes.value).length > 0;
  });

  const changesRequiringRestart = computed(() => {
    return Object.keys(changes.value).filter(key => 
      RESTART_REQUIRED_SETTINGS.includes(key)
    );
  });

  const warnings = computed(() => {
    const warnings = [];
    
    if (changesRequiringRestart.value.length > 0) {
      warnings.push({
        type: 'warning',
        message: t('database.warning'),
        details: t('database.restartRequired', {
          settings: changesRequiringRestart.value.join(', '),
        }),
      });
    }
    
    return warnings;
  });

  // Methods
  /**
   * Load the current database configuration.
   */
  const loadDatabaseConfiguration = async () => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await api.get('/api/v1/instance');
      databaseConfig.value = {
        max_file_size_mb: response.data.max_file_size_mb,
        max_users: response.data.max_users,
        timezone: response.data.timezone,
        default_language: response.data.default_language,
        is_active: response.data.is_active,
      };
      return databaseConfig.value;
    } catch (err) {
      error.value = err;
      console.error('Failed to load database configuration:', err);
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  /**
   * Update database configuration.
   */
  const updateDatabaseConfiguration = async (configData) => {
    isLoading.value = true;
    error.value = null;
    
    try {
      // Check which changes require restart
      const restartSettings = Object.keys(configData).filter(key => 
        RESTART_REQUIRED_SETTINGS.includes(key)
      );
      restartRequired.value = restartSettings.length > 0;
      
      const response = await api.patch('/api/v1/instance/settings', configData);
      databaseConfig.value = {
        ...databaseConfig.value,
        ...configData,
      };
      changes.value = {};
      
      return {
        data: response.data,
        restartRequired: restartRequired.value,
      };
    } catch (err) {
      error.value = err;
      console.error('Failed to update database configuration:', err);
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  /**
   * Track a change to a configuration setting.
   */
  const trackChange = (key, value) => {
    changes.value[key] = value;
    
    // Check if this change requires restart
    if (RESTART_REQUIRED_SETTINGS.includes(key)) {
      restartRequired.value = true;
    }
  };

  /**
   * Clear all tracked changes.
   */
  const clearChanges = () => {
    changes.value = {};
    restartRequired.value = false;
  };

  /**
   * Get the value of a configuration setting.
   */
  const getConfigValue = (key) => {
    if (databaseConfig.value && key in databaseConfig.value) {
      return databaseConfig.value[key];
    }
    if (DEFAULT_DATABASE_CONFIG[key] !== undefined) {
      return DEFAULT_DATABASE_CONFIG[key];
    }
    return null;
  };

  /**
   * Validate a configuration value.
   */
  const validateConfigValue = (key, value) => {
    switch (key) {
      case 'max_file_size_mb':
        return value > 0 && value <= 10000; // Max 10GB
      case 'max_users':
        return value > 0 && value <= 100000; // Max 100k users
      case 'timezone':
        return value.length <= 50; // Reasonable length
      case 'default_language':
        return /^[a-z]{2,3}$/.test(value); // ISO 639-1 or 639-2
      case 'is_active':
        return typeof value === 'boolean';
      default:
        return true;
    }
  };

  /**
   * Validate all changed configuration values.
   */
  const validateAllChanges = () => {
    const errors = [];
    
    for (const [key, value] of Object.entries(changes.value)) {
      if (!validateConfigValue(key, value)) {
        errors.push({
          key,
          message: t('database.invalidValue', { setting: key, value }),
        });
      }
    }
    
    return {
      isValid: errors.length === 0,
      errors,
    };
  };

  /**
   * Check if a specific setting requires restart.
   */
  const requiresRestart = (key) => {
    return RESTART_REQUIRED_SETTINGS.includes(key);
  };

  return {
    // State
    databaseConfig,
    isLoading,
    error,
    changes,
    restartRequired,
    
    // Computed
    hasChanges,
    changesRequiringRestart,
    warnings,
    
    // Methods
    loadDatabaseConfiguration,
    updateDatabaseConfiguration,
    trackChange,
    clearChanges,
    getConfigValue,
    validateConfigValue,
    validateAllChanges,
    requiresRestart,
  };
}
