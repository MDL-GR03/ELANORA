import { defineStore } from 'pinia';
import effectiveNamingStandardApi from '@/api/service/effectiveNamingStandard.js';
import { reportClientError } from '@/utils/errorDiagnostics';

export const useEffectiveStandardStore = defineStore('effectiveStandard', {
  state: () => ({
    locations: [],
    effectiveStandards: {},
    isLoading: false,
    error: '',
    // Track ongoing requests with unique keys
    ongoingRequests: new Set(),
  }),
  actions: {
    async fetchLocations() {
      if (this.isLoading) {
        return;
      }
      this.isLoading = true;
      try {
        const { data } =
          await effectiveNamingStandardApi.getEffectiveStandardsLocations();
        this.locations = data.locations || [];
      } catch (err) {
        reportClientError('Error fetching locations', err);
        this.error = 'Failed to load locations.';
      } finally {
        this.isLoading = false;
      }
    },
    async fetchEffectiveStandards(projectId, locationId, fileTypeIds = []) {
      if (!locationId) return;

      // Create unique key for this request
      const requestKey = `${projectId}-${locationId}`;

      // Prevent duplicate calls
      if (this.ongoingRequests.has(requestKey)) {
        return;
      }

      // Mark as ongoing
      this.ongoingRequests.add(requestKey);

      try {
        const { data } = await effectiveNamingStandardApi.getEffectiveStandards(
          projectId,
          locationId
        );
        const standardsMap = {};
        for (const eff of data.effective_standards) {
          standardsMap[eff.project_file_type_id] = eff.naming_standard_id;
        }
        for (const fileTypeId of fileTypeIds) {
          if (!(fileTypeId in standardsMap)) {
            standardsMap[fileTypeId] = '';
          }
        }
        this.effectiveStandards[locationId] = standardsMap;
        this.error = '';
      } catch (err) {
        reportClientError('Error fetching effective standards', err);
        this.error = 'Failed to load effective standards.';
      } finally {
        // Always remove from ongoing requests
        this.ongoingRequests.delete(requestKey);
      }
    },
    async assignEffectiveStandard(
      projectId,
      fileTypeId,
      standardId,
      locationId
    ) {
      await effectiveNamingStandardApi.assignEffectiveStandard(
        projectId,
        fileTypeId,
        standardId,
        locationId
      );
      if (!this.effectiveStandards[locationId])
        this.effectiveStandards[locationId] = {};
      this.effectiveStandards[locationId][fileTypeId] = standardId;

      // Clear the ongoing request flag if we need to refetch
      const requestKey = `${projectId}-${locationId}`;
      this.ongoingRequests.delete(requestKey);
    },
    async unassignEffectiveStandard(projectId, fileTypeId, locationId) {
      await effectiveNamingStandardApi.unassignEffectiveStandard(
        projectId,
        fileTypeId,
        locationId
      );
      if (!this.effectiveStandards[locationId])
        this.effectiveStandards[locationId] = {};
      this.effectiveStandards[locationId][fileTypeId] = '';

      // Clear the ongoing request flag if we need to refetch
      const requestKey = `${projectId}-${locationId}`;
      this.ongoingRequests.delete(requestKey);
    },
  },
});
