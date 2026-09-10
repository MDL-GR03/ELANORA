import axiosInstance from '@/api/apiClient';

const GIT_PREFIX = '/git';
const gitService = {
  // Check if Git is available
  async checkGit() {
    const { data } = await axiosInstance.get(`${GIT_PREFIX}/check`);
    return data;
  },
  // List all projects for the instance
  async listProjects() {
    const { data } = await axiosInstance.get(`${GIT_PREFIX}/projects`);
    return data;
  },

  // List projects accessible to the current user
  async listUserProjects() {
    const { data } = await axiosInstance.get(`${GIT_PREFIX}/user-projects`);
    return data;
  },

  // Create a new project
  async createProject(projectData) {
    const { data } = await axiosInstance.post(
      `${GIT_PREFIX}/projects/create`,
      projectData
    );
    return data;
  },

  // Commit changes to a project
  async commitChanges(projectName, commitMessage, userName) {
    const payload = {
      commit_message: commitMessage,
      user_name: userName,
    };
    const { data } = await axiosInstance.post(
      `${GIT_PREFIX}/projects/${encodeURIComponent(projectName)}/commit`,
      payload
    );
    return data;
  },

  // Upload ELAN files to a project
  async uploadElanFiles(
    projectId,
    files,
    userName,
    correctionCaseId = null,
    researchContext = {},
    requestConfig = {}
  ) {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    formData.append('user_name', userName);
    if (correctionCaseId) {
      formData.append('correction_case_id', correctionCaseId);
    }
    if (researchContext.topicId) {
      formData.append('research_topic_id', researchContext.topicId);
    }
    if (researchContext.proposedTopicName) {
      formData.append('proposed_topic_name', researchContext.proposedTopicName);
    }
    if (researchContext.summary) {
      formData.append('contribution_summary', researchContext.summary);
    }

    const { data } = await axiosInstance.post(
      `${GIT_PREFIX}/projects/${encodeURIComponent(projectId)}/upload`,
      formData,
      {
        ...requestConfig,
        headers: {
          ...requestConfig.headers,
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return data;
  },

  // Get all branches for a project
  async getBranches(projectName) {
    const { data } = await axiosInstance.get(
      `${GIT_PREFIX}/projects/${encodeURIComponent(projectName)}/branches`
    );
    return data;
  },

  // Resolve conflicts and merge a branch
  async getPendingUploadsWithStatus(projectName) {
    const { data } = await axiosInstance.get(
      `${GIT_PREFIX}/projects/${encodeURIComponent(projectName)}/admin/pending-uploads`
    );
    return data;
  },

  async getAcceptedProjectHistory(projectName) {
    const { data } = await axiosInstance.get(
      `${GIT_PREFIX}/projects/${encodeURIComponent(projectName)}/accepted-history`
    );
    return data;
  },

  async getCurrentProjectRevisionHealth(projectName) {
    const { data } = await axiosInstance.get(
      `${GIT_PREFIX}/projects/${encodeURIComponent(projectName)}/accepted-history/health`
    );
    return data;
  },

  async recoverCurrentProjectRevision(projectName, payload) {
    const { data } = await axiosInstance.post(
      `${GIT_PREFIX}/projects/${encodeURIComponent(projectName)}/accepted-history/recover`,
      payload
    );
    return data;
  },

  async previewProjectVersionRestore(projectName, targetCommit) {
    const { data } = await axiosInstance.post(
      `${GIT_PREFIX}/projects/${encodeURIComponent(projectName)}/accepted-history/preview`,
      { target_commit: targetCommit }
    );
    return data;
  },

  async restoreProjectVersion(projectName, payload) {
    const { data } = await axiosInstance.post(
      `${GIT_PREFIX}/projects/${encodeURIComponent(projectName)}/accepted-history/restore`,
      payload
    );
    return data;
  },

  async updateContributionPolicy(projectId, autoAcceptNewFiles) {
    const { data } = await axiosInstance.put(
      `${GIT_PREFIX}/projects/${encodeURIComponent(projectId)}/contribution-policy`,
      { auto_accept_new_files: autoAcceptNewFiles }
    );
    return data;
  },

  async adminTestMerge(projectName, branchName) {
    const { data } = await axiosInstance.post(
      `${GIT_PREFIX}/projects/${encodeURIComponent(projectName)}/admin/pending-uploads/${encodeURIComponent(branchName)}/test`
    );
    return data;
  },

  async getEafReview(projectName, branchName, filename) {
    const { data } = await axiosInstance.get(
      `${GIT_PREFIX}/projects/${encodeURIComponent(projectName)}/admin/pending-uploads/${encodeURIComponent(branchName)}/eaf-review`,
      { params: { filename } }
    );
    return data;
  },

  async adminCompleteMerge(projectName, branchName, resolutionStrategy) {
    const { data } = await axiosInstance.post(
      `${GIT_PREFIX}/projects/${encodeURIComponent(projectName)}/admin/pending-uploads/${encodeURIComponent(branchName)}/merge`,
      { resolution_strategy: resolutionStrategy }
    );
    return data;
  },

  async dismissDuplicateUpload(projectName, uploadId) {
    const { data } = await axiosInstance.delete(
      `${GIT_PREFIX}/projects/${encodeURIComponent(projectName)}/admin/pending-uploads/${encodeURIComponent(uploadId)}/duplicate`
    );
    return data;
  },

  async declinePendingUpload(projectName, uploadId, reason) {
    const { data } = await axiosInstance.post(
      `${GIT_PREFIX}/projects/${encodeURIComponent(projectName)}/admin/pending-uploads/${encodeURIComponent(uploadId)}/decline`,
      { reason }
    );
    return data;
  },

  async setContributionResearchTopic(projectName, uploadId, decision) {
    const { data } = await axiosInstance.put(
      `${GIT_PREFIX}/projects/${encodeURIComponent(projectName)}/admin/pending-uploads/${encodeURIComponent(uploadId)}/research-topic`,
      decision
    );
    return data;
  },

  // List files in a project (recursive structure)
  async listProjectFiles(projectName, includeMedia = false) {
    const params = includeMedia ? { include_media: true } : {};
    const { data } = await axiosInstance.get(
      `/git/projects/${encodeURIComponent(projectName)}/files`,
      { params }
    );
    return data;
  },

  // Initialize a project from an existing folder with upload
  async initProjectFromFolderUpload({ project_name, description, files }) {
    const formData = new FormData();
    formData.append('project_name', project_name);
    formData.append(
      'description',
      !description || description === 'undefined' ? '' : description
    );

    files.forEach((file) => {
      formData.append('files', file, file.name);
    });

    const { data } = await axiosInstance.post(
      `/git/projects/init-from-folder-upload`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return data;
  },

  // Synchronize the project (apply changes to DB)
  async synchronizeProject(projectName) {
    const { data } = await axiosInstance.post(
      `/git/projects/${encodeURIComponent(projectName)}/synchronize`
    );
    return data;
  },

  // Check if the project is in sync (preview changes)
  async checkSyncStatus(projectName) {
    const { data } = await axiosInstance.get(
      `/git/projects/${encodeURIComponent(projectName)}/synchronize/check`
    );
    return data;
  },

  async getSynchronizationOperations(projectName) {
    const { data } = await axiosInstance.get(
      `/git/projects/${encodeURIComponent(projectName)}/synchronize/operations`
    );
    return data;
  },

  async recoverSynchronizationOperation(projectName, operationId) {
    const { data } = await axiosInstance.post(
      `/git/projects/${encodeURIComponent(projectName)}/synchronize/operations/${encodeURIComponent(operationId)}/recover`
    );
    return data;
  },

  // Delete a project
  async deleteProject(projectName) {
    const { data } = await axiosInstance.delete(
      `/git/projects/${encodeURIComponent(projectName)}`
    );
    return data;
  },

  // Edit a project
  async editProject(oldProjectName, newProjectName, newProjectDescription) {
    const { data } = await axiosInstance.post(
      `/git/projects/${encodeURIComponent(oldProjectName)}/edit`,
      {
        new_project_name: newProjectName,
        new_project_description: newProjectDescription,
      }
    );
    return data;
  },

  // Discard all local changes and reset to remote master
  async discardLocalChanges(projectName) {
    const { data } = await axiosInstance.post(
      `/git/projects/${encodeURIComponent(projectName)}/discard-local-changes`
    );
    return data;
  },

  // Restore the project from backup
  async restoreFromBackup(projectName) {
    const { data } = await axiosInstance.post(
      `/git/projects/${encodeURIComponent(projectName)}/restore-from-backup`
    );
    return data;
  },

  // Decline the backup for a project
  async declineBackup(projectName) {
    const { data } = await axiosInstance.post(
      `/git/projects/${encodeURIComponent(projectName)}/decline-backup`
    );
    return data;
  },
  // Rename a single file
  async renameFile(projectName, elanId, newFilename) {
    const formData = new FormData();
    formData.append('elan_id', elanId);
    formData.append('new_filename', newFilename);

    const response = await axiosInstance.post(
      `${GIT_PREFIX}/projects/${projectName}/rename-file`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  // Rename multiple files
  async renameFiles(projectName, renames) {
    const response = await axiosInstance.post(
      `${GIT_PREFIX}/projects/${projectName}/rename-files`,
      {
        renames: renames,
      }
    );
    return response.data;
  },
};

export default gitService;
