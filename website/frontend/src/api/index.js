/** Barrel export for the @api alias used by composables. */

import axiosInstance from './apiClient';

export function useApi() {
  return axiosInstance;
}

export { default } from './apiClient';
