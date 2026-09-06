# Instance onboarding and branding

ELANORA uses one installation and one database per institution. The first-run
browser route (`/setup`) creates that institution profile and its first verified
administrator. The operation reuses the maintained CLI bootstrap service, runs
in one database transaction, and is protected by the deployment's
`SETUP_TOKEN`. Database uniqueness constraints and application checks prevent a
second institution profile from being created.

The setup token is deployment infrastructure, not an application password. It
must be generated independently for each server, stored as a secret, and given
only to the person responsible for first-time configuration. Production and
server processes refuse to start with the documented development token. After
successful initialization the browser setup endpoint returns a conflict and can
no longer mutate the installation.

The initial visual identity consists of a primary, secondary, and accent color.
They are validated as six-digit hexadecimal colors in both the API and
PostgreSQL, returned with the public instance profile, and applied as global CSS
custom properties. This keeps feature styles independent from institution
configuration. An authenticated installation administrator can update the same
identity through `PATCH /api/v1/instance/branding`; a dedicated post-install
administration screen can be added without changing this contract.

Logo upload is deliberately not part of this first slice. A production-quality
implementation needs an asset storage abstraction, file signature and size
validation, safe image decoding, generated variants, and a durable backup
policy. Reusing a writable static folder would make container replacements and
multi-node deployments unreliable.

The CLI command remains supported for unattended provisioning and emergency
recovery. Browser setup is the normal human workflow; the CLI is not a second
implementation of the domain operation.
