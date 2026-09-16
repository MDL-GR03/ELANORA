"""Every refusal the API can return, with a stable code.

Services and routes raise :class:`ElanoraError` with an :class:`ErrorCode`. One
handler turns it into a response carrying the code, its parameters, and an
English message in ``detail``. The interface translates the code; ``detail``
stays for scripts and older clients.

A message must never contain a token, password, participant data or internal
exception detail.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import JsonValue


class ErrorCode(StrEnum):
    """Stable identifiers the interface translates."""

    # General
    INTERNAL_ERROR = "internal_error"
    REQUEST_FAILED = "request_failed"
    # Authentication and sessions
    NOT_AUTHENTICATED = "not_authenticated"
    CREDENTIALS_INVALID = "credentials_invalid"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_INVALID = "token_invalid"
    REFRESH_TOKEN_MISSING = "refresh_token_missing"
    SESSION_REFRESH_FAILED = "session_refresh_failed"
    LOGIN_INVALID = "login_invalid"
    ACCOUNT_SUSPENDED = "account_suspended"
    ROLE_REQUIRED = "role_required"
    # Registration, verification and recovery
    INVITATION_INVALID = "invitation_invalid"
    INVITATION_EMAIL_MISMATCH = "invitation_email_mismatch"
    INVITATION_PROJECT_MISSING = "invitation_project_missing"
    INVITATION_NOT_REDEEMED = "invitation_not_redeemed"
    USERNAME_CHECK_FAILED = "username_check_failed"
    EMAIL_CHECK_FAILED = "email_check_failed"
    VERIFICATION_CODE_INVALID = "verification_code_invalid"
    ACCOUNT_ALREADY_VERIFIED = "account_already_verified"
    EMAIL_VERIFICATION_FAILED = "email_verification_failed"
    PASSWORD_RESET_FAILED = "password_reset_failed"
    CURRENT_PASSWORD_INCORRECT = "current_password_incorrect"
    PASSWORD_CHANGE_FAILED = "password_change_failed"
    PASSWORD_BREACHED = "password_breached"
    PASSWORD_TOO_SHORT = "password_too_short"
    PASSWORD_TOO_LONG = "password_too_long"
    PASSWORD_COMMON = "password_common"
    PASSWORD_REPETITIVE = "password_repetitive"
    PASSWORD_PERSONAL = "password_personal"
    # Profile and accounts
    USERNAME_TAKEN = "username_taken"
    PROFILE_NO_CHANGES = "profile_no_changes"
    PROFILE_UPDATE_FAILED = "profile_update_failed"
    ADDRESS_UPDATE_FAILED = "address_update_failed"
    ACCOUNT_NOT_FOUND = "account_not_found"
    SELF_STATUS_CHANGE_REFUSED = "self_status_change_refused"
    LAST_ADMINISTRATOR_REFUSED = "last_administrator_refused"
    ACCOUNT_STATUS_UNCHANGED = "account_status_unchanged"
    ADMINISTRATOR_INACTIVE = "administrator_inactive"
    # Installation
    SETUP_TOKEN_INVALID = "setup_token_invalid"
    SETUP_ALREADY_DONE = "setup_already_done"
    SETUP_CONCURRENT = "setup_concurrent"
    INSTITUTION_NOT_FOUND = "institution_not_found"
    LOGO_INVALID = "logo_invalid"
    LOGO_NOT_CONFIGURED = "logo_not_configured"
    CONTACT_FAILED = "contact_failed"
    # Membership and invitations
    USER_NOT_FOUND = "user_not_found"
    USER_NOT_IN_PROJECT = "user_not_in_project"
    MEMBERSHIP_INVALID = "membership_invalid"
    PROJECT_ADMIN_GRANT_FORBIDDEN = "project_admin_grant_forbidden"
    PROJECT_ADMIN_CHANGE_FORBIDDEN = "project_admin_change_forbidden"
    OWNER_PERMISSION_RESERVED = "owner_permission_reserved"
    INVITE_ADMIN_FORBIDDEN = "invite_admin_forbidden"
    INVITATIONS_ADMIN_ONLY = "invitations_admin_only"
    INVITATIONS_OWN_ONLY = "invitations_own_only"
    NOTIFICATION_NOT_FOUND = "notification_not_found"
    NOTIFICATION_UPDATE_UNSUPPORTED = "notification_update_unsupported"
    # Project access and storage
    PROJECT_PERMISSION_REQUIRED = "project_permission_required"
    PROJECT_CAPABILITY_REQUIRED = "project_capability_required"
    PROJECT_LOCKED = "project_locked"
    STORAGE_NOT_WRITABLE = "storage_not_writable"
    PROJECT_NOT_FOUND = "project_not_found"
    PROJECT_FILE_NOT_FOUND = "project_file_not_found"
    PROJECT_RESOURCE_NOT_FOUND = "project_resource_not_found"
    PROJECT_STATE_CONFLICT = "project_state_conflict"
    PROJECT_STATE_INVALID = "project_state_invalid"
    PROJECT_OPERATION_INVALID = "project_operation_invalid"
    PROJECT_NAME_UNAVAILABLE = "project_name_unavailable"
    PROJECT_STORAGE_INTACT = "project_storage_intact"
    RECOVERY_BACKUP_NOT_FOUND = "recovery_backup_not_found"
    # Contributions, research topics and copies
    CONTRIBUTION_STATE_CONFLICT = "contribution_state_conflict"
    CORRECTION_REQUEST_NOT_FOUND = "correction_request_not_found"
    CORRECTION_REQUEST_CLOSED = "correction_request_closed"
    EAF_REVIEW_UNAVAILABLE = "eaf_review_unavailable"
    RESEARCH_TOPIC_NOT_FOUND = "research_topic_not_found"
    RESEARCH_TOPIC_UNKNOWN = "research_topic_unknown"
    RESEARCH_TOPIC_EXISTS = "research_topic_exists"
    RESEARCH_TOPIC_USE_EXISTING = "research_topic_use_existing"
    RESEARCH_TOPIC_SIMILAR = "research_topic_similar"
    RESEARCH_TOPIC_MISMATCH = "research_topic_mismatch"
    RESEARCH_TOPICS_MIXED = "research_topics_mixed"
    RESEARCH_COPY_FILENAME_INVALID = "research_copy_filename_invalid"
    RESEARCH_COPY_SOURCE_MISSING = "research_copy_source_missing"
    RESEARCH_COPY_SELECTION_INVALID = "research_copy_selection_invalid"
    FILENAME_NOT_COMPLIANT = "filename_not_compliant"
    PROTECTED_BASELINE_MODIFIED = "protected_baseline_modified"
    TIER_REINTEGRATION_CONFLICT = "tier_reintegration_conflict"
    EAF_FILENAME_INVALID = "eaf_filename_invalid"
    EAF_FILE_NOT_FOUND = "eaf_file_not_found"
    TIERS_NOT_FOUND = "tiers_not_found"
    # Uploads
    UPLOAD_EMPTY = "upload_empty"
    UPLOAD_BATCH_TOO_LARGE = "upload_batch_too_large"
    UPLOAD_FILE_TOO_LARGE = "upload_file_too_large"
    UPLOAD_EXTENSION_REFUSED = "upload_extension_refused"
    UPLOAD_CONTENT_TYPE_REFUSED = "upload_content_type_refused"
    UPLOAD_EAF_INVALID = "upload_eaf_invalid"
    UPLOAD_VALIDATION_FAILED = "upload_validation_failed"
    INVALID_EAF_BATCH = "invalid_eaf_batch"
    PROTOCOL_CONFIGURATION_CONFLICT = "protocol_configuration_conflict"
    # Protocols
    PROTOCOL_NOT_FOUND = "protocol_not_found"
    PROTOCOL_STATE_CONFLICT = "protocol_state_conflict"
    PROTOCOL_NAME_EXISTS = "protocol_name_exists"
    # File types and naming standards
    FILE_TYPE_NOT_FOUND = "file_type_not_found"
    FILE_TYPE_FOREIGN = "file_type_foreign"
    FILE_TYPE_NAME_EXISTS = "file_type_name_exists"
    FILE_TYPE_IN_USE = "file_type_in_use"
    PROJECT_FILE_TYPE_INVALID = "project_file_type_invalid"
    NAMING_REGEX_EMPTY = "naming_regex_empty"
    NAMING_STANDARD_NOT_FOUND = "naming_standard_not_found"
    NAMING_TARGET_FILE_TYPE_MISSING = "naming_target_file_type_missing"
    NAMING_SOURCE_FILE_TYPE_INVALID = "naming_source_file_type_invalid"
    NAMING_STANDARD_DUPLICATE = "naming_standard_duplicate"
    NAMING_STANDARD_IMPORT_DUPLICATE = "naming_standard_import_duplicate"
    # Reviews
    REVIEW_NOT_FOUND = "review_not_found"
    REVIEW_OPERATION_INVALID = "review_operation_invalid"
    REVIEW_ACTION_FORBIDDEN = "review_action_forbidden"
    REVIEW_LINK_FORBIDDEN = "review_link_forbidden"


@dataclass(frozen=True, slots=True)
class ErrorDefinition:
    """How a refusal is reported: its HTTP status and English message."""

    status: int
    message: str


_E = ErrorCode
ERRORS: Mapping[ErrorCode, ErrorDefinition] = {
    _E.INTERNAL_ERROR: ErrorDefinition(500, "Internal server error"),
    _E.REQUEST_FAILED: ErrorDefinition(500, "The request could not be completed"),
    _E.NOT_AUTHENTICATED: ErrorDefinition(401, "Not authenticated"),
    _E.CREDENTIALS_INVALID: ErrorDefinition(401, "Could not validate credentials"),
    _E.TOKEN_EXPIRED: ErrorDefinition(401, "Your session has expired"),
    _E.TOKEN_INVALID: ErrorDefinition(401, "The session token is invalid"),
    _E.REFRESH_TOKEN_MISSING: ErrorDefinition(401, "Refresh token is missing"),
    _E.SESSION_REFRESH_FAILED: ErrorDefinition(
        401, "Your session could not be refreshed"
    ),
    _E.LOGIN_INVALID: ErrorDefinition(400, "Invalid credentials"),
    _E.ACCOUNT_SUSPENDED: ErrorDefinition(
        403, "This account is suspended. Contact your institution administrator."
    ),
    _E.ROLE_REQUIRED: ErrorDefinition(403, "Your role does not allow this action"),
    _E.INVITATION_INVALID: ErrorDefinition(
        400, "The invitation is invalid or has expired"
    ),
    _E.INVITATION_EMAIL_MISMATCH: ErrorDefinition(
        400, "The email address does not match the invitation"
    ),
    _E.INVITATION_PROJECT_MISSING: ErrorDefinition(
        400, "The invitation's project no longer exists"
    ),
    _E.INVITATION_NOT_REDEEMED: ErrorDefinition(
        409, "The invitation could not be redeemed. No account was created."
    ),
    _E.USERNAME_CHECK_FAILED: ErrorDefinition(
        500, "Unable to check username availability"
    ),
    _E.EMAIL_CHECK_FAILED: ErrorDefinition(500, "Unable to check email availability"),
    _E.VERIFICATION_CODE_INVALID: ErrorDefinition(
        400, "The verification code is invalid"
    ),
    _E.ACCOUNT_ALREADY_VERIFIED: ErrorDefinition(
        400, "The account is already verified"
    ),
    _E.EMAIL_VERIFICATION_FAILED: ErrorDefinition(500, "Unable to verify the email"),
    _E.PASSWORD_RESET_FAILED: ErrorDefinition(500, "Unable to reset the password"),
    _E.CURRENT_PASSWORD_INCORRECT: ErrorDefinition(
        400, "The current password is incorrect"
    ),
    _E.PASSWORD_CHANGE_FAILED: ErrorDefinition(500, "Unable to change the password"),
    _E.PASSWORD_BREACHED: ErrorDefinition(
        400, "This password appears in a known data breach"
    ),
    _E.PASSWORD_TOO_SHORT: ErrorDefinition(400, "The password is too short"),
    _E.PASSWORD_TOO_LONG: ErrorDefinition(400, "The password is too long"),
    _E.PASSWORD_COMMON: ErrorDefinition(400, "The password is too common"),
    _E.PASSWORD_REPETITIVE: ErrorDefinition(
        400, "The password is a repeated or sequential pattern"
    ),
    _E.PASSWORD_PERSONAL: ErrorDefinition(
        400, "The password must not be built from the account's own details"
    ),
    _E.USERNAME_TAKEN: ErrorDefinition(409, "This username is already taken"),
    _E.PROFILE_NO_CHANGES: ErrorDefinition(400, "No fields to update"),
    _E.PROFILE_UPDATE_FAILED: ErrorDefinition(500, "Unable to update the profile"),
    _E.ADDRESS_UPDATE_FAILED: ErrorDefinition(500, "Unable to update the address"),
    _E.ACCOUNT_NOT_FOUND: ErrorDefinition(404, "Account not found in this institution"),
    _E.SELF_STATUS_CHANGE_REFUSED: ErrorDefinition(
        409, "Administrators cannot change their own account status"
    ),
    _E.LAST_ADMINISTRATOR_REFUSED: ErrorDefinition(
        409, "The institution must retain an active administrator"
    ),
    _E.ACCOUNT_STATUS_UNCHANGED: ErrorDefinition(
        409, "The account already has the requested status"
    ),
    _E.ADMINISTRATOR_INACTIVE: ErrorDefinition(
        403, "Your administrator access is no longer active"
    ),
    _E.SETUP_TOKEN_INVALID: ErrorDefinition(403, "Invalid setup token"),
    _E.SETUP_ALREADY_DONE: ErrorDefinition(
        409, "This installation is already initialized"
    ),
    _E.SETUP_CONCURRENT: ErrorDefinition(
        409, "This installation was initialized concurrently"
    ),
    _E.INSTITUTION_NOT_FOUND: ErrorDefinition(404, "Institution not found"),
    _E.LOGO_INVALID: ErrorDefinition(422, "Invalid institution logo"),
    _E.LOGO_NOT_CONFIGURED: ErrorDefinition(404, "Institution logo not configured"),
    _E.CONTACT_FAILED: ErrorDefinition(500, "Failed to send the contact message"),
    _E.USER_NOT_FOUND: ErrorDefinition(404, "User not found"),
    _E.USER_NOT_IN_PROJECT: ErrorDefinition(
        404, "The user is not associated with this project"
    ),
    _E.MEMBERSHIP_INVALID: ErrorDefinition(400, "Invalid project membership operation"),
    _E.PROJECT_ADMIN_GRANT_FORBIDDEN: ErrorDefinition(
        403, "Only an institution administrator can grant project administrator access"
    ),
    _E.PROJECT_ADMIN_CHANGE_FORBIDDEN: ErrorDefinition(
        403, "Project administrators cannot modify another administrator"
    ),
    _E.OWNER_PERMISSION_RESERVED: ErrorDefinition(
        422, "Owner is a reserved permission"
    ),
    _E.INVITE_ADMIN_FORBIDDEN: ErrorDefinition(
        403, "Only an institution administrator can invite project administrators"
    ),
    _E.INVITATIONS_ADMIN_ONLY: ErrorDefinition(
        403, "Only administrators can manage these invitations"
    ),
    _E.INVITATIONS_OWN_ONLY: ErrorDefinition(
        403, "You can only view your own invitations"
    ),
    _E.NOTIFICATION_NOT_FOUND: ErrorDefinition(404, "Notification not found"),
    _E.NOTIFICATION_UPDATE_UNSUPPORTED: ErrorDefinition(
        400, "Only marking notifications as read is supported"
    ),
    _E.PROJECT_PERMISSION_REQUIRED: ErrorDefinition(
        403, "Insufficient project permission"
    ),
    _E.PROJECT_CAPABILITY_REQUIRED: ErrorDefinition(
        403, "Missing project capability: {capability}"
    ),
    _E.PROJECT_LOCKED: ErrorDefinition(
        423, "Another operation is currently modifying this project"
    ),
    _E.STORAGE_NOT_WRITABLE: ErrorDefinition(
        503, "Project storage is not writable; contact the instance administrator"
    ),
    _E.PROJECT_NOT_FOUND: ErrorDefinition(404, "Project not found"),
    _E.PROJECT_FILE_NOT_FOUND: ErrorDefinition(404, "Project or file not found"),
    _E.PROJECT_RESOURCE_NOT_FOUND: ErrorDefinition(404, "Project resource not found"),
    _E.PROJECT_STATE_CONFLICT: ErrorDefinition(409, "Project state conflict"),
    _E.PROJECT_STATE_INVALID: ErrorDefinition(422, "Invalid project state"),
    _E.PROJECT_OPERATION_INVALID: ErrorDefinition(400, "Invalid project operation"),
    _E.PROJECT_NAME_UNAVAILABLE: ErrorDefinition(
        409,
        "This name is already used by another project, including a deleted "
        "project that can still be restored. Choose a different name.",
    ),
    _E.PROJECT_STORAGE_INTACT: ErrorDefinition(
        409,
        "This project's storage is intact, so there is nothing to recover. "
        "Reopen the synchronization check to see its current state.",
    ),
    _E.RECOVERY_BACKUP_NOT_FOUND: ErrorDefinition(
        404, "No recovery backup exists for this project"
    ),
    _E.CONTRIBUTION_STATE_CONFLICT: ErrorDefinition(409, "Contribution state conflict"),
    _E.CORRECTION_REQUEST_NOT_FOUND: ErrorDefinition(
        404, "Correction request not found"
    ),
    _E.CORRECTION_REQUEST_CLOSED: ErrorDefinition(
        409, "This correction request cannot accept a new response"
    ),
    _E.EAF_REVIEW_UNAVAILABLE: ErrorDefinition(422, "EAF review is unavailable"),
    _E.RESEARCH_TOPIC_NOT_FOUND: ErrorDefinition(404, "Research topic not found"),
    _E.RESEARCH_TOPIC_UNKNOWN: ErrorDefinition(
        422, "The selected research topic does not exist in this project"
    ),
    _E.RESEARCH_TOPIC_EXISTS: ErrorDefinition(
        409, "A research topic with this name already exists"
    ),
    _E.RESEARCH_TOPIC_USE_EXISTING: ErrorDefinition(
        409, 'Use the existing research topic "{name}" instead'
    ),
    _E.RESEARCH_TOPIC_SIMILAR: ErrorDefinition(
        422, 'Did you mean the existing topic "{suggested_topic_name}"?'
    ),
    _E.RESEARCH_TOPIC_MISMATCH: ErrorDefinition(
        409,
        "The selected research topic does not match the downloaded research copy",
    ),
    _E.RESEARCH_TOPICS_MIXED: ErrorDefinition(
        422, "Upload research copies from one research topic at a time"
    ),
    _E.RESEARCH_COPY_FILENAME_INVALID: ErrorDefinition(
        400, "The research-copy source filename is invalid"
    ),
    _E.RESEARCH_COPY_SOURCE_MISSING: ErrorDefinition(
        409, "The source file {filename} is no longer available"
    ),
    _E.RESEARCH_COPY_SELECTION_INVALID: ErrorDefinition(
        422, "Invalid research-copy tier selection"
    ),
    _E.FILENAME_NOT_COMPLIANT: ErrorDefinition(
        422,
        "This project requires uploaded filenames to follow its naming standard. "
        "Rename the file and upload it again.",
    ),
    _E.PROTECTED_BASELINE_MODIFIED: ErrorDefinition(
        422, "Protected baseline tiers were modified"
    ),
    _E.TIER_REINTEGRATION_CONFLICT: ErrorDefinition(
        409, "Submitted tiers conflict with the accepted file"
    ),
    _E.EAF_FILENAME_INVALID: ErrorDefinition(400, "Select a valid EAF filename"),
    _E.EAF_FILE_NOT_FOUND: ErrorDefinition(404, "The selected EAF file was not found"),
    _E.TIERS_NOT_FOUND: ErrorDefinition(404, "Project not found or no tiers available"),
    _E.UPLOAD_EMPTY: ErrorDefinition(400, "At least one file is required"),
    _E.UPLOAD_BATCH_TOO_LARGE: ErrorDefinition(
        400, "Total upload size too large. Maximum is {max_mb} MB"
    ),
    _E.UPLOAD_FILE_TOO_LARGE: ErrorDefinition(
        400, "File too large. Maximum size is {max_mb} MB per file"
    ),
    _E.UPLOAD_EXTENSION_REFUSED: ErrorDefinition(400, "Only .eaf files are allowed"),
    _E.UPLOAD_CONTENT_TYPE_REFUSED: ErrorDefinition(
        400, "This file type is not allowed for security reasons"
    ),
    _E.UPLOAD_EAF_INVALID: ErrorDefinition(400, "Invalid ELAN file: {summary}"),
    _E.UPLOAD_VALIDATION_FAILED: ErrorDefinition(400, "File validation failed"),
    _E.INVALID_EAF_BATCH: ErrorDefinition(
        422,
        "One or more EAF files failed validation. Original bytes were preserved "
        "for diagnosis; no file in this batch entered project history.",
    ),
    _E.PROTOCOL_CONFIGURATION_CONFLICT: ErrorDefinition(
        409, "Project protocol configuration conflict"
    ),
    _E.PROTOCOL_NOT_FOUND: ErrorDefinition(404, "Protocol not found"),
    _E.PROTOCOL_STATE_CONFLICT: ErrorDefinition(409, "Protocol state conflict"),
    _E.PROTOCOL_NAME_EXISTS: ErrorDefinition(
        409, "A protocol with this name already exists"
    ),
    _E.FILE_TYPE_NOT_FOUND: ErrorDefinition(404, "File type not found in this project"),
    _E.FILE_TYPE_FOREIGN: ErrorDefinition(
        403, "File type does not belong to this project"
    ),
    _E.FILE_TYPE_NAME_EXISTS: ErrorDefinition(
        409, "File type name already exists in this project"
    ),
    _E.FILE_TYPE_IN_USE: ErrorDefinition(
        409,
        "This file type is used by a naming standard or component. Delete the "
        "related naming standard first.",
    ),
    _E.PROJECT_FILE_TYPE_INVALID: ErrorDefinition(400, "Invalid project file type"),
    _E.NAMING_REGEX_EMPTY: ErrorDefinition(
        400, "Regex must not be empty for any component"
    ),
    _E.NAMING_STANDARD_NOT_FOUND: ErrorDefinition(404, "Naming standard not found"),
    _E.NAMING_TARGET_FILE_TYPE_MISSING: ErrorDefinition(
        400, "The target project does not have the required file type"
    ),
    _E.NAMING_SOURCE_FILE_TYPE_INVALID: ErrorDefinition(
        409, "The source naming standard has no valid file type"
    ),
    _E.NAMING_STANDARD_DUPLICATE: ErrorDefinition(
        409, "A naming standard with this name already exists"
    ),
    _E.NAMING_STANDARD_IMPORT_DUPLICATE: ErrorDefinition(
        409, "The imported naming standard already exists in this project"
    ),
    _E.REVIEW_NOT_FOUND: ErrorDefinition(404, "Review case or task not found"),
    _E.REVIEW_OPERATION_INVALID: ErrorDefinition(422, "Invalid review operation"),
    _E.REVIEW_ACTION_FORBIDDEN: ErrorDefinition(403, "Review action not permitted"),
    _E.REVIEW_LINK_FORBIDDEN: ErrorDefinition(
        403, "Only the submitting researcher may link this contribution"
    ),
}


class ElanoraError(Exception):
    """A refusal the researcher should understand, identified by its code.

    ``params`` fill the English message and are returned so the interface can
    fill its translation; they must be safe to show to the requester.
    """

    def __init__(self, code: ErrorCode, **params: JsonValue) -> None:
        self.code = code
        self.params: dict[str, JsonValue] = params
        super().__init__(self.message)

    @property
    def status_code(self) -> int:
        return ERRORS[self.code].status

    @property
    def message(self) -> str:
        template = ERRORS[self.code].message
        try:
            return template.format(**self.params)
        except (KeyError, IndexError):
            return template


def error_body(error: ElanoraError) -> dict[str, JsonValue]:
    """The JSON body returned for a refusal."""
    return {"detail": error.message, "code": error.code.value, "params": error.params}


async def elanora_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Report an :class:`ElanoraError` with its status, code and parameters."""
    if not isinstance(exc, ElanoraError):
        raise exc
    return JSONResponse(status_code=exc.status_code, content=error_body(exc))
