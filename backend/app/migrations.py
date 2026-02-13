"""Migration helpers for adding new columns to existing SQLite tables.

SQLite does not support full ALTER TABLE, but ALTER TABLE ADD COLUMN works.
This module provides idempotent migration functions.
"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.analysis import Analysis, AnalysisStatus

logger = logging.getLogger(__name__)

# Columns to add to the analyses table: (column_name, column_definition)
_NEW_COLUMNS = [
    ("is_favorite", "BOOLEAN DEFAULT 0"),
    ("property_address", "VARCHAR(500)"),
    ("property_name", "VARCHAR(200)"),
    ("property_type", "VARCHAR(100)"),
    ("area", "FLOAT"),
    ("appraised_value", "INTEGER"),
    ("recommendation", "VARCHAR(20)"),
    ("expected_roi", "FLOAT"),
    ("confidence_score", "FLOAT"),
]


async def run_migrations(session: AsyncSession) -> None:
    """Add new columns to the analyses table if they don't already exist."""
    # Get existing columns
    result = await session.execute(text("PRAGMA table_info(analyses)"))
    existing_columns = {row[1] for row in result.fetchall()}

    for col_name, col_def in _NEW_COLUMNS:
        if col_name not in existing_columns:
            await session.execute(
                text(f"ALTER TABLE analyses ADD COLUMN {col_name} {col_def}")
            )
            logger.info("Added column %s to analyses table", col_name)

    await session.commit()


def extract_summary_fields(analysis: Analysis) -> None:
    """Extract summary fields from parsed_documents and report JSON columns.

    This mutates the analysis object in-place. Call before db.commit().
    """
    parsed = analysis.parsed_documents or {}
    report = analysis.report or {}

    # From parsed_documents.registry
    registry = parsed.get("registry", {})
    if registry:
        if registry.get("property_address"):
            analysis.property_address = registry["property_address"]
        if registry.get("building_name"):
            analysis.property_name = registry["building_name"]
        if registry.get("property_type"):
            analysis.property_type = registry["property_type"]
        if registry.get("area"):
            analysis.area = registry["area"]

    # From parsed_documents.appraisal
    appraisal = parsed.get("appraisal", {})
    if appraisal and appraisal.get("appraised_value"):
        analysis.appraised_value = appraisal["appraised_value"]

    # From parsed_documents.status_report (alternative source)
    status_report = parsed.get("status_report", {})
    if status_report:
        if not analysis.property_address and status_report.get("property_address"):
            analysis.property_address = status_report["property_address"]
        if not analysis.property_name and status_report.get("building_name"):
            analysis.property_name = status_report["building_name"]
        if not analysis.property_type and status_report.get("property_type"):
            analysis.property_type = status_report["property_type"]
        if not analysis.area and status_report.get("area"):
            analysis.area = status_report["area"]

    # From parsed_documents.sale_item
    sale_item = parsed.get("sale_item", {})
    if sale_item and not analysis.case_number:
        if sale_item.get("case_number"):
            analysis.case_number = sale_item["case_number"]

    # From report
    if report.get("recommendation"):
        analysis.recommendation = report["recommendation"]
    if report.get("expected_roi") is not None:
        analysis.expected_roi = report["expected_roi"]
    if report.get("confidence_score") is not None:
        analysis.confidence_score = report["confidence_score"]


async def backfill_summary_fields() -> None:
    """Backfill summary fields for all DONE analyses where recommendation is NULL."""
    async with async_session() as db:
        from sqlalchemy import select

        result = await db.execute(
            select(Analysis).where(
                Analysis.status == AnalysisStatus.DONE,
                Analysis.recommendation.is_(None),
            )
        )
        analyses = result.scalars().all()

        if not analyses:
            logger.info("No analyses to backfill")
            return

        count = 0
        for analysis in analyses:
            extract_summary_fields(analysis)
            count += 1

        await db.commit()
        logger.info("Backfilled summary fields for %d analyses", count)
