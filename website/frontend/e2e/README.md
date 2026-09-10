# Browser workflow tests

Run the Playwright suite from the repository root with:

```bash
make test-e2e
```

Install its browser once on a new development machine with:

```bash
cd website/frontend
npx playwright install chromium
```

The browser suite intercepts the documented API contracts and does not alter a
developer's corpus or database. It verifies the assembled Vue application,
including route guards, authenticated workspace hydration, contribution
ordering, research-context review, details navigation, and responsive layout.

Backend unit and PostgreSQL integration tests remain responsible for EAF,
database, migration, and merge semantics. Together, the suites cover both the
browser workflow and the authoritative server-side state transitions.
