# Installing ELANORA

One institution, one installation. Setup generates everything it can and asks
only for what the institution alone can decide.

```sh
make install
```

or, without a terminal to answer prompts:

```sh
sh installer/install.sh \
  --url https://elanora.example.org \
  --institution "Example Institute" \
  --admin-email admin@example.org \
  --admin-first-name Ada \
  --admin-last-name Researcher
```

`make install-check` verifies prerequisites and changes nothing.

## What it asks

| Question | Why it cannot be derived |
| --- | --- |
| Where researchers will reach this installation | Decides cookie, CORS and API addresses; only the institution knows its address. |
| The institution's name | Shown to researchers and recorded on every contribution. |
| The first administrator's name and email | Somebody has to be able to sign in and invite the rest. |

Optional: `--admin-username` (default `admin`) and `--timezone` (default `UTC`).

## What it never asks

Every secret is generated: the token signing key, the setup token, the database
password, the outbox encryption key, and the passphrase that encrypts backups.
Re-running setup keeps the ones already there — rotating the backup passphrase
would make every backup taken so far unreadable.

The first administrator's password is generated and printed once, at the end.
Change it after signing in.

## What happens afterwards

The installation maintains itself. A maintenance worker in the composition
backs it up daily, verifies the newest backup weekly, applies each project's
retention policy, and watches the disk holding project storage. The
administrator operations page reports what it actually did, including when
there is no usable backup.

Backups go to `./backups` on this machine by default, so a fresh installation
is recoverable immediately. That protects against losing the database or a bad
upgrade, not against losing the machine: point it at storage elsewhere before
trusting it with research that cannot be re-collected. See
[`../docs/DISASTER_RECOVERY.md`](../docs/DISASTER_RECOVERY.md).

Email delivery is optional. Without `MAIL_*` configured, invitations and
verification messages queue and the operations page reports them; nothing else
is blocked.

## Re-running

Safe. Existing secrets and an existing institution are left alone, so the same
command upgrades an installation in place after pulling a new version.
