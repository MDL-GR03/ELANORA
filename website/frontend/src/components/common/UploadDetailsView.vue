<template>
  <div class="upload-details">
    <div class="details-section">
      <h3>Upload Information</h3>
      <div class="details-grid">
        <div class="detail-item">
          <label>Contribution:</label>
          <span>#{{ upload.upload_id }}</span>
        </div>
        <div class="detail-item">
          <label>Upload Type:</label>
          <span>{{ formatUploadType(upload.upload_type) }}</span>
        </div>
        <div class="detail-item">
          <label>Status:</label>
          <span
            class="status-badge"
            :class="getStatusClass(upload.merge_status)"
          >
            {{ formatStatus(upload.merge_status) }}
          </span>
        </div>
        <div class="detail-item">
          <label>Uploaded:</label>
          <span>{{ formatDate(upload.uploaded_at) }}</span>
        </div>
        <div class="detail-item">
          <label>Uploaded By:</label>
          <span>{{ upload.uploaded_by || 'Unknown researcher' }}</span>
        </div>
        <div v-if="upload.tested_at" class="detail-item">
          <label>Last Tested:</label>
          <span>{{ formatDate(upload.tested_at) }}</span>
        </div>
      </div>
    </div>

    <div class="details-section">
      <h3>Quality checks</h3>
      <div class="details-grid">
        <div class="detail-item">
          <label>ELAN file structure</label>
          <span>Passed</span>
        </div>
        <div class="detail-item">
          <label>Project naming rules</label>
          <span>Passed</span>
        </div>
        <div class="detail-item">
          <label>Project protocol</label>
          <span>{{ protocolLabel }}</span>
        </div>
      </div>
    </div>

    <div class="details-section">
      <h3>File Changes</h3>
      <div class="file-changes">
        <div v-if="upload.files?.new?.length > 0" class="file-group">
          <h4 class="file-group-title new">
            <span class="file-icon">+</span>
            New Files ({{ upload.files.new.length }})
          </h4>
          <ul class="file-list">
            <li
              v-for="file in upload.files.new"
              :key="file"
              class="file-item new"
            >
              <span class="file-name" :title="file">{{ file }}</span>
            </li>
          </ul>
        </div>

        <div v-if="upload.files?.modified?.length > 0" class="file-group">
          <h4 class="file-group-title modified">
            <span class="file-icon">~</span>
            Modified Files ({{ upload.files.modified.length }})
          </h4>
          <ul class="file-list">
            <li
              v-for="file in upload.files.modified"
              :key="file"
              class="file-item modified"
            >
              <span class="file-name" :title="file">{{ file }}</span>
            </li>
          </ul>
        </div>

        <div v-if="upload.files?.deleted?.length > 0" class="file-group">
          <h4 class="file-group-title deleted">
            <span class="file-icon">-</span>
            Deleted Files ({{ upload.files.deleted.length }})
          </h4>
          <ul class="file-list">
            <li
              v-for="file in upload.files.deleted"
              :key="file"
              class="file-item deleted"
            >
              <span class="file-name" :title="file">{{ file }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <div v-if="upload.conflicted_files?.length > 0" class="details-section">
      <h3>Conflicts</h3>
      <div class="conflicts-info">
        <p class="conflict-summary">
          {{ upload.conflicted_files.length }} files have merge conflicts that
          need resolution.
        </p>
        <ul class="conflict-files">
          <li
            v-for="file in upload.conflicted_files"
            :key="file"
            class="conflict-file"
          >
            <span class="conflict-icon">⚠️</span>
            <span class="file-name" :title="file">{{ file }}</span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  upload: {
    type: Object,
    required: true,
  },
});

const protocolLabel = computed(() => {
  const outcome = props.upload.quality_checks?.protocol;
  if (outcome === 'passed') return 'Passed';
  if (outcome === 'recheck_required')
    return 'Protocol changed; this contribution will be checked again before acceptance';
  if (outcome === 'not_configured') return 'Not configured for this project';
  return 'Not recorded for this older contribution';
});

function formatUploadType(type) {
  const types = {
    pending_upload: 'New Files Only',
    upload_with_modifications: 'With Modifications',
    upload_with_deletions: 'With Deletions',
  };
  return types[type] || type;
}

function formatStatus(status) {
  const statuses = {
    ready_to_merge: 'Ready to Merge',
    needs_resolution: 'Needs Resolution',
    error: 'Error',
    pending_admin_approval: 'Pending Review',
  };
  return statuses[status] || status;
}

