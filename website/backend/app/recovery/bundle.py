"""Encrypted, checksum-manifested installation recovery bundles."""

import hashlib
import json
import os
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"ELANORA-RECOVERY-V1\n"
SALT_SIZE = 16
NONCE_SIZE = 12
TAG_SIZE = 16
CHUNK_SIZE = 1024 * 1024
MINIMUM_PASSPHRASE_LENGTH = 16


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _key(passphrase: str, salt: bytes) -> bytes:
    if len(passphrase) < MINIMUM_PASSPHRASE_LENGTH:
        raise ValueError("Backup passphrase must contain at least 16 characters")
    return Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(
        passphrase.encode("utf-8")
    )


def _source_files(
    database_dump: Path, projects_root: Path, assets_root: Path
) -> list[tuple[Path, str]]:
    if database_dump.is_symlink():
        raise ValueError("Database dump may not be a symbolic link")
    sources = [(database_dump, "database.sql")]
    for root, prefix in ((projects_root, "projects"), (assets_root, "instance-assets")):
        if not root.is_dir():
            raise FileNotFoundError(f"Required backup directory not found: {root}")
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Backup source contains a symbolic link: {path}")
            if path.is_file():
                sources.append((path, f"{prefix}/{path.relative_to(root).as_posix()}"))
            elif not path.is_dir():
                raise ValueError(f"Backup source contains a special file: {path}")
    return sources


