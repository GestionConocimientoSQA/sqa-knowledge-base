"""Conversiones SQLAlchemy model ↔ Pydantic entity.

Mantenemos las conversiones aisladas en este módulo para que los repositorios
queden enfocados en queries y los models y entities sigan independientes
entre sí.

Convenciones:
- `to_*_entity(model)` — model → domain (lectura desde DB).
- `to_*_model(entity)` — domain → model (escritura a DB; `update()` usa
  `model.__init__(...)` con todos los campos).
- Los timestamps `created_at`/`updated_at` los maneja la BD (server_default
  + onupdate) — los mappers de escritura NO los seteamos.
"""

from __future__ import annotations

from typing import Any

from sqa_kb.adapters.repositories.postgres import models
from sqa_kb.domain import entities
from sqa_kb.domain.value_objects import (
    ActivityType,
    CategoryCode,
    DocStatus,
    DocTypeCode,
    IngestionStatus,
    MessageRole,
    MessageStatus,
    ProjectMemberRole,
    RoleId,
    SessionMode,
    SessionStatus,
)

# Fase 9.1: ID del proyecto seed que aloja todos los datos pre-existentes.
# Se materializa con la migración `c8e2f5a1d3b6 → d4f9a8e2b1c3` y vive
# en `projects` para que los FKs sean satisfactibles desde el día 0 de
# Fase 9. En Fase 9.3, los servicios pasan `project_id` explícito desde
# el contexto del request; mientras tanto este es el default de los
# `new_*_model` para mantener compatibilidad con el código pre-9.3.
GK_GENERAL_PROJECT_ID = "00000000-0000-0000-0000-000000000001"

# ===========================================================================
# Users
# ===========================================================================


