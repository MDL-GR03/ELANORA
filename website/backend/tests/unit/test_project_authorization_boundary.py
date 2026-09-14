"""Every project-scoped API route must be closed to non-members by default.

Invariant 5 of the architecture roadmap states that one installation holds one
institution and that project access is default-deny. Individual behavior tests
cover `ProjectGuard` itself; this guard covers the wiring, so a newly added
route cannot silently omit authorization.
"""

import ast
from pathlib import Path

API_ROOT = Path(__file__).parents[2] / "app" / "api" / "v1"

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}

# A dependency that resolves the caller's permission on the requested project.
PROJECT_GUARDS = {
    "get_project_read_dep",
    "get_project_write_dep",
    "get_project_admin_dep",
    "get_protocol_manager_dep",
}

# The same check performed imperatively in the route body.
IMPERATIVE_GUARDS = {"authorize_project", "authorize_project_access"}

# Institution administrators own the whole installation, so configuration
# routes may rely on the institution guard alone. Each entry is a deliberate
# decision: adding one means accepting that any institution administrator may
# act on any project in the installation. Researchers never reach these.
INSTITUTION_ADMIN_ROUTES = {
    ("effective_naming_standard.py", "assign_standard"),
    ("effective_naming_standard.py", "unassign_standard"),
    ("effective_naming_standard.py", "get_effective_standards_for_location"),
    ("file_type.py", "get_file_types_for_project"),
    ("file_type.py", "remove_file_type_from_project"),
    ("file_type.py", "add_project_file_type"),
    ("file_type.py", "update_project_file_type"),
    ("project_location_file_type.py", "add_file_type"),
    ("project_location_file_type.py", "remove_file_type"),
    ("project_location_file_type.py", "get_file_types"),
    ("project_naming_standard.py", "get_standards_for_project"),
    ("project_naming_standard.py", "get_component_names"),
    ("project_naming_standard.py", "get_project_naming_standards_full"),
}

INSTITUTION_GUARDS = {"get_admin_dep"}


def _referenced_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            names.add(sub.id)
        elif isinstance(sub, ast.Attribute):
            names.add(sub.attr)
    return names


def _router_level_guards(tree: ast.AST) -> set[str]:
    """Guards applied to every route through APIRouter(dependencies=[...])."""
    guards: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        if name != "APIRouter":
            continue
        for keyword in node.keywords:
            if keyword.arg == "dependencies":
                guards |= _referenced_names(keyword.value)
    return guards


def _is_route(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for decorator in func.decorator_list:
        call = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(call, ast.Attribute) and call.attr in HTTP_METHODS:
            return True
    return False


def _parameter_defaults(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names: set[str] = set()
    defaults = list(func.args.defaults) + [d for d in func.args.kw_defaults if d]
    for default in defaults:
        names |= _referenced_names(default)
    return names


def _body_calls(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            called = node.func
            name = (
                called.id
                if isinstance(called, ast.Name)
                else getattr(called, "attr", "")
            )
            names.add(name)
    return names


def _project_routes() -> list[tuple[str, str, int, set[str]]]:
    routes = []
    for path in sorted(API_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        inherited = _router_level_guards(tree)
        for func in ast.walk(tree):
            if not isinstance(func, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if not _is_route(func):
                continue
            parameters = {a.arg for a in func.args.args + func.args.kwonlyargs}
            if "project_id" not in parameters:
                continue
            guards = _parameter_defaults(func) | inherited | _body_calls(func)
            routes.append((path.name, func.name, func.lineno, guards))
    return routes


def test_the_audit_finds_the_project_scoped_routes() -> None:
    """A broken scan would make every assertion below vacuously pass."""
    routes = _project_routes()
    assert len(routes) >= 30
    assert any(guards & PROJECT_GUARDS for _, _, _, guards in routes)


def test_every_project_scoped_route_is_authorized() -> None:
    unprotected = [
        f"{name}:{line} {func}()"
        for name, func, line, guards in _project_routes()
        if not (guards & PROJECT_GUARDS)
        and not (guards & IMPERATIVE_GUARDS)
        and (name, func) not in INSTITUTION_ADMIN_ROUTES
    ]
    assert unprotected == [], (
        "These routes accept a project_id without resolving the caller's "
        "access to that project. Add a project guard dependency, call "
        "authorize_project in the body, or record the route in "
        "INSTITUTION_ADMIN_ROUTES if it is genuinely installation-wide "
        f"configuration: {unprotected}"
    )


def test_institution_admin_routes_really_are_admin_only() -> None:
    """The allow-list must not become a way to leave a route open."""
    routes = {(name, func): guards for name, func, _, guards in _project_routes()}
    missing = sorted(
        entry
        for entry in INSTITUTION_ADMIN_ROUTES
        if not (routes.get(entry, set()) & INSTITUTION_GUARDS)
    )
    assert missing == [], (
        "Routes listed as institution-admin-only no longer require the "
        f"institution administrator guard: {missing}"
    )


def test_the_allow_list_has_no_stale_entries() -> None:
    """A removed or newly guarded route should leave the allow-list."""
    routes = {(name, func) for name, func, _, _ in _project_routes()}
    stale = sorted(entry for entry in INSTITUTION_ADMIN_ROUTES if entry not in routes)
    assert stale == [], f"INSTITUTION_ADMIN_ROUTES lists unknown routes: {stale}"