function getStatusClass(status) {
  const classes = {
    ready_to_merge: 'ready',
    needs_resolution: 'conflicts',
    error: 'error',
    pending_admin_approval: 'pending',
  };
  return classes[status] || 'pending';
}

function formatDate(dateString) {
  if (!dateString) return 'Unknown';
  return new Date(dateString).toLocaleString();
}
</script>

<style scoped>
.upload-details {
  padding: 20px 0;
}

.details-section {
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.details-section:last-child {
  border-bottom: none;
}

.details-section h3 {
  margin: 0 0 15px;
  color: #2c3e50;
  font-size: 1.2rem;
}

.details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 15px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0; /* Allow flex items to shrink */
}

.detail-item label {
  font-weight: 600;
  color: #666;
  font-size: 0.9rem;
  flex-shrink: 0;
}

.detail-item span {
  color: #2c3e50;
  min-width: 0; /* Allow text to wrap/truncate */
}

/* Branch name specific styling with truncation */
.branch-name {
  font-family: monospace;
  font-size: 0.9rem;
  word-break: break-all;
  overflow-wrap: break-word;
  max-width: 100%;
  display: block;
}

/* Alternative: use ellipsis truncation for very long names */
.branch-name-ellipsis {
  font-family: monospace;
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
  display: block;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 500;
  text-transform: uppercase;
  width: fit-content;
}

.status-badge.ready {
  background: #e8f5e8;
  color: #2e7d32;
}

.status-badge.conflicts {
  background: #fff3e0;
  color: #f57c00;
}

.status-badge.error {
  background: #ffebee;
  color: #d32f2f;
}

.status-badge.pending {
  background: #e3f2fd;
  color: #1976d2;
}

.file-group {
  margin-bottom: 20px;
}

.file-group-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 10px;
  font-size: 1rem;
  font-weight: 600;
}

.file-icon {
  font-weight: bold;
  font-size: 1.2rem;
  flex-shrink: 0;
}

.file-group-title.new {
  color: #2e7d32;
}

.file-group-title.modified {
  color: #f57c00;
}

.file-group-title.deleted {
  color: #d32f2f;
}

.file-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.file-item {
  padding: 8px 12px;
  margin-bottom: 4px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.9rem;
  min-width: 0;
}

.file-item.new {
  background: #e8f5e8;
  border-left: 3px solid #2e7d32;
}

.file-item.modified {
  background: #fff3e0;
  border-left: 3px solid #f57c00;
}

.file-item.deleted {
  background: #ffebee;
  border-left: 3px solid #d32f2f;
}

/* File name styling with proper wrapping */
.file-name {
  word-break: break-all;
  overflow-wrap: break-word;
  display: block;
  max-width: 100%;
}

.conflicts-info {
  background: #fff3e0;
  padding: 15px;
  border-radius: 8px;
  border-left: 4px solid #f57c00;
}

.conflict-summary {
  margin: 0 0 15px;
  font-weight: 500;
  color: #f57c00;
}

.conflict-files {
  list-style: none;
  padding: 0;
  margin: 0;
}

.conflict-file {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px;
  background: white;
  border-radius: 4px;
  margin-bottom: 4px;
  font-family: monospace;
  font-size: 0.9rem;
  min-width: 0;
}

.conflict-icon {
  font-size: 1rem;
  flex-shrink: 0;
  margin-top: 1px; /* Align with text baseline */
}

.tech-details {
  background: #f8f9fa;
  border-radius: 8px;
  overflow-x: auto;
}

.tech-details pre {
  padding: 15px;
  margin: 0;
  font-size: 0.8rem;
  color: #666;
  white-space: pre-wrap;
  word-break: break-all;
  overflow-wrap: break-word;
}

/* Responsive design improvements */
@media (width <= 768px) {
  .details-grid {
    grid-template-columns: 1fr;
  }

  .detail-item {
    padding: 8px 0;
    border-bottom: 1px solid #f0f0f0;
  }

  .detail-item:last-child {
    border-bottom: none;
  }

  .branch-name {
    font-size: 0.8rem;
  }
}

/* Alternative styles if you prefer ellipsis truncation */

/* Uncomment these and change .branch-name to .branch-name-ellipsis in template */

/*
@media (min-width: 769px) {
  .branch-name-ellipsis {
    max-width: 250px;
  }
}

@media (max-width: 768px) {
  .branch-name-ellipsis {
    max-width: 200px;
  }
}
*/
</style>