def to_user_entity(model: models.UserModel) -> entities.User:
    return entities.User(
        oid=model.oid,
        email=model.email,
        name=model.name,
        role_id=RoleId(model.role_id),
        carpetas_owned=[CategoryCode(c) for c in model.carpetas_owned],
        puede_gobernar_taxonomia=model.puede_gobernar_taxonomia,
        puede_aprobar_taxonomia=model.puede_aprobar_taxonomia,
        puede_ver_metricas_globales=model.puede_ver_metricas_globales,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_user_to_model(entity: entities.User, model: models.UserModel) -> None:
    """Copia campos editables del entity al model (no toca timestamps)."""
    model.email = entity.email
    model.name = entity.name
    model.role_id = str(entity.role_id)
    model.carpetas_owned = [str(c) for c in entity.carpetas_owned]
    model.puede_gobernar_taxonomia = entity.puede_gobernar_taxonomia
    model.puede_aprobar_taxonomia = entity.puede_aprobar_taxonomia
    model.puede_ver_metricas_globales = entity.puede_ver_metricas_globales


def new_user_model(entity: entities.User) -> models.UserModel:
    return models.UserModel(
        oid=entity.oid,
        email=entity.email,
        name=entity.name,
        role_id=str(entity.role_id),
        carpetas_owned=[str(c) for c in entity.carpetas_owned],
        puede_gobernar_taxonomia=entity.puede_gobernar_taxonomia,
        puede_aprobar_taxonomia=entity.puede_aprobar_taxonomia,
        puede_ver_metricas_globales=entity.puede_ver_metricas_globales,
    )


# ===========================================================================
# Taxonomy
# ===========================================================================


def to_category_entity(model: models.CategoryModel) -> entities.Category:
    return entities.Category(
        code=CategoryCode(model.code),
        label=model.label,
        docs=model.docs,
        vigentes=model.vigentes,
        autoritativos=model.autoritativos,
        score_avg=model.score_avg,
        obsolescencia=model.obsolescencia,
    )


def to_doc_type_entity(model: models.DocTypeModel) -> entities.DocType:
    return entities.DocType(code=DocTypeCode(model.code), label=model.label)


# ===========================================================================
# Documents
# ===========================================================================


def to_document_entity(model: models.DocumentModel) -> entities.Document:
    return entities.Document(
        id=model.id,
        project_id=model.project_id,
        titulo=model.titulo,
        carpeta=CategoryCode(model.carpeta),
        tipo=DocTypeCode(model.tipo),
        autoritativo=model.autoritativo,
        estado=DocStatus(model.estado),
        autor_oid=model.autor_oid,
        autor_name=model.autor_name,
        autor_role=model.autor_role,
        fecha=model.fecha,
        revision=model.revision,
        version=model.version,
        citas=model.citas,
        score=model.score,
        anonimizado=model.anonimizado,
        fragmentos=model.fragmentos,
        paginas=model.paginas,
        formato=model.formato,
        aprobador_name=model.aprobador_name,
        fecha_aprobacion=model.fecha_aprobacion,
        tags=list(model.tags),
        blob_path=model.blob_path,
    )


def to_document_detail_entity(
    model: models.DocumentModel,
    incoming_citations: list[entities.IncomingCitation] | None = None,
) -> entities.DocumentDetail:
    base = to_document_entity(model)
    return entities.DocumentDetail(
        **base.model_dump(),
        incoming_citations=incoming_citations or [],
        resumen=model.resumen,
    )


def new_document_model(
    entity: entities.Document,
    project_id: str = GK_GENERAL_PROJECT_ID,
) -> models.DocumentModel:
    # Si el entity ya trae `project_id`, lo respetamos; si no, fallback
    # al proyecto raíz (legacy / tests pre-9.3).
    effective_project_id = entity.project_id or project_id
    return models.DocumentModel(
        id=entity.id,
        project_id=effective_project_id,
        titulo=entity.titulo,
        carpeta=str(entity.carpeta),
        tipo=str(entity.tipo),
        autoritativo=entity.autoritativo,
        estado=str(entity.estado),
        autor_oid=entity.autor_oid,
        autor_name=entity.autor_name,
        autor_role=entity.autor_role,
        fecha=entity.fecha,
        revision=entity.revision,
        version=entity.version,
        citas=entity.citas,
        score=entity.score,
        anonimizado=entity.anonimizado,
        fragmentos=entity.fragmentos,
        paginas=entity.paginas,
        formato=entity.formato,
        aprobador_name=entity.aprobador_name,
        fecha_aprobacion=entity.fecha_aprobacion,
        tags=list(entity.tags),
        blob_path=entity.blob_path,
        resumen="",
    )


# ===========================================================================
# Sessions + Messages
# ===========================================================================


def to_session_entity(model: models.SessionModel) -> entities.Session:
    stage = model.current_stage
    parsed_stage: int | str | None = None
    if stage is not None:
        parsed_stage = int(stage) if stage.isdigit() else stage
    return entities.Session(
        id=model.id,
        owner_oid=model.owner_oid,
        mode=SessionMode(model.mode),
        title=model.title,
        status=SessionStatus(model.status),
        current_stage=parsed_stage,
        message_count=model.message_count,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def new_session_model(
    entity: entities.Session,
    project_id: str = GK_GENERAL_PROJECT_ID,
) -> models.SessionModel:
    stage_str: str | None = (
        str(entity.current_stage) if entity.current_stage is not None else None
    )
    return models.SessionModel(
        id=entity.id,
        project_id=project_id,
        owner_oid=entity.owner_oid,
        mode=str(entity.mode),
        title=entity.title,
        status=str(entity.status),
        current_stage=stage_str,
        message_count=entity.message_count,
        agent_state={},
    )


def to_message_entity(model: models.MessageModel) -> entities.Message:
    stage = model.stage
    parsed_stage: int | str | None = None
    if stage is not None:
        parsed_stage = int(stage) if stage.isdigit() else stage

    classification = (
        entities.ClassificationPayload(**model.classification)
        if model.classification
        else None
    )
    scoring = entities.ScoringPayload(**model.scoring) if model.scoring else None
    token_usage = (
        entities.TokenUsagePayload(**model.token_usage) if model.token_usage else None
    )
    citations = [entities.CitationPayload(**c) for c in model.citations]
    artifacts = [entities.DocumentArtifactPayload(**a) for a in model.artifacts]

    return entities.Message(
        id=model.id,
        session_id=model.session_id,
        role=MessageRole(model.role),
        content=model.content,
        stage=parsed_stage,
        status=MessageStatus(model.status),
        started_at=model.started_at,
        ended_at=model.ended_at,
        duration_ms=model.duration_ms,
        classification=classification,
        citations=citations,
        scoring=scoring,
        artifacts=artifacts,
        token_usage=token_usage,
        error=model.error_payload,
    )


def new_message_model(entity: entities.Message) -> models.MessageModel:
    stage_str: str | None = str(entity.stage) if entity.stage is not None else None
    return models.MessageModel(
        id=entity.id,
        session_id=entity.session_id,
        role=str(entity.role),
        content=entity.content,
        stage=stage_str,
        status=str(entity.status),
        started_at=entity.started_at,
        ended_at=entity.ended_at,
        duration_ms=entity.duration_ms,
        classification=(
            entity.classification.model_dump() if entity.classification else None
        ),
        citations=[c.model_dump() for c in entity.citations],
        scoring=entity.scoring.model_dump() if entity.scoring else None,
        artifacts=[a.model_dump() for a in entity.artifacts],
        token_usage=(entity.token_usage.model_dump() if entity.token_usage else None),
        cost_usd=entity.token_usage.cost_usd if entity.token_usage else 0.0,
        error_payload=entity.error_payload,
    )


# ===========================================================================
# Ingestion, Queries, Skills, AuditLog, Activity
# ===========================================================================


def to_ingestion_entity(model: models.IngestionItemModel) -> entities.IngestionItem:
    return entities.IngestionItem(
        id=model.id,
        project_id=model.project_id,
        filename=model.filename,
        size_bytes=model.size_bytes,
        paginas=model.paginas,
        carpeta_sugerida=(
            CategoryCode(model.carpeta_sugerida) if model.carpeta_sugerida else None
        ),
        tipo_sugerido=DocTypeCode(model.tipo_sugerido) if model.tipo_sugerido else None,
        aprobador_oid=model.aprobador_oid,
        aprobador_name=model.aprobador_name,
        fecha_aprobacion=model.fecha_aprobacion,
        fuente_original=model.fuente_original,
        version=model.version,
        status=IngestionStatus(model.status),
        uploaded_by_oid=model.uploaded_by_oid,
        uploaded_at=model.uploaded_at,
        blob_path=model.blob_path,
        error_detail=model.error_detail,
    )


def new_ingestion_model(
    entity: entities.IngestionItem,
) -> models.IngestionItemModel:
    """El `project_id` viene del entity (Fase 9.3) — antes había un default
    `gk-general` aquí mientras el wiring no lo cableaba; ahora es
    siempre obligatorio en la entity."""
    return models.IngestionItemModel(
        id=entity.id,
        project_id=entity.project_id,
        filename=entity.filename,
        size_bytes=entity.size_bytes,
        paginas=entity.paginas,
        carpeta_sugerida=(
            str(entity.carpeta_sugerida) if entity.carpeta_sugerida else None
        ),
        tipo_sugerido=str(entity.tipo_sugerido) if entity.tipo_sugerido else None,
        aprobador_oid=entity.aprobador_oid,
        aprobador_name=entity.aprobador_name,
        fecha_aprobacion=entity.fecha_aprobacion,
        fuente_original=entity.fuente_original,
        version=entity.version,
        status=str(entity.status),
        uploaded_by_oid=entity.uploaded_by_oid,
        blob_path=entity.blob_path,
        error_detail=entity.error_detail,
    )


def to_skill_entity(model: models.SkillModel) -> entities.Skill:
    return entities.Skill(
        id=model.id,
        name=model.name,
        description=model.description,
        body_markdown=model.body_markdown,
        enabled=model.enabled,
        version=model.version,
        updated_by_oid=model.updated_by_oid,
        updated_at=model.updated_at,
    )


def to_audit_entity(model: models.AuditLogModel) -> entities.AuditLog:
    return entities.AuditLog(
        id=model.id,
        actor_oid=model.actor_oid,
        event_type=model.event_type,
        resource_id=model.resource_id,
        metadata=dict(model.audit_metadata),
        at=model.at,
    )


def new_audit_model(entity: entities.AuditLog) -> models.AuditLogModel:
    return models.AuditLogModel(
        id=entity.id,
        actor_oid=entity.actor_oid,
        event_type=entity.event_type,
        resource_id=entity.resource_id,
        audit_metadata=dict(entity.metadata),
        at=entity.at,
    )


def to_activity_entity(model: models.RecentActivityModel) -> entities.RecentActivityItem:
    return entities.RecentActivityItem(
        id=model.id,
        type=ActivityType(model.type),
        actor=entities.ActorRef(oid=model.actor_oid, name=model.actor_name),
        at=model.at,
        summary=model.summary,
        ref_url=model.ref_url,
    )


# ===========================================================================
# Projects + ProjectMembers (Fase 9.1)
# ===========================================================================


def to_project_entity(model: models.ProjectModel) -> entities.Project:
    return entities.Project(
        id=model.id,
        slug=model.slug,
        name=model.name,
        description=model.description,
        owner_oid=model.owner_oid,
        created_at=model.created_at,
        archived_at=model.archived_at,
    )


def new_project_model(entity: entities.Project) -> models.ProjectModel:
    return models.ProjectModel(
        id=entity.id,
        slug=entity.slug,
        name=entity.name,
        description=entity.description,
        owner_oid=entity.owner_oid,
        archived_at=entity.archived_at,
    )


def to_project_member_entity(
    model: models.ProjectMemberModel,
) -> entities.ProjectMember:
    return entities.ProjectMember(
        project_id=model.project_id,
        user_oid=model.user_oid,
        role=ProjectMemberRole(model.role),
        added_at=model.added_at,
    )


def new_project_member_model(
    entity: entities.ProjectMember,
) -> models.ProjectMemberModel:
    return models.ProjectMemberModel(
        project_id=entity.project_id,
        user_oid=entity.user_oid,
        role=str(entity.role),
    )


# Suppress unused import warning if Pydantic types are referenced elsewhere.
_ = Any
