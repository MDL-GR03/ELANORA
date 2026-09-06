import { defineStore } from 'pinia';
import gitService from '@/api/service/gitService';

export const useProjectStore = defineStore('project', {
  state: () => ({
    currentProject: null,
    projects: [],
    isLoading: false,
    initialized: false,
    loadPromise: null,
    broadcastChannel: null,
  }),

  getters: {
    projectId: (state) => state.currentProject?.project_id ?? null,
    projectName: (state) => state.currentProject?.project_name ?? '',
    projectDescription: (state) =>
      state.currentProject?.project_description ?? '',
    currentPermission: (state) => state.currentProject?.permission ?? null,
    projectList: (state) => state.projects ?? [],
  },

  actions: {
    initBroadcastChannel() {
      if (this.broadcastChannel) return;
      if (typeof window !== 'undefined' && 'BroadcastChannel' in window) {
        this.broadcastChannel = new BroadcastChannel('project-sync');

        // Listen for messages from other tabs
        this.broadcastChannel.onmessage = (event) => {
          if (event.data.type === 'projects-updated') {
            // Update local store with the latest projects
            this.projects = event.data.projects;
            this.sortProjects();
            // Update localStorage
            localStorage.setItem('projects', JSON.stringify(this.projects));
          }
        };
      }
    },

    sortProjects() {
      this.projects = this.projects
        .slice()
        .sort((a, b) => a.project_name.localeCompare(b.project_name));
    },
    initializeFromStorage() {
      this.isLoading = true;
      const savedProjects = localStorage.getItem('projects');
      if (savedProjects) {
        this.projects = JSON.parse(savedProjects);
        this.sortProjects();
      }
      const savedCurrentProject = localStorage.getItem('currentProject');
      if (savedCurrentProject) {
        this.currentProject = JSON.parse(savedCurrentProject);
      }
      this.isLoading = false;
    },
    setCurrentProject(project) {
      this.currentProject = project;
      // Save to localStorage
      localStorage.setItem('currentProject', JSON.stringify(project));
    },
    setProjects(projects) {
      this.projects = projects.slice();
      this.sortProjects();
      this.initialized = true;
      localStorage.setItem('projects', JSON.stringify(this.projects));

      // Broadcast to other tabs with serialized data
      if (this.broadcastChannel) {
        this.broadcastChannel.postMessage({
          type: 'projects-updated',
          projects: JSON.parse(JSON.stringify(this.projects)),
        });
      }
    },
    async ensureProjects() {
      if (this.initialized) return this.projects;
      if (this.loadPromise) return this.loadPromise;
      this.isLoading = true;
      this.loadPromise = gitService
        .listUserProjects()
        .then((response) => {
          this.setProjects(response?.projects || []);
          if (!this.projects.length) this.clearCurrentProject();
          return this.projects;
        })
        .finally(() => {
          this.isLoading = false;
          this.loadPromise = null;
        });
      return this.loadPromise;
    },
    loadCurrentProject() {
      this.isLoading = true;
      const saved = localStorage.getItem('currentProject');
      if (saved) {
        this.currentProject = JSON.parse(saved);
      }
      this.isLoading = false;
    },
    clearCurrentProject() {
      this.currentProject = null;
      localStorage.removeItem('currentProject');
    },
    resetForSession() {
      this.currentProject = null;
      this.projects = [];
      this.initialized = false;
      this.loadPromise = null;
      localStorage.removeItem('currentProject');
      localStorage.removeItem('projects');
    },

    $dispose() {
      if (this.broadcastChannel) {
        this.broadcastChannel.close();
      }
    },
  },
});
