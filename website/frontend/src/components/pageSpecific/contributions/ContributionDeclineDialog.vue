<template>
  <div
    v-if="upload"
    class="modal-overlay"
    role="presentation"
    @click.self="requestClose"
  >
    <form
      ref="dialogElement"
      class="modal-content decline-modal"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="titleId"
      tabindex="-1"
      @submit.prevent="submit"
      @click.stop
    >
      <div class="modal-header">
        <div>
          <span class="modal-eyebrow">{{
            t('contributionWorkspace.decline.eyebrow', { id: upload.upload_id })
          }}</span>
          <h2 :id="titleId">{{ t('contributionWorkspace.decline.title') }}</h2>
        </div>
        <button
          type="button"
          class="close-btn"
          :aria-label="t('common.close')"
          :disabled="busy"
          @click="requestClose"
        >
          <font-awesome-icon icon="fa-solid fa-xmark" />
        </button>
      </div>
      <div class="modal-body decline-modal-body">
        <p>{{ t('contributionWorkspace.decline.warning') }}</p>
        <label :for="reasonId">{{
          t('contributionWorkspace.decline.reasonLabel')
        }}</label>
        <textarea
          :id="reasonId"
          v-model="reason"
          rows="5"
          maxlength="1000"
          required
          minlength="3"
          :placeholder="t('contributionWorkspace.decline.reasonPlaceholder')"
        ></textarea>
        <div class="decline-modal-actions">
          <button
            type="button"
            class="action-btn view-btn"
            :disabled="busy"
            @click="requestClose"
          >
            {{ t('common.cancel') }}
          </button>
          <button
            type="submit"
            class="action-btn decline-btn"
            :disabled="!canSubmit"
          >
            {{
              busy
                ? t('contributionWorkspace.decline.submitting')
                : t('contributionWorkspace.decline.submit')
            }}
          </button>
        </div>
      </div>
    </form>
  </div>
</template>

<script setup>
import { computed, ref, useId, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useModalDialog } from '@/composables/useModalDialog';

// The contribution being declined is passed in explicitly. It is never shared
// with other page state, so nothing else can change which contribution a
// terminal decision applies to while the dialog is open.
const props = defineProps({
  upload: { type: Object, default: null },
  busy: { type: Boolean, default: false },
});
const emit = defineEmits(['decline', 'close']);

const MINIMUM_REASON_LENGTH = 3;

const { t } = useI18n();
const dialogElement = ref(null);
const reason = ref('');
const generatedId = useId();
const titleId = `decline-title-${generatedId}`;
const reasonId = `decline-reason-${generatedId}`;

const canSubmit = computed(
  () => !props.busy && reason.value.trim().length >= MINIMUM_REASON_LENGTH
);

watch(
  () => props.upload?.upload_id,
  () => {
    reason.value = '';
  }
);

function requestClose() {
  // A decline in flight cannot be abandoned half-way.
  if (!props.busy) emit('close');
}

function submit() {
  if (canSubmit.value) emit('decline', reason.value.trim());
}

useModalDialog(dialogElement, {
  onClose: requestClose,
  isOpen: () => Boolean(props.upload),
  initialFocus: dialogElement,
});
</script>
