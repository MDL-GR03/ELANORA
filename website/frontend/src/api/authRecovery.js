/**
 * Coordinate session refreshes across concurrent failed API requests.
 *
 * A failed refresh latches recovery until an explicit reset (normally a
 * successful login). This prevents polling requests from creating a refresh
 * storm when the refresh cookie is absent or expired.
 *
 * @param {{refresh: () => Promise<unknown>, onFailure: (error: unknown) => void}} options
 */
export function createAuthRecovery({ refresh, onFailure }) {
  let activeAttempt = null;
  let blockedError = null;

  return {
    attempt() {
      if (blockedError) return Promise.reject(blockedError);

      if (!activeAttempt) {
        activeAttempt = Promise.resolve()
          .then(refresh)
          .catch((error) => {
            blockedError = error;
            onFailure(error);
            throw error;
          })
          .finally(() => {
            activeAttempt = null;
          });
      }

      return activeAttempt;
    },

    reset() {
      blockedError = null;
    },
  };
}
