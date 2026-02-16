"""تعريفات مخطط قاعدة البيانات المعتمدة للنظام.

توفر هذه الوحدة بيانات المخطط المطلوبة وقوائم الجداول المسموح بها
بهدف تقليل التعقيد في منطق التحقق وضمان وضوح الحدود البنيوية.
"""

from typing import Final, NotRequired, TypedDict

__all__ = [
    "REQUIRED_SCHEMA",
    "_ALLOWED_TABLES",
    "SchemaValidationResult",
    "TableSchemaConfig",
]


class TableSchemaConfig(TypedDict):
    """تمثيل تعريف جدول مع أوامر الإصلاح والفهارس المطلوبة."""

    columns: list[str]
    auto_fix: dict[str, str]
    indexes: dict[str, str]
    index_names: NotRequired[dict[str, str]]
    create_table: NotRequired[str]


class SchemaValidationResult(TypedDict):
    """نتيجة التحقق من المخطط مع تفاصيل العناصر الناقصة أو المُعالجة."""

    status: str
    checked_tables: list[str]
    missing_columns: list[str]
    fixed_columns: list[str]
    missing_indexes: list[str]
    fixed_indexes: list[str]
    errors: list[str]


_ALLOWED_TABLES: Final[frozenset[str]] = frozenset(
    {
        "admin_conversations",
        "audit_log",
        "customer_conversations",
        "customer_messages",
        "permissions",
        "refresh_tokens",
        "role_permissions",
        "roles",
        "user_roles",
        "users",
        "missions",
        "mission_plans",
        "tasks",
        "mission_events",
        "prompt_templates",
        "generated_prompts",
        "knowledge_nodes",
        "knowledge_edges",
    }
)


