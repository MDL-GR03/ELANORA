import os
import shutil
from pathlib import Path

from app.core.centralized_logging import get_logger
from app.core.config import ELAN_BACKUPS_BASE_PATH
from app.core.error_diagnostics import safe_exception_type
from app.storage.paths import safe_project_path


def make_writable(path: Path):
    """Recursively make all files and folders under 'path' writable."""
    for root, dirs, files in os.walk(path):
        for d in dirs:
            os.chmod(os.path.join(root, d), 0o700)
        for f in files:
            os.chmod(os.path.join(root, f), 0o600)


def create_hidden_folder_in_root() -> Path:
    """Create and return the configured same-host recovery cache directory."""
    hidden_folder = Path(ELAN_BACKUPS_BASE_PATH).resolve()
    hidden_folder.mkdir(parents=True, exist_ok=True)
    return hidden_folder


def create_project_backup_structure(project_name: str):
    """Create a backup structure for the project in the hidden folder."""
    hidden_folder = create_hidden_folder_in_root()
    project_backup_path = safe_project_path(hidden_folder, project_name)
    project_backup_path.mkdir(parents=True, exist_ok=True)


def update_backup(project_name: str, projects_root: Path | None):
    """Copy .git, elan_files, README.md, and .gitignore from the project directory to its backup directory."""
    logger = get_logger()
    hidden_folder = create_hidden_folder_in_root()
    project_backup_path = safe_project_path(hidden_folder, project_name)

    # Infer projects_root if not provided
    if projects_root is None:
        projects_root = hidden_folder.parent / "elanora_projects"

    project_path = safe_project_path(projects_root, project_name)

    # Backup .git folder
    git_src = project_path / ".git"
    git_dst = project_backup_path / ".git"
    if git_src.exists() and git_src.is_dir():
        if git_dst.exists():
            shutil.rmtree(git_dst)
            logger.info(f"Removed existing backup .git at {git_dst}")
        shutil.copytree(git_src, git_dst)
        make_writable(git_dst)
        logger.info(f"Copied .git from {git_src} to {git_dst}")
    else:
        logger.warning(f"No .git folder found in {project_path}")

    # Backup elan_files folder (only flat .eaf files)
    elan_src = project_path / "elan_files"
    elan_dst = project_backup_path / "elan_files"
    if elan_src.exists() and elan_src.is_dir():
        if elan_dst.exists():
            shutil.rmtree(elan_dst)
            logger.info(f"Removed existing backup elan_files at {elan_dst}")
        elan_dst.mkdir(parents=True, exist_ok=True)
        for file in elan_src.glob("*.eaf"):
            shutil.copy2(file, elan_dst / file.name)
            os.chmod(elan_dst / file.name, 0o600)
            logger.info(f"Copied {file.name} to backup elan_files")
    else:
        logger.warning(f"No elan_files folder found in {project_path}")

    # Backup README.md
    readme_src = project_path / "README.md"
    readme_dst = project_backup_path / "README.md"
    if readme_src.exists() and readme_src.is_file():
        shutil.copy2(readme_src, readme_dst)
        os.chmod(readme_dst, 0o600)
        logger.info(f"Copied README.md from {readme_src} to {readme_dst}")
    else:
        logger.warning(f"No README.md found in {project_path}")

    # Backup .gitignore
    gitignore_src = project_path / ".gitignore"
    gitignore_dst = project_backup_path / ".gitignore"
    if gitignore_src.exists() and gitignore_src.is_file():
        shutil.copy2(gitignore_src, gitignore_dst)
        os.chmod(gitignore_dst, 0o600)
        logger.info(f"Copied .gitignore from {gitignore_src} to {gitignore_dst}")
    else:
        logger.warning(f"No .gitignore found in {project_path}")


def remove_project_backup(project_name: str):
    """Remove the backup directory for the specified project."""
    logger = get_logger()
    hidden_folder = create_hidden_folder_in_root()
    project_backup_path = safe_project_path(hidden_folder, project_name)

    if project_backup_path.exists():
        try:
            shutil.rmtree(project_backup_path)
            logger.info(f"Deleted backup for project: {project_name}")
        except Exception as e:
            logger.error(
                "Failed to delete a project backup; error_type=%s",
                safe_exception_type(e),
            )
            raise
    else:
        logger.warning(f"No backup found for project: {project_name}")


