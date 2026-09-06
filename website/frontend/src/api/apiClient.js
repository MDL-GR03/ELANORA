/** Shared HTTP client with cookie, CSRF, and single-flight session recovery. */

import axios from 'axios';

import { createAuthRecovery } from './authRecovery';

const baseURL = import.meta.env.VITE_API_URL || '/api/v1';
const clientOptions = {
  baseURL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
};

const axiosInstance = axios.create(clientOptions);

// Refreshes deliberately bypass the application response interceptor. A 401
// from this client must never attempt to refresh itself.
const refreshClient = axios.create(clientOptions);

function getCsrfToken() {
  return document.cookie
    .split('; ')
    .find((row) => row.startsWith('elanora_csrf='))
    ?.split('=')[1];
}

function redirectAfterSessionExpiry() {
  const currentLocation = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  if (window.location.pathname !== '/') {
    localStorage.setItem('redirectTo', currentLocation);
    window.location.href = '/';
  }
}

const authRecovery = createAuthRecovery({
  refresh: () => {
    const csrfToken = getCsrfToken();
    return refreshClient.post(
      '/auth/refresh',
      {},
      csrfToken ? { headers: { 'X-CSRF-Token': csrfToken } } : undefined
    );
  },
  onFailure: redirectAfterSessionExpiry,
});

function isSessionEndpoint(url = '') {
  return ['/auth/login', '/auth/logout', '/auth/refresh'].some((endpoint) =>
    url.includes(endpoint)
  );
}

axiosInstance.interceptors.request.use((config) => {
  if (
    ['post', 'put', 'delete', 'patch'].includes(config.method?.toLowerCase())
  ) {
    const csrfToken = getCsrfToken();

    if (csrfToken) {
      config.headers['X-CSRF-Token'] = csrfToken;
    }
  }
  return config;
});

axiosInstance.interceptors.response.use(
  (response) => {
    const url = response.config?.url || '';
    if (url.includes('/auth/login') || url.includes('/auth/refresh')) {
      authRecovery.reset();
    }
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    if (!originalRequest || isSessionEndpoint(originalRequest.url)) {
      return Promise.reject(error);
    }

    const needsCsrfRecovery =
      error.response?.status === 403 &&
      error.response?.data?.detail === 'CSRF token missing or invalid.' &&
      !originalRequest._csrfRetry;
    const needsAuthenticationRecovery =
      error.response?.status === 401 && !originalRequest._authRetry;

    if (!needsCsrfRecovery && !needsAuthenticationRecovery) {
      return Promise.reject(error);
    }

    if (needsCsrfRecovery) originalRequest._csrfRetry = true;
    if (needsAuthenticationRecovery) originalRequest._authRetry = true;

    try {
      await authRecovery.attempt();
      return axiosInstance(originalRequest);
    } catch (refreshError) {
      return Promise.reject(refreshError);
    }
  }
);

export default axiosInstance;
