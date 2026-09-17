import { ref } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useProtocolLibrary } from './useProtocolLibrary';

const api = vi.hoisted(() => ({
  archiveProtocolVersion: vi.fn(),
  deleteProtocolDraft: vi.fn(),
  listComplianceScans: vi.fn(),
  listProtocols: vi.fn(),
  pinProtocolVersion: vi.fn(),
  publishProtocolVersion: vi.fn(),
  purgeProtocolVersion: vi.fn(),
  runComplianceScan: vi.fn(),
}));
const reviews = vi.hoisted(() => ({ create: vi.fn() }));
vi.mock('@/api/service/protocolService', () => api);
vi.mock('@/api/service/reviewService', () => ({ default: reviews }));

const protocol = { protocol_id: 1, name: 'Core' };
const version = { protocol_version_id: 10, version_number: 2 };

describe('useProtocolLibrary', () => {
  let notify;
  let confirm;

  function setup() {
    notify = vi.fn();
    confirm = vi.fn().mockResolvedValue(true);
    return useProtocolLibrary({
      projectId: ref(5),
      translate: (key) => `t:${key}`,
      notify,
      confirm,
    });
  }

  beforeEach(() => {
    Object.values(api).forEach((mock) => mock.mockReset());
    reviews.create.mockReset();
    api.listProtocols.mockResolvedValue({ data: [protocol] });
    api.listComplianceScans.mockResolvedValue({ data: [{ scan_id: 1 }] });
  });

  it('loads protocols and scans', async () => {
    const library = setup();
    await library.load();
    expect(library.protocols.value).toEqual([protocol]);
    expect(library.latestScan.value).toEqual({ scan_id: 1 });
    expect(library.loading.value).toBe(false);
  });

  it('shows the translated reason when an action is refused', async () => {
    api.publishProtocolVersion.mockRejectedValue({
      response: { data: { code: 'protocol_state_conflict' } },
    });
    const library = setup();

    expect(await library.publish(version)).toBe(false);
    expect(library.error.value).toBe('t:apiErrors.protocol_state_conflict');
    expect(notify).not.toHaveBeenCalled();
  });

  it('does nothing when a destructive action is not confirmed', async () => {
    const library = setup();
    confirm.mockResolvedValue(false);

    expect(await library.removeDraft(protocol, version)).toBe(false);
    expect(await library.archive(protocol, version)).toBe(false);
    expect(await library.purge(protocol, version)).toBe(false);
    expect(api.deleteProtocolDraft).not.toHaveBeenCalled();
    expect(api.archiveProtocolVersion).not.toHaveBeenCalled();
    expect(api.purgeProtocolVersion).not.toHaveBeenCalled();
  });

  it('archives without an untranslated reason and reloads', async () => {
    const library = setup();
    expect(await library.archive(protocol, version)).toBe(true);
    expect(api.archiveProtocolVersion).toHaveBeenCalledWith(5, 10);
    expect(confirm.mock.calls[0][0].tone).toBe('danger');
    expect(api.listProtocols).toHaveBeenCalledOnce();
  });

  it('puts a new scan first and warns when files need attention', async () => {
    api.runComplianceScan.mockResolvedValue({
      data: { scan_id: 2, failed_files: 3 },
    });
    const library = setup();
    await library.load();
    await library.scan(version);

    expect(api.runComplianceScan).toHaveBeenCalledWith(5, 10, true);
    expect(library.scans.value.map((item) => item.scan_id)).toEqual([2, 1]);
    expect(notify).toHaveBeenCalledWith(
      't:protocols.messages.scan_attention',
      'warning'
    );
    expect(library.scanning.value).toBe(false);
  });

  it('opens a correction request for a finding', async () => {
    const library = setup();
    await library.createCorrection(
      { filename: 'a.eaf' },
      { validation_issue_id: 9, message: 'Missing tier', location: '/X' }
    );
    expect(reviews.create).toHaveBeenCalledWith(
      5,
      expect.objectContaining({ validation_issue_id: 9, filename: 'a.eaf' })
    );
  });
});