def restore_project_backup(project_name: str, projects_root: Path | None):
    """Restore .git, elan_files, README.md, and .gitignore from backup to the project directory."""
    logger = get_logger()
    hidden_folder = create_hidden_folder_in_root()
    project_backup_path = safe_project_path(hidden_folder, project_name)

    if projects_root is None:
        projects_root = hidden_folder.parent / "elanora_projects"

    project_path = safe_project_path(projects_root, project_name)
    project_path.mkdir(parents=True, exist_ok=True)

    # Restore .git folder
    git_src = project_backup_path / ".git"
    git_dst = project_path / ".git"
    if git_src.exists() and git_src.is_dir():
        if git_dst.exists():
            make_writable(git_dst)
            shutil.rmtree(git_dst)
            logger.info(f"Removed existing .git at {git_dst}")
        shutil.copytree(git_src, git_dst)
        make_writable(git_dst)
        logger.info(f"Restored .git from backup for project '{project_name}'")
    else:
        logger.warning(f"No .git backup found for project '{project_name}'")

    # Restore elan_files folder (only flat .eaf files)
    elan_src = project_backup_path / "elan_files"
    elan_dst = project_path / "elan_files"
    if elan_src.exists() and elan_src.is_dir():
        if elan_dst.exists():
            shutil.rmtree(elan_dst)
            logger.info(f"Removed existing elan_files at {elan_dst}")
        elan_dst.mkdir(parents=True, exist_ok=True)
        for file in elan_src.glob("*.eaf"):
            shutil.copy2(file, elan_dst / file.name)
            os.chmod(elan_dst / file.name, 0o600)
            logger.info(f"Restored {file.name} from backup to elan_files")
    else:
        logger.warning(f"No elan_files backup found for project '{project_name}'")

    # Restore README.md
    readme_src = project_backup_path / "README.md"
    readme_dst = project_path / "README.md"
    if readme_src.exists() and readme_src.is_file():
        shutil.copy2(readme_src, readme_dst)
        os.chmod(readme_dst, 0o600)
        logger.info(f"Restored README.md from backup for project '{project_name}'")
    else:
        logger.warning(f"No README.md backup found for project '{project_name}'")

    # Restore .gitignore
    gitignore_src = project_backup_path / ".gitignore"
    gitignore_dst = project_path / ".gitignore"
    if gitignore_src.exists() and gitignore_src.is_file():
        shutil.copy2(gitignore_src, gitignore_dst)
        os.chmod(gitignore_dst, 0o600)
        logger.info(f"Restored .gitignore from backup for project '{project_name}'")
    else:
        logger.warning(f"No .gitignore backup found for project '{project_name}'")


def rename_project_backup_folder(old_project_name: str, new_project_name: str):
    """Rename the backup folder for a project in the hidden backup directory.

    Args:
        old_project_name (str): The current name of the project.
        new_project_name (str): The new name to assign to the backup folder.

    Raises:
        FileNotFoundError: If the old backup folder does not exist.
        FileExistsError: If the new backup folder already exists.
        Exception: If renaming fails.

    """
    logger = get_logger()
    hidden_folder = create_hidden_folder_in_root()
    old_backup_path = safe_project_path(hidden_folder, old_project_name)
    new_backup_path = safe_project_path(hidden_folder, new_project_name)

    if not old_backup_path.exists():
        logger.error(f"Backup folder '{old_backup_path}' not found.")
        raise FileNotFoundError(f"Backup folder '{old_backup_path}' not found.")
    if new_backup_path.exists():
        logger.error(f"Target backup folder '{new_backup_path}' already exists.")
        raise FileExistsError(
            f"Target backup folder '{new_backup_path}' already exists."
        )
    try:
        shutil.move(str(old_backup_path), str(new_backup_path))
        logger.info(
            f"Renamed backup folder from '{old_backup_path}' to '{new_backup_path}'"
        )
    except Exception as e:
        logger.error(
            "Failed to rename a backup directory; error_type=%s",
            safe_exception_type(e),
        )
        raise
