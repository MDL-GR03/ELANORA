import { computed, ref } from 'vue';

import {
  archiveProtocolVersion,
  deleteProtocolDraft,
  listComplianceScans,
  listProtocols,
  pinProtocolVersion,
  publishProtocolVersion,
  purgeProtocolVersion,
  runComplianceScan,
} from '@/api/service/protocolService';
import reviewService from '@/api/service/reviewService';
import { apiErrorMessage } from '@/utils/apiError';

/**
 * A project's protocols, their versions and compliance scans, with the
 * lifecycle actions a protocol manager takes on them. Destructive actions ask
 * for confirmation first and resolve to whether they happened.
 */
export function useProtocolLibrary({ projectId, translate, notify, confirm }) {
  const protocols = ref([]);
  const scans = ref([]);
  const loading = ref(true);
  const scanning = ref(false);
  const error = ref('');

  const latestScan = computed(() => scans.value[0] ?? null);

  function fail(reason) {
    error.value = apiErrorMessage(
      reason,
      translate,
      translate('protocols.errors.unexpected')
    );
  }

  async function attempt(action) {
    error.value = '';
    try {
      await action();
      return true;
    } catch (reason) {
      fail(reason);
      return false;
    }
  }

  async function load() {
    loading.value = true;
    await attempt(async () => {
      const [protocolList, scanList] = await Promise.all([
        listProtocols(projectId.value),
        listComplianceScans(projectId.value),
      ]);
      protocols.value = protocolList.data;
      scans.value = scanList.data;
    });
    loading.value = false;
  }

  function confirmFor(kind, protocol, version, confirmText) {
    return confirm({
      title: translate(`protocols.confirm.${kind}.title`),
      message: translate(`protocols.confirm.${kind}.message`, {
        number: version.version_number,
        name: protocol.name,
      }),
      confirmText,
      cancelText: translate(`protocols.confirm.${kind}.cancel`),
      tone: 'danger',
    });
  }

  function publish(version) {
    return attempt(async () => {
      await publishProtocolVersion(
        projectId.value,
        version.protocol_version_id
      );
      notify(translate('protocols.messages.published'));
      await load();
    });
  }

  async function removeDraft(protocol, version) {
    const confirmed = await confirmFor(
      'delete_draft',
      protocol,
      version,
      translate('protocols.delete_draft')
    );
    if (!confirmed) return false;
    return attempt(async () => {
      await deleteProtocolDraft(projectId.value, version.protocol_version_id);
      notify(translate('protocols.messages.draft_deleted'));
      await load();
    });
  }

  async function archive(protocol, version) {
    const confirmed = await confirmFor(
      'archive',
      protocol,
      version,
      translate('protocols.confirm.archive.confirm')
    );
    if (!confirmed) return false;
    return attempt(async () => {
      await archiveProtocolVersion(
        projectId.value,
        version.protocol_version_id
      );
      notify(translate('protocols.messages.archived'));
      await load();
    });
  }

  async function purge(protocol, version) {
    const confirmed = await confirmFor(
      'purge',
      protocol,
      version,
      translate('protocols.delete_permanently')
    );
    if (!confirmed) return false;
    return attempt(async () => {
      await purgeProtocolVersion(projectId.value, version.protocol_version_id);
      notify(translate('protocols.messages.purged'));
      await load();
    });
  }

  function pin(version) {
    return attempt(async () => {
      await pinProtocolVersion(projectId.value, version.protocol_version_id);
      notify(translate('protocols.messages.pinned'));
    });
  }

  async function scan(version) {
    scanning.value = true;
    await attempt(async () => {
      const { data } = await runComplianceScan(
        projectId.value,
        version.protocol_version_id,
        true
      );
      scans.value = [
        data,
        ...scans.value.filter((item) => item.scan_id !== data.scan_id),
      ];
      notify(
        data.failed_files
          ? translate('protocols.messages.scan_attention')
          : translate('protocols.messages.scan_passed'),
        data.failed_files ? 'warning' : 'success'
      );
    });
    scanning.value = false;
  }

  function createCorrection(file, issue) {
    return attempt(async () => {
      await reviewService.create(projectId.value, {
        upload_id: null,
        validation_issue_id: issue.validation_issue_id,
        filename: file.filename,
        title: translate('protocols.correction.title', {
          filename: file.filename,
        }),
        initial_comment: translate('protocols.correction.comment', {
          message: issue.message,
          location: issue.location,
        }),
      });
      notify(translate('protocols.messages.correction_created'));
    });
  }

  return {
    protocols,
    scans,
    latestScan,
    loading,
    scanning,
    error,
    fail,
    load,
    publish,
    removeDraft,
    archive,
    purge,
    pin,
    scan,
    createCorrection,
  };
}
