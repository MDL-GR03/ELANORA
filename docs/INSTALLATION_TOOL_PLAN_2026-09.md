# Installation Tool Feature Plan

**Date:** 18 September 2026  
**Branch:** `feat/first-time-setup-wizard` (to be created after this plan is approved)  
**Status:** Planning Phase

## Summary

This document outlines the plan for adding an installation configuration tool and guided onboarding workflow to ELANORA. The feature will:

1. Allow administrators to modify installation settings after initial setup
2. Provide a guided workflow for configuring the first project, inviting the first collaborator, and uploading the first files
3. Be integrated into the existing Operations page or a new Administration page

## Current State Analysis

### What Already Exists

1. **Backend Setup Endpoints** (`/api/v1/setup/*`):
   - `GET /api/v1/setup/status` - Checks if setup is available
   - `POST /api/v1/setup/initialize` - One-time bootstrap with first admin
   - Located in: `website/backend/app/api/v1/setup.py`

2. **Frontend SetupPage** (`/setup`):
   - One-time form for initial installation
   - Creates instance owner and visual identity
   - Located in: `website/frontend/src/views/SetupPage.vue`

3. **OperationsPage** (`/operations`):
   - Admin-only page for monitoring
   - Shows storage, integrity, backup status
   - Located in: `website/frontend/src/views/OperationsPage.vue`
   - Accessible via AppHeader for administrators

4. **AdminInvitationsPage** (`/admin-invitations`):
   - For managing user invitations
   - Separate from OperationsPage

5. **AppHeader Navigation**:
   - Operations link visible to administrators
   - No dedicated Administration menu yet

### What's Missing

1. **Post-Setup Configuration**: No way to modify installation settings after initial setup
2. **Guided Onboarding**: No workflow for first project, collaborator, and file upload
3. **Centralized Admin**: No single administration page for all admin functions

## Proposed Solution

### Option A: Extend OperationsPage (Recommended)

Add installation configuration as a new section within the existing OperationsPage. This maintains consistency with the current admin-only access pattern.

**Pros:**
- Consistent with existing patterns
- Single location for all admin operational tasks
- No new menu items needed
- Lower complexity

**Cons:**
- OperationsPage could become large
- Mixes monitoring with configuration

### Option B: Create New AdministrationPage

Create a new Administration page accessible via AppHeader with sub-routes:
- `/admin/installation` - Installation settings
- `/admin/onboarding` - Guided first-project workflow

**Pros:**
- Clear separation of concerns
- Room for future admin features
- Better organization

**Cons:**
- New menu item
- More complex routing
- Need to decide between Operations and Administration for admin functions

**Recommendation:** Start with **Option A** (extend OperationsPage) as it's simpler and can be refactored later if needed.

## Feature Requirements

### 1. Installation Configuration Modification

Allow administrators to modify installation settings that were set during initial setup:

- Instance name
- Institution name
- Visual theme (colors)
- Default language
- Storage configuration
- Backup settings

**Backend Requirements:**
- New endpoint: `PATCH /api/v1/instance` or `PATCH /api/v1/setup/instance`
- Update Instance model to allow modifications
- Add validation for changes
- Audit logging for all modifications

**Frontend Requirements:**
- New component: `InstallationSettingsPanel`
- Form with current instance settings
- Validation and confirmation dialogs
- Success/error feedback

### 2. Guided Onboarding Workflow

Provide a step-by-step guide for new installations to configure their first project:

**Steps:**
1. **Project Creation**
   - Guide through creating the first project
   - Set project name, description, conventions/standards
   - Configure data classification and retention

2. **First Collaborator**
   - Invite first team member
   - Set appropriate permissions
   - Send invitation email

3. **First File Upload**
   - Guide through uploading first EAF file
   - Verify it passes validation
   - Explain the review process

**Backend Requirements:**
- No new endpoints needed (reuse existing project, invitation, upload endpoints)
- Track onboarding completion status in database
- New model: `OnboardingStatus` (table to track progress)

**Frontend Requirements:**
- New component: `OnboardingWizard`
- Step indicator showing progress
- Contextual help at each step
- Ability to save and resume
- Skip option for experienced users

### 3. Database Needs Configuration

Allow configuration of database-related settings:

- Connection pool settings
- Backup schedule
- Retention policies (already partially exists)
- Storage backend configuration

**Backend Requirements:**
- New endpoint: `GET /api/v1/operations/configuration`
- New endpoint: `PATCH /api/v1/operations/configuration`
- Validation for database-related settings
- Restart/reload mechanisms where needed

**Frontend Requirements:**
- New component: `DatabaseConfigurationPanel`
- Form with safe defaults
- Warning for changes that require restart
- Confirmation for sensitive changes

## Implementation Plan

### Phase 1: Backend Foundation (Priority: High)

1. **Add Onboarding Service**
   - Create `app/services/onboarding.py`
   - Define onboarding state machine
   - Track completion of each step
   - Pydantic models for onboarding state

