"""Database utility functions for common operations."""

from collections.abc import Sequence
from typing import Any, TypeVar

from sqlalchemy import delete, exists, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.centralized_logging import get_logger

ModelType = TypeVar("ModelType", bound=DeclarativeBase)

logger = get_logger()

# asyncpg rejects statements with more than 32,767 bind parameters. Leave
# headroom for dialect/compiler changes and split every bulk operation by the
# actual number of columns supplied per row.
MAX_BULK_BIND_PARAMETERS = 30_000


class DatabaseUtils:
    """Reusable database operation utilities."""

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        model: type[ModelType],
        id_field: str,
        id_value: Any,
        options: list | None = None,
    ) -> ModelType | None:
        logger.info("get_by_id: model=%s id_field=%s", model.__name__, id_field)
        query = select(model).filter(getattr(model, id_field) == id_value)
        if options:
            for opt in options:
                query = query.options(opt)
        result = await db.execute(query)
        instance = result.scalar_one_or_none()
        logger.debug(f"get_by_id: found={instance is not None}")
        return instance

    @staticmethod
    async def get_all(
        db: AsyncSession, model: type[ModelType], options: list | None = None
    ) -> list[ModelType]:
        logger.info(f"get_all: model={model.__name__}")
        query = select(model)
        if options:
            for opt in options:
                query = query.options(opt)
        result = await db.execute(query)
        all_results = list(result.scalars().all())
        logger.debug(f"get_all: count={len(all_results)}")
        return all_results

    @staticmethod
    async def exists(
        db: AsyncSession, model: type[ModelType], field: str, value: Any
    ) -> bool:
        logger.info("exists: model=%s field=%s", model.__name__, field)
        result = await db.execute(
            select(getattr(model, field)).filter(getattr(model, field) == value)
        )
        exists = result.scalar_one_or_none() is not None
        logger.debug(f"exists: result={exists}")
        return exists

    @staticmethod
    async def create(db: AsyncSession, instance: ModelType) -> ModelType:
        logger.info("create: model=%s", type(instance).__name__)
        db.add(instance)
        return instance

    @staticmethod
    async def delete_by_id(
        db: AsyncSession,
        model: type[ModelType],
        id_field: str,
        id_value: Any,
    ) -> bool:
        """Delete one model instance by primary-key field, if it exists."""
        instance = await DatabaseUtils.get_by_id(db, model, id_field, id_value)
        if instance is None:
            return False
        await db.delete(instance)
        return True

    @staticmethod
    async def delete_by_filter(
        db: AsyncSession, model: type[ModelType], auto_commit: bool = False, **filters
    ) -> int:
        logger.info(
            "delete_by_filter: model=%s filter_fields=%s",
            model.__name__,
            sorted(filters),
        )
        query = select(model)
        for field, value in filters.items():
            query = query.filter(getattr(model, field) == value)
        result = await db.execute(query)
        instances = list(result.scalars().all())
        count = len(instances)
        for instance in instances:
            await db.delete(instance)
        logger.info(f"delete_by_filter: deleted count={count}")
        return count

    @staticmethod
    async def bulk_insert(
        db: AsyncSession,
        model: type[ModelType],
        values: list[dict],
        ignore_duplicates: bool = False,
    ) -> None:
        """Bulk insert records, optionally ignoring unique-key duplicates."""
        if not values:
            return
        column_count = max(len(row) for row in values)
        rows_per_batch = max(1, MAX_BULK_BIND_PARAMETERS // column_count)
        dialect_name = db.bind.dialect.name if db.bind is not None else ""
        for offset in range(0, len(values), rows_per_batch):
            batch = values[offset : offset + rows_per_batch]
            if ignore_duplicates and dialect_name == "postgresql":
                stmt = postgresql_insert(model).values(batch).on_conflict_do_nothing()
            elif ignore_duplicates and dialect_name == "sqlite":
                stmt = sqlite_insert(model).values(batch).on_conflict_do_nothing()
            else:
                stmt = insert(model).values(batch)
            await db.execute(stmt)

    @staticmethod
    async def update_by_filter(
        db: AsyncSession, model: type[ModelType], filters: dict, update_fields: dict
    ) -> int:
        """Update records matching filters with update_fields. Returns number of updated rows."""
        query = update(model)
        for field, value in filters.items():
            query = query.where(getattr(model, field) == value)
        query = query.values(**update_fields)
        result = await db.execute(query)
        return result.rowcount

    @staticmethod
    async def get_by_filter(
        db: AsyncSession,
        model: type[ModelType],
        filters: dict,
        order_by: list | None = None,
        options: list | None = None,
    ) -> list[ModelType]:
        """Get records matching filters, optionally ordered."""
        query = select(model)
        for field, value in filters.items():
            if isinstance(value, list):
                query = query.where(getattr(model, field).in_(tuple(value)))
            else:
                query = query.where(getattr(model, field) == value)
        if order_by:
            query = query.order_by(*order_by)
        if options:
            for opt in options:
                query = query.options(opt)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_one_by_filter(
        db: AsyncSession,
        model: type[ModelType],
        filters: dict,
        order_by: list | None = None,
        options: list | None = None,
    ) -> ModelType | None:
        """Get a single record matching filters, optionally ordered."""
        query = select(model)
        for field, value in filters.items():
            if isinstance(value, list):
                query = query.where(getattr(model, field).in_(tuple(value)))
            else:
                query = query.where(getattr(model, field) == value)
        if order_by:
            query = query.order_by(*order_by)
        if options:
            for opt in options:
                query = query.options(opt)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def paginate(
        db: AsyncSession,
        model: type[ModelType],
        page: int,
        page_size: int,
        filters: dict | None,
        options: list | None = None,
    ) -> list[ModelType]:
        """Paginate records with optional filters."""
        query = select(model)
        filters = filters or {}
        for field, value in filters.items():
            if isinstance(value, list):
                query = query.where(getattr(model, field).in_(tuple(value)))
            else:
                query = query.where(getattr(model, field) == value)
        if options:
            for opt in options:
                query = query.options(opt)
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def count(
        db: AsyncSession, model: type[ModelType], filters: dict | None
    ) -> int:
        """Count records matching optional filters."""
        query = select(func.count()).select_from(model)
        filters = filters or {}
        for field, value in filters.items():
            if isinstance(value, list):
                query = query.where(getattr(model, field).in_(tuple(value)))
            else:
                query = query.where(getattr(model, field) == value)
        result = await db.execute(query)
        return result.scalar_one()

    @staticmethod
    async def bulk_delete(
        db: AsyncSession, model: type[ModelType], where_clause
    ) -> int:
        """Bulk delete records matching the given where_clause.
        Returns the number of deleted rows.
        """
        logger.info("bulk_delete: model=%s", model.__name__)
        result = await db.execute(delete(model).where(where_clause))
        logger.info(f"bulk_delete: model={model.__name__} deleted={result.rowcount}")
        return result.rowcount if result.rowcount is not None else 0

    @staticmethod
    async def bulk_update(
        db: AsyncSession,
        model: type[ModelType],
        data: list[dict],
        pk_field: str,
    ) -> int:
        """Bulk update records for the given model.
        Each dict in data must include the primary key field.
        Returns the number of updated rows.
        """
        if not data:
            return 0
        total = 0
        for row in data:
            pk_value = row[pk_field]
            update_data = {k: v for k, v in row.items() if k != pk_field}
            result = await db.execute(
                update(model)
                .where(getattr(model, pk_field) == pk_value)
                .values(**update_data)
            )
            total += result.rowcount if result.rowcount else 0
        logger.info(f"bulk_update: model={model.__name__} updated={total}")
        return total

    @staticmethod
    async def get_orphaned_by_association(
        db: AsyncSession,
        main_model: type[ModelType],
        assoc_model: type[ModelType],
        main_id_field: str,
        assoc_main_id_field: str,
        assoc_parent_field: str,
        parent_id: int,
    ) -> list[ModelType]:
        """Fetch instances from main_model that are linked in assoc_model
        only to the given parent_id (via assoc_parent_field), and to no other parent.
        """
        main_id_col = getattr(main_model, main_id_field)
        assoc_main_id_col = getattr(assoc_model, assoc_main_id_field)
        assoc_parent_col = getattr(assoc_model, assoc_parent_field)

        stmt = (
            select(main_model)
            .join(assoc_model, assoc_main_id_col == main_id_col)
            .group_by(main_id_col)
            .having(
                func.count(assoc_parent_col) == 1,
                func.max(assoc_parent_col) == parent_id,
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_fully_orphaned(
        db,
        main_model,
        assoc_model,
        main_id_field: str,
        assoc_ref_field: str,
    ):
        """Return all main_model records whose main_id_field is NOT referenced in assoc_model.assoc_ref_field.
        Logs orphans and non-orphans with references.
        """
        main_id_col = getattr(main_model, main_id_field)
        assoc_ref_col = getattr(assoc_model, assoc_ref_field)

        # Get all main IDs
        all_main_ids_result = await db.execute(select(main_id_col))
        all_main_ids = {row[0] for row in all_main_ids_result}

        # Get all referenced IDs
        referenced_ids_result = await db.execute(select(assoc_ref_col))
        referenced_ids = {row[0] for row in referenced_ids_result if row[0] is not None}

        # Find orphans and non-orphans
        orphan_ids = all_main_ids - referenced_ids
        non_orphan_ids = all_main_ids & referenced_ids

        logger.info(
            "get_fully_orphaned: model=%s orphan_count=%s referenced_count=%s",
            main_model.__name__,
            len(orphan_ids),
            len(non_orphan_ids),
        )

        # Execute the reference lookup to preserve the historical query behavior,
        # but never serialize identifiers or association rows into logs.
        if non_orphan_ids:
            for oid in sorted(non_orphan_ids):
                refs = await db.execute(select(assoc_model).where(assoc_ref_col == oid))
                refs.scalars().all()

        # Return orphan objects
        if orphan_ids:
            query = select(main_model).where(main_id_col.in_(orphan_ids))
            result = await db.execute(query)
            orphans = list(result.scalars().all())
        else:
            orphans = []
        return orphans

    @staticmethod
    async def delete_fully_orphaned(
        db,
        main_model,
        assoc_model,
        main_id_field: str,
        assoc_ref_field: str,
    ) -> int:
        """Delete all main_model records whose main_id_field is NOT referenced in assoc_model.assoc_ref_field.

        Logs what is deleted.
        """
        orphans = await DatabaseUtils.get_fully_orphaned(
            db, main_model, assoc_model, main_id_field, assoc_ref_field
        )
        count = len(orphans)
        logger.info(
            "delete_fully_orphaned: model=%s count=%s",
            main_model.__name__,
            count,
        )
        for orphan in orphans:
            await db.delete(orphan)
        return count

    @staticmethod
    async def get_distinct_column_values(
        db: AsyncSession,
        model,
        column,
        filters: dict[str, Any] | None = None,
        in_filter: tuple | None = None,
        order_by=None,
    ) -> Sequence[Any]:
        """Utility to get distinct values for a column, with optional filters and IN clause.
        - model: SQLAlchemy model class
        - column: model.column to select
        - filters: dict of {column_name: value}
        - in_filter: tuple of (column, list_of_values)
        - order_by: model.column or list of columns
        """
        stmt = select(column).distinct()
        if filters:
            for k, v in filters.items():
                stmt = stmt.where(getattr(model, k) == v)
        if in_filter:
            col, values = in_filter
            stmt = stmt.where(col.in_(values))
        if order_by is not None:
            if isinstance(order_by, list):
                stmt = stmt.order_by(*order_by)
            else:
                stmt = stmt.order_by(order_by)
        result = await db.execute(stmt)
        return [row[0] for row in result.all()]

    @staticmethod
    async def get_all_with_related_exists(
        db: AsyncSession,
        model: type[ModelType],
        related_model: type[ModelType],
        related_field: str,
        model_field: str,
    ) -> list[ModelType]:
        """Returns all instances of `model` where at least one `related_model` exists
        such that related_model.<related_field> == model.<model_field>
        """
        stmt = select(model).where(
            exists().where(
                getattr(related_model, related_field) == getattr(model, model_field)
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_all_by_filter(db: AsyncSession, model, filters: dict):
        stmt = select(model).filter_by(**filters)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_with_join(
        db: AsyncSession,
        stmt: select,  # Pre-built SQLAlchemy select statement with joins
        as_dict: bool = False,  # Optional: return as dict if needed
    ) -> list[Any]:
        """Execute a select statement with joins and return results.

        Args:
            db: AsyncSession instance.
            stmt: SQLAlchemy select statement (e.g., with joins).
            as_dict: If True, return results as dicts (for non-ORM queries).

        Returns:
            List of results (ORM objects or dicts).

        """
        try:
            result = await db.execute(stmt)
            if as_dict:
                return [dict(row) for row in result.all()]
            return result.all()
        except Exception as e:
            logger.error("Database join query failed; error_type=%s", type(e).__name__)
            raise
