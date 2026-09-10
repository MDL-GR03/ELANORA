import { expect, test } from '@playwright/test';

const project = {
  project_id: 268,
  project_name: 'E2E corpus',
  project_description: 'Disposable browser-test project',
  permission: 'admin',
};

const contribution = (id, researcher, context) => ({
  upload_id: id,
  branch_name: `contribution-${id}`,
  merge_status: 'ready_to_merge',
  uploaded_at: `2026-09-09T12:${id === 14 ? '41' : '42'}:00Z`,
  uploaded_by: researcher,
  tested_at: '2026-09-09T12:45:00Z',
  files: {
    new: [],
    modified: ['elan_files/CLSFB2912_S060.eaf'],
    deleted: [],
  },
  quality_checks: { protocol: 'not_configured' },
  annotation_collisions: [],
  conflicted_files: [],
  research_context: {
    changed_tiers: ['CA:summary1'],
    baseline_changed_tiers: [],
    declared_baseline_correction_tiers: [],
    outside_scope_tiers: [],
    ...context,
  },
});

const contributions = [
  contribution(14, 'external.researcher', {
    declared_topic_name: 'Prosody',
    summary: 'Reviewed prominence and rhythm.',
    changed_tiers: ['CA:summary1', 'Sign:left'],
    baseline_changed_tiers: ['Sign:left'],
    scope_status: 'aligned',
  }),
  contribution(15, 'second.researcher', {
    proposed_topic_name: 'Interactional rhythm',
    summary: 'Annotated turn timing.',
    scope_status: 'topic_review_needed',
  }),
];

async function mockApplication(page) {
  await page.context().addCookies([
    {
      name: 'elanora_csrf',
      value: 'e2e-only-token',
      domain: '127.0.0.1',
      path: '/',
    },
  ]);
  await page.addInitScript((selectedProject) => {
    localStorage.setItem('language', 'en');
    localStorage.setItem('projects', JSON.stringify([selectedProject]));
    localStorage.setItem('currentProject', JSON.stringify(selectedProject));
  }, project);

  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body = {};
    if (path.endsWith('/setup/status')) body = { initialized: true };
    else if (path.endsWith('/user/me')) {
      body = { user_id: 1, username: 'administrator', role: 'admin' };
    } else if (path.endsWith('/git/user-projects')) {
      body = { projects: [project] };
    } else if (path.endsWith('/instance/info')) {
      body = { instance_name: 'E2E instance', default_language: 'en' };
    } else if (path.includes('/admin/pending-uploads')) {
      body = { pending_uploads: contributions };
    } else if (path.endsWith('/review/projects/268/cases')) body = [];
    else if (path.endsWith('/tier/268/topics')) {
      body = [{ topic_id: 1, name: 'Prosody', tier_names: ['CA:summary1'] }];
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });
  });
}

test.beforeEach(async ({ page }) => {
  await mockApplication(page);
});

test('admin orders contributions and inspects declared research context', async ({
  page,
}) => {
  await page.goto('/contribution?view=queue');

  const cards = page.getByRole('heading', {
    name: /^Contribution #(14|15)$/,
    level: 3,
  });
  await expect(cards).toHaveText(['Contribution #14', 'Contribution #15']);
  await expect(page.getByText('Reviewed prominence and rhythm.')).toBeVisible();

  await page.getByLabel('Order incoming contributions').click();
  await page.getByRole('option', { name: 'Newest first' }).click();
  await expect(cards).toHaveText(['Contribution #15', 'Contribution #14']);

  await page.getByRole('button', { name: 'Review topic suggestion' }).click();
  await expect(page.getByText('Use an existing topic')).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Assign topic' })
  ).toBeDisabled();

  await page
    .locator('#contribution-14')
    .getByRole('button', { name: 'View Details' })
    .click();
  await expect(
    page.getByRole('heading', { name: 'Contribution #14' })
  ).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Research context' })
  ).toBeVisible();
  await expect(
    page.getByText('Declared topic matches the detected changes')
  ).toBeVisible();
  await expect(page.getByText('Sign:left', { exact: true })).toBeVisible();
});

test('contribution queue remains usable at a mobile viewport', async ({
  page,
}, testInfo) => {
  test.skip(!testInfo.project.name.startsWith('mobile-'), 'Mobile-only check');
  await page.goto('/contribution?view=queue');

  await expect(
    page.getByRole('heading', { name: 'Incoming work' })
  ).toBeVisible();
  await expect(page.getByLabel('Order incoming contributions')).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Contribution #14' })
  ).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth)
  ).toBeLessThanOrEqual(
    await page.evaluate(() => document.documentElement.clientWidth)
  );
});