2. **Add Onboarding Endpoints**
   - `GET /api/v1/onboarding/status` - Get current onboarding state
   - `POST /api/v1/onboarding/start` - Begin onboarding workflow
   - `POST /api/v1/onboarding/complete-step` - Mark a step as complete
   - `POST /api/v1/onboarding/skip` - Skip onboarding

3. **Add Installation Configuration Endpoints**
   - `GET /api/v1/instance` - Get current instance settings
   - `PATCH /api/v1/instance` - Update instance settings
   - Add instance update service

4. **Add Database Configuration Endpoints**
   - `GET /api/v1/operations/configuration` - Get current configuration
   - `PATCH /api/v1/operations/configuration` - Update configuration

5. **Database Migration**
   - Add `onboarding_status` table
   - Add instance modification tracking
   - Add configuration history table

### Phase 2: Frontend Foundation (Priority: High)

1. **Create Composables**
   - `useOnboarding` - Manage onboarding state
   - `useInstallationSettings` - Manage instance configuration
   - `useDatabaseConfiguration` - Manage database settings

2. **Create Components**
   - `OnboardingWizard.vue` - Main wizard component
   - `OnboardingStep.vue` - Individual step component
   - `InstallationSettingsForm.vue` - Instance configuration form
   - `DatabaseConfigurationForm.vue` - Database settings form
   - `FirstProjectGuide.vue` - First project creation guide
   - `FirstCollaboratorGuide.vue` - First collaborator invitation guide
   - `FirstUploadGuide.vue` - First file upload guide

3. **Update OperationsPage**
   - Add new sections for installation and onboarding
   - Integrate new components
   - Add routing for onboarding steps

### Phase 3: Integration and Testing (Priority: High)

1. **Backend Tests**
   - Unit tests for onboarding service
   - Integration tests for new endpoints
   - Authorization tests
   - Validation tests

2. **Frontend Tests**
   - Unit tests for composables
   - Component tests for new components
   - E2E tests for onboarding workflow
   - Translation parity for new strings

3. **Documentation**
   - Update API documentation
   - Add user documentation for onboarding
   - Update example env files if needed

## Technical Specifications

### Backend Models

```python
# app/model/onboarding.py
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.sql import func
from app.db.base import Base

class OnboardingStatus(Base):
    __tablename__ = "onboarding_status"
    
    id = Column(Integer, primary_key=True)
    instance_id = Column(Integer, ForeignKey("instance.id"), unique=True, nullable=False)
    current_step = Column(Enum("project", "collaborator", "upload", "complete", "skipped"), default=None)
    project_created = Column(Boolean, default=False)
    collaborator_invited = Column(Boolean, default=False)
    first_upload = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), default=None)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

```python
# app/schema/requests/onboarding.py
from enum import Enum
from pydantic import BaseModel

class OnboardingStep(str, Enum):
    PROJECT = "project"
    COLLABORATOR = "collaborator"
    UPLOAD = "upload"
    COMPLETE = "complete"
    SKIPPED = "skipped"

class OnboardingStatusResponse(BaseModel):
    current_step: OnboardingStep | None
    project_created: bool
    collaborator_invited: bool
    first_upload: bool
    completed: bool
    completed_at: str | None

class MarkStepCompleteRequest(BaseModel):
    step: OnboardingStep
```

### Frontend State Management

```javascript
// src/composables/useOnboarding.js
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';

export function useOnboarding() {
  const { t } = useI18n();
  const steps = [
    { id: 'project', title: t('onboarding.steps.project.title'), description: t('onboarding.steps.project.description') },
    { id: 'collaborator', title: t('onboarding.steps.collaborator.title'), description: t('onboarding.steps.collaborator.description') },
    { id: 'upload', title: t('onboarding.steps.upload.title'), description: t('onboarding.steps.upload.description') },
  ];
  
  const currentStep = ref(null);
  const completedSteps = ref(new Set());
  const isComplete = computed(() => completedSteps.value.size === steps.length);
  
  // Methods to load status, complete step, skip, etc.
  
  return { steps, currentStep, completedSteps, isComplete, ... };
}
```

## Safeguards and Best Practices

### Backend Safeguards

1. **Instance Modification**
   - Only administrators can modify instance settings
   - Critical settings (like instance_id) cannot be changed
   - Changes are audited in audit trail
   - Rate limiting on modification endpoints

2. **Database Configuration**
   - Validation of all configuration values
   - Safe defaults for all settings
   - Warning for changes that require restart
   - Prevent changes that would break the system

3. **Onboarding**
   - Only available for new installations
   - Can be skipped by experienced users
   - Progress is saved and can be resumed
   - Completion marks installation as "configured"

### Frontend Safeguards

1. **Installation Settings**
   - Confirmation dialog for critical changes
   - Loading states to prevent double-submission
   - Error handling with user-friendly messages
   - Form validation before submission

2. **Database Configuration**
   - Clear warnings for changes requiring restart
   - Disabled fields for read-only settings
   - Tooltips explaining each setting
   - Visual indication of changed values

3. **Onboarding Wizard**
   - Step validation before allowing next
   - Save progress automatically
   - Allow skipping the entire workflow
   - Clear exit path at any point

## File Structure

```
website/backend/app/
├── api/v1/
│   ├── onboarding.py          # New: Onboarding endpoints
│   └── instance.py            # New: Instance modification endpoint
├── model/
│   └── onboarding.py          # New: OnboardingStatus model
├── schema/
│   ├── requests/
│   │   └── onboarding.py      # New: Request schemas
│   └── responses/
│       └── onboarding.py      # New: Response schemas
└── services/
    └── onboarding.py          # New: Onboarding service

