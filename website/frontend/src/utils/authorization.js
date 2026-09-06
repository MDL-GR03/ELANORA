const PROJECT_PERMISSION_LEVEL = Object.freeze({ read: 1, write: 2, admin: 3 });

export function isInstitutionAdmin(user) {
  return user?.role === 'admin';
}

export function hasProjectPermission(user, project, required = 'read') {
  if (!project) return false;
  if (isInstitutionAdmin(user)) return true;
  if (!(required in PROJECT_PERMISSION_LEVEL)) return false;
  return (
    (PROJECT_PERMISSION_LEVEL[project.permission] || 0) >=
    PROJECT_PERMISSION_LEVEL[required]
  );
}

export function hasProjectCapability(user, project, capability) {
  if (!project) return false;
  return (
    isInstitutionAdmin(user) ||
    Boolean(project?.capabilities?.includes(capability))
  );
}
