# Authorization matrix

ELANORA uses two separate authorization dimensions. `USER.role` controls the
institution installation, while `USER_TO_PROJECT.permission` controls access
to one research project. The frontend mirrors these rules for navigation and
discoverability, but FastAPI dependencies remain the security boundary.

| Function | Read | Write | Project admin | Institution admin |
| --- | ---: | ---: | ---: | ---: |
| See assigned project and its tiers/files | yes | yes | yes | yes |
| Upload EAF contributions and rename files | no | yes | yes | yes |
| Review/merge pending contributions | no | no | yes | yes |
| See and manage project members | no | no | yes | yes |
| Grant project-admin permission | no | no | no | yes |
| Configure naming/file-type standards | no | no | no | yes |
| Organize tier sections | no | no | no | yes |
| Review exceptional server filesystem changes | no | no | no | yes |
| Create, rename, or delete projects | no | no | no | yes |
| Configure institution branding and installation | no | no | no | yes |
| Suspend or restore institution accounts | no | no | no | yes |

The independent `manage_protocols` capability grants access only to the
Protocols configuration section and its versioning/validation actions. It does
not imply write or project-admin permission.

`owner` is a virtual permission representing an institution administrator. It
must never be accepted from an API request or persisted as a delegated project
permission. A project administrator may delegate `read` or `write`, but cannot
promote another member to project admin or alter another project administrator.

Account suspension is reached from **Profile -> Accounts**. Suspending an
account revokes every active browser session immediately and refuses further
logins and token refreshes, while preserving the account's contributions,
reviews, and audit history. Every suspension and restoration records an
`account.suspended` or `account.reactivated` audit event with the
administrator's reason. Two rules protect the installation from becoming
unadministered: an administrator cannot change their own status, and the last
active administrator cannot be suspended.

The project-member administration UI is available from **Projects**, using the
settings action on a project card, then **Collaborators -> Members**. It shows
member identities, project permissions, and the delegated protocol-manager
capability. Institution administrators see every configuration section;
delegated project administrators see only the member-management section.

Public endpoints are limited to installation status/initialization (which is
single-use and setup-token protected), login and account-recovery flows,
invitation-code validation, public instance identity/logo, location reference
data, and the rate-limited contact form.
