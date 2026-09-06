import { defineStore } from 'pinia';
import { fetchUser } from '@/api/service/userService';
import {
  login as authLogin,
  logout as authLogout,
} from '@/api/service/authService';
import { useProjectStore } from '@/stores/project';

/* =========================
   Store Definition
   ========================= */
export const useUserStore = defineStore('user', {
  /* =========================
     State
     ========================= */
  state: () => ({
    user: null,
    authState: {
      initialized: false,
      isAuthenticated: false,
      loading: true,
    },
  }),

  /* =========================
     Actions
     ========================= */
  actions: {
    initializeFromStorage() {
      try {
        return this.user;
      } catch (error) {
        console.error('Error initializing user store:', error);
        this.clearAuth();
        return null;
      }
    },
    /**
     * Actively verify authentication with the server.
     */
    async verifyAuthentication() {
      this.authState.loading = true;
      try {
        const userResponse = await fetchUser();
        if (userResponse.data) {
          this.user = userResponse.data;
          this.authState.isAuthenticated = true;
          this.authState.initialized = true;
          return true;
        } else {
          this.clearAuth();
          this.authState.initialized = true;
          return false;
        }
      } catch (error) {
        // Only log error if it's not a 401 (which is expected when not authenticated)
        if (error.response?.status !== 401) {
          console.error('Error verifying authentication:', error);
        } else {
          console.log('User not authenticated (401 response expected)');
        }
        this.clearAuth();
        this.authState.initialized = true;
        return false;
      } finally {
        this.authState.loading = false;
      }
    },
    /**
     * Handles user login.
     * @param {Object} credentials - { login, password }
     */
    async login(credentials) {
      try {
        // First request: authentication
        const response = await authLogin(credentials);

        // Mark as authenticated as soon as login succeeds (cookies set)
        this.authState.isAuthenticated = true;

        try {
          // Second request: fetch user data
          const userResponse = await fetchUser();
          if (userResponse.data) {
            this.user = userResponse.data;
          }
        } catch (userError) {
          // If user data fetch fails, we continue anyway
          // because authentication succeeded (cookies are set)
          console.error('Error fetching user data after login:', userError);
          // Don't re-throw the error
        }

        return response.data;
      } catch (error) {
        console.error('Login error:', error);
        throw error;
      }
    },
    /**
     * Log user out (with API call).
     */
    async logout() {
      try {
        const csrfToken = document.cookie
          .split('; ')
          .find((row) => row.startsWith('elanora_csrf='))
          ?.split('=')[1];
        if (csrfToken) {
          await authLogout(csrfToken);
        }
      } catch (error) {
        console.error('Logout error:', error);
      } finally {
        this.clearAuth();
        useProjectStore().resetForSession();
      }
    },
    /**
     * Clear all authentication data.
     */
    clearAuth() {
      this.user = null;
      this.authState.isAuthenticated = false;
      const csrfCookieName = 'elanora_csrf';
      if (document.cookie.indexOf(csrfCookieName) >= 0) {
        document.cookie = `${csrfCookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
      }
    },
  },

  /* =========================
     Getters
     ========================= */
  getters: {
    /**
     * Frontend-only check for authentication check.
     */
    isAuthenticated() {
      if (!this.authState.isAuthenticated) return false;
      const hasCSRFCookie = document.cookie.includes('elanora_csrf');
      return !!this.user?.user_id && hasCSRFCookie;
    },
  },
});