def create_bundle(
    database_dump: Path,
    projects_root: Path,
    assets_root: Path,
    output: Path,
    passphrase: str,
) -> dict[str, object]:
    """Create an encrypted installation snapshot from an existing SQL dump."""
    if not database_dump.is_file():
        raise FileNotFoundError(f"Database dump not found: {database_dump}")
    if output.exists():
        raise FileExistsError(f"Recovery bundle already exists: {output}")
    sources = _source_files(database_dump, projects_root, assets_root)
    manifest: dict[str, object] = {
        "format": "elanora-recovery-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "files": [
            {"path": archive_name, "size": path.stat().st_size, "sha256": _sha256(path)}
            for path, archive_name in sources
        ],
        "external_media_included": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="elanora-bundle-") as temporary:
        archive = Path(temporary) / "payload.tar.gz"
        with tarfile.open(archive, "w:gz", format=tarfile.PAX_FORMAT) as tar:
            manifest_bytes = json.dumps(
                manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            info = tarfile.TarInfo("manifest.json")
            info.size = len(manifest_bytes)
            info.mtime = 0
            with tempfile.SpooledTemporaryFile() as manifest_file:
                manifest_file.write(manifest_bytes)
                manifest_file.seek(0)
                tar.addfile(info, manifest_file)
            for path, archive_name in sources:
                tar.add(path, arcname=archive_name, recursive=False)
        with tempfile.NamedTemporaryFile(
            prefix=f".{output.name}.", dir=output.parent, delete=False
        ) as encrypted_file:
            temporary_output = Path(encrypted_file.name)
        try:
            _encrypt(archive, temporary_output, passphrase)
            os.chmod(temporary_output, 0o600)
            temporary_output.replace(output)
        finally:
            temporary_output.unlink(missing_ok=True)
    verify_bundle(output, passphrase)
    return manifest


def _encrypt(source: Path, destination: Path, passphrase: str) -> None:
    salt, nonce = os.urandom(SALT_SIZE), os.urandom(NONCE_SIZE)
    encryptor = Cipher(
        algorithms.AES(_key(passphrase, salt)), modes.GCM(nonce)
    ).encryptor()
    encryptor.authenticate_additional_data(MAGIC + salt + nonce)
    with source.open("rb") as plain, destination.open("wb") as encrypted:
        encrypted.write(MAGIC + salt + nonce)
        while chunk := plain.read(CHUNK_SIZE):
            encrypted.write(encryptor.update(chunk))
        encrypted.write(encryptor.finalize())
        encrypted.write(encryptor.tag)


def _decrypt(source: Path, destination: Path, passphrase: str) -> None:
    minimum = len(MAGIC) + SALT_SIZE + NONCE_SIZE + TAG_SIZE
    if source.stat().st_size < minimum:
        raise ValueError("Recovery bundle is truncated")
    with source.open("rb") as encrypted:
        if encrypted.read(len(MAGIC)) != MAGIC:
            raise ValueError("Not an ELANORA recovery bundle")
        salt, nonce = encrypted.read(SALT_SIZE), encrypted.read(NONCE_SIZE)
        encrypted.seek(-TAG_SIZE, os.SEEK_END)
        tag = encrypted.read(TAG_SIZE)
        remaining = source.stat().st_size - minimum
        encrypted.seek(len(MAGIC) + SALT_SIZE + NONCE_SIZE)
        decryptor = Cipher(
            algorithms.AES(_key(passphrase, salt)), modes.GCM(nonce, tag)
        ).decryptor()
        decryptor.authenticate_additional_data(MAGIC + salt + nonce)
        with destination.open("wb") as plain:
            while remaining:
                chunk = encrypted.read(min(CHUNK_SIZE, remaining))
                if not chunk:
                    raise ValueError("Recovery bundle is truncated")
                remaining -= len(chunk)
                plain.write(decryptor.update(chunk))
            plain.write(decryptor.finalize())


def _safe_name(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or path.parts == ():
        raise ValueError(f"Unsafe recovery bundle path: {name}")
    return path


def _verify_archive(
    archive: Path, extraction_root: Path | None = None
) -> dict[str, object]:
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        if any(member.issym() or member.islnk() for member in members):
            raise ValueError("Recovery bundles may not contain links")
        try:
            manifest_member = tar.getmember("manifest.json")
            manifest_file = tar.extractfile(manifest_member)
            if manifest_file is None:
                raise ValueError("Recovery manifest is unreadable")
            manifest = json.load(manifest_file)
        except (KeyError, json.JSONDecodeError) as exc:
            raise ValueError("Recovery manifest is missing or invalid") from exc
        if manifest.get("format") != "elanora-recovery-v1":
            raise ValueError("Unsupported recovery bundle format")
        expected = {item["path"]: item for item in manifest.get("files", [])}
        actual_names = {member.name for member in members if member.isfile()} - {
            "manifest.json"
        }
        if actual_names != set(expected):
            raise ValueError("Recovery bundle contents do not match its manifest")
        for member in members:
            safe_path = _safe_name(member.name)
            if not member.isfile() or member.name == "manifest.json":
                continue
            source = tar.extractfile(member)
            if source is None:
                raise ValueError(f"Could not read {member.name}")
            digest = hashlib.sha256()
            size = 0
            target = None
            if extraction_root is not None:
                target_path = extraction_root.joinpath(*safe_path.parts)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target = target_path.open("wb")
            try:
                while chunk := source.read(CHUNK_SIZE):
                    digest.update(chunk)
                    size += len(chunk)
                    if target is not None:
                        target.write(chunk)
            finally:
                if target is not None:
                    target.close()
            item = expected[member.name]
            if size != item["size"] or digest.hexdigest() != item["sha256"]:
                raise ValueError(f"Recovery checksum mismatch: {member.name}")
            if extraction_root is not None:
                os.chmod(extraction_root.joinpath(*safe_path.parts), 0o600)
    return manifest


def verify_bundle(source: Path, passphrase: str) -> dict[str, object]:
    """Authenticate and checksum every file in an encrypted bundle."""
    with tempfile.TemporaryDirectory(prefix="elanora-verify-") as temporary:
        archive = Path(temporary) / "payload.tar.gz"
        _decrypt(source, archive, passphrase)
        manifest = _verify_archive(archive)
    return manifest


def extract_bundle(
    source: Path, destination: Path, passphrase: str
) -> dict[str, object]:
    """Verify and extract into a new or empty recovery-drill directory."""
    if destination.exists():
        raise FileExistsError("Recovery destination must not already exist")
    with tempfile.TemporaryDirectory(prefix="elanora-extract-") as temporary:
        archive = Path(temporary) / "payload.tar.gz"
        extracted = Path(temporary) / "restored"
        extracted.mkdir()
        _decrypt(source, archive, passphrase)
        manifest = _verify_archive(archive, extracted)
        destination.parent.mkdir(parents=True, exist_ok=True)
        extracted.replace(destination)
    return manifest
