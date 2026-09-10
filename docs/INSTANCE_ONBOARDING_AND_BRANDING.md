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

Logo uploads are signature-checked, size-limited, decoded safely, stripped of
metadata, and normalized to a bounded WebP image. The database stores immutable
identity and checksum metadata while bytes live behind the asset-storage
boundary. Reads verify both byte size and SHA-256 before serving the logo.

`ASSET_STORAGE_BACKEND=local` is the development and single-node default. Set it
to `s3` with `ASSET_S3_BUCKET` and optional prefix, region, and endpoint settings
for AWS S3 or a compatible institutional service. Credentials may come from the
standard AWS workload-identity chain; if static credentials are unavoidable,
provide both `ASSET_S3_ACCESS_KEY_ID` and `ASSET_S3_SECRET_ACCESS_KEY` through the
deployment secret manager. Never commit them to an environment file.

The bucket must have versioning, encryption, retention, access logging, and an
independent backup policy enabled by infrastructure. ELANORA writes UUID-based
keys with create-only semantics so an existing asset is never silently
overwritten. The encrypted filesystem recovery bundle covers local assets; an
S3 deployment must pair its PostgreSQL recovery point with a bucket version or
snapshot and rehearse restoring both.

The CLI command remains supported for unattended provisioning and emergency
recovery. Browser setup is the normal human workflow; the CLI is not a second
implementation of the domain operation.