website/frontend/src/
├── components/
│   ├── common/
│   │   └── OnboardingWizard.vue     # New: Main wizard
│   └── pageSpecific/
│       └── operations/
│           ├── InstallationSettingsForm.vue  # New
│           ├── DatabaseConfigurationForm.vue # New
│           ├── FirstProjectGuide.vue         # New
│           ├── FirstCollaboratorGuide.vue     # New
│           └── FirstUploadGuide.vue           # New
├── composables/
│   ├── useOnboarding.js              # New
│   ├── useInstallationSettings.js    # New
│   └── useDatabaseConfiguration.js   # New
├── locales/
│   ├── en.json                        # Add onboarding strings
│   ├── fr.json                        # Add onboarding strings
│   └── ja.json                        # Add onboarding strings
├── router/
│   └── router.js                     # Add onboarding routes
└── views/
    └── OperationsPage.vue             # Modified: Add new sections
```

## Translation Requirements

New translation keys needed in en.json, fr.json, ja.json:

```json
{
  "onboarding": {
    "title": "Welcome to ELANORA",
    "description": "Let's get your installation configured",
    "skip": "Skip onboarding",
    "steps": {
      "project": {
        "title": "Create Your First Project",
        "description": "Start by creating your first research project"
      },
      "collaborator": {
        "title": "Invite Your First Collaborator",
        "description": "Add a team member to work with you"
      },
      "upload": {
        "title": "Upload Your First File",
        "description": "Upload and validate your first EAF file"
      }
    }
  },
  "installation": {
    "settings": "Installation Settings",
    "edit": "Edit Installation",
    "save": "Save Changes",
    "success": "Settings updated successfully"
  },
  "database": {
    "configuration": "Database Configuration",
    "warning": "Some changes require application restart"
  }
}
```

## Success Criteria

1. **Backend**
   - [ ] Onboarding service with state tracking
   - [ ] New endpoints for onboarding and configuration
   - [ ] Database migration for onboarding_status
   - [ ] All endpoints have proper authorization
   - [ ] All changes are audited
   - [ ] Integration tests pass

2. **Frontend**
   - [ ] Onboarding wizard guides new users
   - [ ] Installation settings can be modified
   - [ ] Database configuration is available
   - [ ] All new strings are translated
   - [ ] All tests pass
   - [ ] Accessible to screen readers

3. **User Experience**
   - [ ] Clear progress through onboarding
   - [ ] Helpful tooltips and explanations
   - [ ] Smooth transitions between steps
   - [ ] Clear error messages
   - [ ] Can be skipped or resumed

## Dependencies

1. **Existing Features**
   - SetupPage for initial installation
   - OperationsPage for admin access
   - Project creation workflow
   - Invitation system
   - File upload system

2. **New Dependencies**
   - None - uses existing patterns and libraries

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Onboarding breaks existing setup | Keep onboarding optional and skippable |
| Instance modification causes issues | Validate all changes, audit everything |
| Database config changes break system | Prevent unsafe changes, require restart warnings |
| Translation parity issues | Use existing i18n tools, validate before merge |
| Performance issues with new endpoints | Rate limiting, proper indexing |

## Timeline Estimate

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1 | Backend foundation | 2-3 days |
| Phase 2 | Frontend foundation | 3-4 days |
| Phase 3 | Integration and testing | 2 days |
| **Total** | | **1 week** |

## Next Steps

1. Review and approve this plan
2. Create branch `feat/first-time-setup-wizard` (if not already exists)
3. Implement Phase 1: Backend foundation
4. Commit and run gates after each phase
5. Review and refine as needed

## Questions for Team

1. Should onboarding be mandatory for new installations? (Recommendation: No, but strongly encouraged)
2. Should we create a new Administration page or extend OperationsPage? (Recommendation: Extend OperationsPage for now)
3. What level of database configuration should be exposed? (Recommendation: Storage backend, backup schedule, retention policies)
4. Should first collaborator be required to have admin privileges? (Recommendation: No, regular member is safer)