REQUIRED_SCHEMA: Final[dict[str, TableSchemaConfig]] = {
    "admin_conversations": {
        "columns": [
            "id",
            "title",
            "user_id",
            "conversation_type",
            "linked_mission_id",
            "created_at",
        ],
        "auto_fix": {
            "linked_mission_id": 'ALTER TABLE "admin_conversations" ADD COLUMN "linked_mission_id" INTEGER'
        },
        "indexes": {
            "linked_mission_id": 'CREATE INDEX IF NOT EXISTS "ix_admin_conversations_linked_mission_id" ON "admin_conversations"("linked_mission_id")'
        },
        "index_names": {"linked_mission_id": "ix_admin_conversations_linked_mission_id"},
        "create_table": (
            'CREATE TABLE IF NOT EXISTS "admin_conversations"('
            '"id" SERIAL PRIMARY KEY,'
            '"title" VARCHAR(500) NOT NULL,'
            '"user_id" INTEGER NOT NULL REFERENCES "users"("id") ON DELETE CASCADE,'
            "\"conversation_type\" VARCHAR(50) DEFAULT 'general',"
            '"linked_mission_id" INTEGER,'
            '"created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()'
            ")"
        ),
    },
    "customer_conversations": {
        "columns": [
            "id",
            "title",
            "user_id",
            "created_at",
        ],
        "auto_fix": {},
        "indexes": {
            "user_id": 'CREATE INDEX IF NOT EXISTS "ix_customer_conversations_user_id" ON "customer_conversations"("user_id")'
        },
        "index_names": {"user_id": "ix_customer_conversations_user_id"},
        "create_table": (
            'CREATE TABLE IF NOT EXISTS "customer_conversations"('
            '"id" SERIAL PRIMARY KEY,'
            '"title" VARCHAR(500) NOT NULL,'
            '"user_id" INTEGER NOT NULL REFERENCES "users"("id") ON DELETE CASCADE,'
            '"created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()'
            ")"
        ),
    },
    "customer_messages": {
        "columns": [
            "id",
            "conversation_id",
            "role",
            "content",
            "policy_flags",
            "created_at",
        ],
        "auto_fix": {},
        "indexes": {
            "conversation_id": 'CREATE INDEX IF NOT EXISTS "ix_customer_messages_conversation_id" ON "customer_messages"("conversation_id")'
        },
        "index_names": {"conversation_id": "ix_customer_messages_conversation_id"},
        "create_table": (
            'CREATE TABLE IF NOT EXISTS "customer_messages"('
            '"id" SERIAL PRIMARY KEY,'
            '"conversation_id" INTEGER NOT NULL REFERENCES "customer_conversations"("id") ON DELETE CASCADE,'
            '"role" VARCHAR(50) NOT NULL,'
            '"content" TEXT NOT NULL,'
            '"policy_flags" TEXT,'
            '"created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()'
            ")"
        ),
    },
    "users": {
        "columns": [
            "id",
            "external_id",
            "full_name",
            "email",
            "password_hash",
            "is_admin",
            "is_active",
            "status",
            "created_at",
            "updated_at",
        ],
        "auto_fix": {
            "external_id": 'ALTER TABLE "users" ADD COLUMN "external_id" VARCHAR(36)',
            "is_active": 'ALTER TABLE "users" ADD COLUMN "is_active" BOOLEAN NOT NULL DEFAULT TRUE',
            "status": 'ALTER TABLE "users" ADD COLUMN "status" VARCHAR(50) NOT NULL DEFAULT \'active\'',
        },
        "indexes": {
            "external_id": 'CREATE UNIQUE INDEX IF NOT EXISTS "ix_users_external_id" ON "users"("external_id")'
        },
        "index_names": {"external_id": "ix_users_external_id"},
        "create_table": (
            'CREATE TABLE IF NOT EXISTS "users"('
            '"id" SERIAL PRIMARY KEY,'
            '"external_id" VARCHAR(36) UNIQUE,'
            '"full_name" VARCHAR(150) NOT NULL,'
            '"email" VARCHAR(150) NOT NULL UNIQUE,'
            '"password_hash" VARCHAR(256),'
            '"is_admin" BOOLEAN DEFAULT FALSE,'
            '"is_active" BOOLEAN DEFAULT TRUE,'
            "\"status\" VARCHAR(50) DEFAULT 'active',"
            '"created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),'
            '"updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()'
            ")"
        ),
    },
    "roles": {
        "columns": [
            "id",
            "name",
            "description",
            "created_at",
            "updated_at",
        ],
        "auto_fix": {},
        "indexes": {
            "name": 'CREATE UNIQUE INDEX IF NOT EXISTS "ix_roles_name" ON "roles"("name")',
        },
        "index_names": {"name": "ix_roles_name"},
        "create_table": (
            'CREATE TABLE IF NOT EXISTS "roles"('
            '"id" SERIAL PRIMARY KEY,'
            '"name" VARCHAR(100) NOT NULL UNIQUE,'
            '"description" VARCHAR(255),'
            '"created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),'
            '"updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()'
            ")"
        ),
    },
    "permissions": {
        "columns": [
            "id",
            "name",
            "description",
            "created_at",
            "updated_at",
        ],
        "auto_fix": {},
        "indexes": {
            "name": 'CREATE UNIQUE INDEX IF NOT EXISTS "ix_permissions_name" ON "permissions"("name")',
        },
        "index_names": {"name": "ix_permissions_name"},
        "create_table": (
            'CREATE TABLE IF NOT EXISTS "permissions"('
            '"id" SERIAL PRIMARY KEY,'
            '"name" VARCHAR(100) NOT NULL UNIQUE,'
            '"description" VARCHAR(255),'
            '"created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),'
            '"updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()'
            ")"
        ),
    },
    "user_roles": {
        "columns": ["user_id", "role_id", "created_at"],
        "auto_fix": {},
        "indexes": {
            "user_id": 'CREATE INDEX IF NOT EXISTS "ix_user_roles_user_id" ON "user_roles"("user_id")',
            "role_id": 'CREATE INDEX IF NOT EXISTS "ix_user_roles_role_id" ON "user_roles"("role_id")',
        },
        "index_names": {
            "user_id": "ix_user_roles_user_id",
            "role_id": "ix_user_roles_role_id",
        },
        "create_table": (
            'CREATE TABLE IF NOT EXISTS "user_roles"('
            '"user_id" INTEGER NOT NULL REFERENCES "users"("id") ON DELETE CASCADE,'
            '"role_id" INTEGER NOT NULL REFERENCES "roles"("id") ON DELETE CASCADE,'
            '"created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),'
            'PRIMARY KEY ("user_id", "role_id")'
            ")"
        ),
    },
    "role_permissions": {
        "columns": ["role_id", "permission_id", "created_at"],
        "auto_fix": {},
        "indexes": {
            "role_id": 'CREATE INDEX IF NOT EXISTS "ix_role_permissions_role_id" ON "role_permissions"("role_id")',
            "permission_id": 'CREATE INDEX IF NOT EXISTS "ix_role_permissions_permission_id" ON "role_permissions"("permission_id")',
        },
        "index_names": {
            "role_id": "ix_role_permissions_role_id",
            "permission_id": "ix_role_permissions_permission_id",
        },
        "create_table": (
            'CREATE TABLE IF NOT EXISTS "role_permissions"('
            '"role_id" INTEGER NOT NULL REFERENCES "roles"("id") ON DELETE CASCADE,'
            '"permission_id" INTEGER NOT NULL REFERENCES "permissions"("id") ON DELETE CASCADE,'
            '"created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),'
            'PRIMARY KEY ("role_id", "permission_id")'
            ")"
        ),
    },
    "refresh_tokens": {
        "columns": [
            "id",
            "token_id",
            "family_id",
            "user_id",
            "hashed_token",
            "expires_at",
            "revoked_at",
            "replaced_by_token_id",
            "created_ip",
            "user_agent",
            "created_at",
        ],
        "auto_fix": {
            "family_id": 'ALTER TABLE "refresh_tokens" ADD COLUMN "family_id" VARCHAR(36) NOT NULL DEFAULT \'unknown\'',
            "replaced_by_token_id": 'ALTER TABLE "refresh_tokens" ADD COLUMN "replaced_by_token_id" VARCHAR(36)',
            "created_ip": 'ALTER TABLE "refresh_tokens" ADD COLUMN "created_ip" VARCHAR(64)',
            "user_agent": 'ALTER TABLE "refresh_tokens" ADD COLUMN "user_agent" VARCHAR(255)',
        },
        "indexes": {
            "user_id": 'CREATE INDEX IF NOT EXISTS "ix_refresh_tokens_user_id" ON "refresh_tokens"("user_id")',
            "expires_at": 'CREATE INDEX IF NOT EXISTS "ix_refresh_tokens_expires_at" ON "refresh_tokens"("expires_at")',
            "token_id": 'CREATE UNIQUE INDEX IF NOT EXISTS "ix_refresh_tokens_token_id" ON "refresh_tokens"("token_id")',
            "family_id": 'CREATE INDEX IF NOT EXISTS "ix_refresh_tokens_family_id" ON "refresh_tokens"("family_id")',
            "replaced_by_token_id": 'CREATE INDEX IF NOT EXISTS "ix_refresh_tokens_replaced_by_token_id" ON "refresh_tokens"("replaced_by_token_id")',
        },
        "index_names": {
            "user_id": "ix_refresh_tokens_user_id",
            "expires_at": "ix_refresh_tokens_expires_at",
            "token_id": "ix_refresh_tokens_token_id",
            "family_id": "ix_refresh_tokens_family_id",
            "replaced_by_token_id": "ix_refresh_tokens_replaced_by_token_id",
        },
        "create_table": (
            'CREATE TABLE IF NOT EXISTS "refresh_tokens"('
            '"id" SERIAL PRIMARY KEY,'
            '"token_id" VARCHAR(36) NOT NULL UNIQUE,'
            '"family_id" VARCHAR(36) NOT NULL,'
            '"user_id" INTEGER NOT NULL REFERENCES "users"("id") ON DELETE CASCADE,'
            '"hashed_token" VARCHAR(255) NOT NULL,'
            '"expires_at" TIMESTAMPTZ NOT NULL,'
            '"revoked_at" TIMESTAMPTZ,'
            '"replaced_by_token_id" VARCHAR(36),'
            '"created_ip" VARCHAR(64),'
            '"user_agent" VARCHAR(255),'
            '"created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()'
            ")"
        ),
    },
    "audit_log": {
        "columns": [
            "id",
            "actor_user_id",
            "action",
            "target_type",
            "target_id",
            "metadata",
            "ip",
            "user_agent",
            "created_at",
        ],
        "auto_fix": {},
        "indexes": {
            "actor_user_id": 'CREATE INDEX IF NOT EXISTS "ix_audit_log_actor_user_id" ON "audit_log"("actor_user_id")',
            "created_at": 'CREATE INDEX IF NOT EXISTS "ix_audit_log_created_at" ON "audit_log"("created_at")',
        },
        "index_names": {
            "actor_user_id": "ix_audit_log_actor_user_id",
            "created_at": "ix_audit_log_created_at",
        },
        "create_table": (
            'CREATE TABLE IF NOT EXISTS "audit_log"('
            '"id" SERIAL PRIMARY KEY,'
            '"actor_user_id" INTEGER REFERENCES "users"("id") ON DELETE SET NULL,'
            '"action" VARCHAR(150) NOT NULL,'
            '"target_type" VARCHAR(100) NOT NULL,'
            '"target_id" VARCHAR(150),'
            "\"metadata\" JSON NOT NULL DEFAULT '{}',"
            '"ip" VARCHAR(64),'
            '"user_agent" VARCHAR(255),'
            '"created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()'
            ")"
        ),
    },
    "missions": {
        "columns": [
            "id",
            "objective",
            "status",
            "initiator_id",
            "active_plan_id",
            "idempotency_key",
            "locked",
            "result_summary",
            "total_cost_usd",
            "adaptive_cycles",
            "created_at",
            "updated_at",
        ],
        "auto_fix": {
            "idempotency_key": 'ALTER TABLE "missions" ADD COLUMN "idempotency_key" VARCHAR(128)',
            "locked": 'ALTER TABLE "missions" ADD COLUMN "locked" BOOLEAN DEFAULT FALSE',
            "result_summary": 'ALTER TABLE "missions" ADD COLUMN "result_summary" TEXT',
            "total_cost_usd": 'ALTER TABLE "missions" ADD COLUMN "total_cost_usd" FLOAT',
            "adaptive_cycles": 'ALTER TABLE "missions" ADD COLUMN "adaptive_cycles" INTEGER DEFAULT 0',
        },
        "indexes": {
            "initiator_id": 'CREATE INDEX IF NOT EXISTS "ix_missions_initiator_id" ON "missions"("initiator_id")',
            "idempotency_key": 'CREATE UNIQUE INDEX IF NOT EXISTS "ix_missions_idempotency_key" ON "missions"("idempotency_key")',
        },
        "index_names": {
            "initiator_id": "ix_missions_initiator_id",
            "idempotency_key": "ix_missions_idempotency_key",
        },
        "create_table": (
            'CREATE TABLE IF NOT EXISTS "missions"('
            '"id" SERIAL PRIMARY KEY,'
            '"objective" TEXT,'
            "\"status\" VARCHAR(50) DEFAULT 'pending',"
            '"initiator_id" INTEGER NOT NULL REFERENCES "users"("id"),'
            '"active_plan_id" INTEGER,'
            '"idempotency_key" VARCHAR(128) UNIQUE,'
            '"locked" BOOLEAN DEFAULT FALSE,'
            '"result_summary" TEXT,'
            '"total_cost_usd" FLOAT,'
            '"adaptive_cycles" INTEGER DEFAULT 0,'
            '"created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),'
            '"updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()'
            ")"
        ),
    },
    "mission_plans": {
        "columns": [
            "id",
            "mission_id",
            "version",
            "planner_name",
            "status",
            "score",
            "rationale",
            "raw_json",
            "stats_json",
            "warnings_json",
            "content_hash",
            "created_at",
        ],
        "auto_fix": {},
        "indexes": {
            "mission_id": 'CREATE INDEX IF NOT EXISTS "ix_mission_plans_mission_id" ON "mission_plans"("mission_id")'
        },
        "index_names": {"mission_id": "ix_mission_plans_mission_id"},
        "create_table": (
            'CREATE TABLE IF NOT EXISTS "mission_plans"('
            '"id" SERIAL PRIMARY KEY,'
            '"mission_id" INTEGER NOT NULL REFERENCES "missions"("id"),'
            '"version" INTEGER DEFAULT 1,'
            '"planner_name" VARCHAR(100) NOT NULL,'
            "\"status\" VARCHAR(50) DEFAULT 'draft',"
            '"score" FLOAT DEFAULT 0.0,'
            '"rationale" TEXT,'
            '"raw_json" TEXT,'
            '"stats_json" TEXT,'
            '"warnings_json" TEXT,'
            '"content_hash" VARCHAR(64),'
            '"created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()'
            ")"
        ),
    },
    "tasks": {
        "columns": [
            "id",
            "mission_id",
            "plan_id",
            "task_key",
            "description",
            "tool_name",
            "tool_args_json",
            "status",
            "attempt_count",
            "max_attempts",
            "priority",
            "risk_level",
            "criticality",
            "depends_on_json",
            "result_text",
            "result_meta_json",
            "error_text",
            "started_at",
            "finished_at",
            "next_retry_at",
            "duration_ms",
            "created_at",
            "updated_at",
        ],
        "auto_fix": {},
        "indexes": {
            "mission_id": 'CREATE INDEX IF NOT EXISTS "ix_tasks_mission_id" ON "tasks"("mission_id")',
            "plan_id": 'CREATE INDEX IF NOT EXISTS "ix_tasks_plan_id" ON "tasks"("plan_id")',
        },
        "index_names": {"mission_id": "ix_tasks_mission_id", "plan_id": "ix_tasks_plan_id"},
        "create_table": (
            'CREATE TABLE IF NOT EXISTS "tasks"('
            '"id" SERIAL PRIMARY KEY,'
            '"mission_id" INTEGER NOT NULL REFERENCES "missions"("id"),'
            '"plan_id" INTEGER REFERENCES "mission_plans"("id"),'
            '"task_key" VARCHAR(50) NOT NULL,'
            '"description" TEXT,'
            '"tool_name" VARCHAR(100),'
            '"tool_args_json" TEXT,'
            "\"status\" VARCHAR(50) DEFAULT 'pending',"
            '"attempt_count" INTEGER DEFAULT 0,'
            '"max_attempts" INTEGER DEFAULT 3,'
            '"priority" INTEGER DEFAULT 0,'
            '"risk_level" VARCHAR(50),'
            '"criticality" VARCHAR(50),'
            '"depends_on_json" TEXT,'
            '"result_text" TEXT,'
            '"result_meta_json" TEXT,'
            '"error_text" TEXT,'
            '"started_at" TIMESTAMPTZ,'
            '"finished_at" TIMESTAMPTZ,'
            '"next_retry_at" TIMESTAMPTZ,'
            '"duration_ms" INTEGER DEFAULT 0,'
            '"created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),'
            '"updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()'
            ")"
        ),
    },
    "mission_events": {
        "columns": ["id", "mission_id", "event_type", "payload_json", "created_at"],
        "auto_fix": {"payload_json": 'ALTER TABLE "mission_events" ADD COLUMN "payload_json" TEXT'},
        "indexes": {
            "mission_id": 'CREATE INDEX IF NOT EXISTS "ix_mission_events_mission_id" ON "mission_events"("mission_id")'
        },
        "index_names": {"mission_id": "ix_mission_events_mission_id"},
        "create_table": (
            'CREATE TABLE IF NOT EXISTS "mission_events"('
            '"id" SERIAL PRIMARY KEY,'
            '"mission_id" INTEGER NOT NULL REFERENCES "missions"("id"),'
            '"event_type" VARCHAR(50) NOT NULL,'
            '"payload_json" TEXT,'
            '"created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()'
            ")"
        ),
    },
    "prompt_templates": {
        "columns": ["id", "name", "template"],
        "auto_fix": {
            "template": 'ALTER TABLE "prompt_templates" ADD COLUMN "template" TEXT NOT NULL DEFAULT \'\''
        },
        "indexes": {
            "name": 'CREATE UNIQUE INDEX IF NOT EXISTS "ix_prompt_templates_name" ON "prompt_templates"("name")'
        },
        "index_names": {"name": "ix_prompt_templates_name"},
        "create_table": (
            'CREATE TABLE IF NOT EXISTS "prompt_templates"('
            '"id" SERIAL PRIMARY KEY,'
            '"name" VARCHAR(255) NOT NULL UNIQUE,'
            '"template" TEXT NOT NULL'
            ")"
        ),
    },
    "generated_prompts": {
        "columns": ["id", "prompt", "template_id"],
        "auto_fix": {
            "prompt": 'ALTER TABLE "generated_prompts" ADD COLUMN "prompt" TEXT NOT NULL DEFAULT \'\''
        },
        "indexes": {
            "template_id": 'CREATE INDEX IF NOT EXISTS "ix_generated_prompts_template_id" ON "generated_prompts"("template_id")'
        },
        "index_names": {"template_id": "ix_generated_prompts_template_id"},
        "create_table": (
            'CREATE TABLE IF NOT EXISTS "generated_prompts"('
            '"id" SERIAL PRIMARY KEY,'
            '"prompt" TEXT NOT NULL,'
            '"template_id" INTEGER NOT NULL REFERENCES "prompt_templates"("id")'
            ")"
        ),
    },
    "knowledge_nodes": {
        "columns": [
            "id",
            "label",
            "name",
            "content",
            "embedding",
            "search_vector",
            "metadata",
            "created_at",
        ],
        "auto_fix": {
            "embedding": 'ALTER TABLE "knowledge_nodes" ALTER COLUMN "embedding" TYPE vector(1024)',
            "search_vector": 'ALTER TABLE "knowledge_nodes" ADD COLUMN "search_vector" tsvector GENERATED ALWAYS AS (to_tsvector(\'simple\', "name" || \' \' || COALESCE("content", \'\'))) STORED',
        },
        "indexes": {
            "embedding": 'CREATE INDEX IF NOT EXISTS "ix_knowledge_nodes_embedding" ON "knowledge_nodes" USING hnsw ("embedding" vector_cosine_ops)',
            "name": 'CREATE INDEX IF NOT EXISTS "ix_knowledge_nodes_name" ON "knowledge_nodes"("name")',
            "search_vector": 'CREATE INDEX IF NOT EXISTS "ix_knowledge_nodes_search_vector" ON "knowledge_nodes" USING GIN ("search_vector")',
        },
        "index_names": {
            "embedding": "ix_knowledge_nodes_embedding",
            "name": "ix_knowledge_nodes_name",
            "search_vector": "ix_knowledge_nodes_search_vector",
        },
        "create_table": (
            'CREATE TABLE IF NOT EXISTS "knowledge_nodes"('
            '"id" UUID PRIMARY KEY,'
            '"label" VARCHAR(50),'
            '"name" VARCHAR(255) NOT NULL,'
            '"content" TEXT,'
            '"embedding" vector(1024),'
            "\"search_vector\" tsvector GENERATED ALWAYS AS (to_tsvector('simple', \"name\" || ' ' || COALESCE(\"content\", ''))) STORED,"
            "\"metadata\" JSONB DEFAULT '{}',"
            '"created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()'
            ")"
        ),
    },
    "knowledge_edges": {
        "columns": [
            "id",
            "source_id",
            "target_id",
            "relation",
            "properties",
            "created_at",
        ],
        "auto_fix": {},
        "indexes": {
            "source_id": 'CREATE INDEX IF NOT EXISTS "ix_knowledge_edges_source_id" ON "knowledge_edges"("source_id")',
            "target_id": 'CREATE INDEX IF NOT EXISTS "ix_knowledge_edges_target_id" ON "knowledge_edges"("target_id")',
        },
        "index_names": {
            "source_id": "ix_knowledge_edges_source_id",
            "target_id": "ix_knowledge_edges_target_id",
        },
        "create_table": (
            'CREATE TABLE IF NOT EXISTS "knowledge_edges"('
            '"id" UUID PRIMARY KEY,'
            '"source_id" UUID NOT NULL REFERENCES "knowledge_nodes"("id") ON DELETE CASCADE,'
            '"target_id" UUID NOT NULL REFERENCES "knowledge_nodes"("id") ON DELETE CASCADE,'
            '"relation" VARCHAR(50) NOT NULL,'
            "\"properties\" JSONB DEFAULT '{}',"
            '"created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()'
            ")"
        ),
    },
}
