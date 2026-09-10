import asyncio
import hashlib
import io
import uuid
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.audit_event import AuditEvent
from app.model.instance import Instance
from app.model.instance_asset import InstanceAsset
from app.model.user import User
from app.storage.assets import get_asset_storage

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
OUTPUT_SIZE = (512, 512)


def normalize_logo(content: bytes) -> tuple[bytes, int, int]:
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("Logo must be between 1 byte and 5 MB")
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(
                io.BytesIO(content), formats=("PNG", "JPEG", "WEBP")
            ) as image:
                image.load()
                converted = ImageOps.exif_transpose(image).convert("RGBA")
                converted.thumbnail(OUTPUT_SIZE, Image.Resampling.LANCZOS)
                canvas = Image.new("RGBA", OUTPUT_SIZE, (255, 255, 255, 0))
                canvas.alpha_composite(
                    converted,
                    ((512 - converted.width) // 2, (512 - converted.height) // 2),
                )
                output = io.BytesIO()
                canvas.save(output, format="WEBP", lossless=True, method=4)
                return output.getvalue(), converted.width, converted.height
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
    ) as error:
        raise ValueError("Logo must be a valid PNG, JPEG, or WebP image") from error


async def replace_logo(
    db: AsyncSession, instance: Instance, user: User, content: bytes
) -> InstanceAsset:
    normalized, width, height = await asyncio.to_thread(normalize_logo, content)
    asset_id = uuid.uuid4()
    key = f"instances/{instance.installation_id}/logos/{asset_id}.webp"
    storage = get_asset_storage()
    await asyncio.to_thread(storage.put, key, normalized)
    asset = InstanceAsset(
        asset_id=asset_id,
        instance_id=instance.instance_id,
        kind="logo",
        storage_key=key,
        content_type="image/webp",
        byte_size=len(normalized),
        sha256=hashlib.sha256(normalized).hexdigest(),
        width=width,
        height=height,
        created_by=user.user_id,
    )
    db.add(asset)
    await db.flush()
    instance.logo_asset_id = asset_id
    db.add(
        AuditEvent(
            actor_user_id=user.user_id,
            action="instance.logo.replaced",
            resource_type="instance",
            resource_id=str(instance.installation_id),
            details={"asset_id": str(asset_id), "sha256": asset.sha256},
        )
    )
    await db.commit()
    return asset


async def read_logo(db: AsyncSession, instance: Instance) -> bytes | None:
    if instance.logo_asset_id is None:
        return None
    asset = await db.get(InstanceAsset, instance.logo_asset_id)
    if asset is None:
        return None
    content = await asyncio.to_thread(
        get_asset_storage().read,
        asset.storage_key,
    )
    if (
        len(content) != asset.byte_size
        or hashlib.sha256(content).hexdigest() != asset.sha256
    ):
        raise ValueError("Stored institution logo failed its integrity check")
    return content
