"""
Router principal e agregador modular para todos os endpoints de Webhooks.
"""
from typing import List
from fastapi import APIRouter
from database import get_db
from models import (
    WebhookConfigModel, WebhookEventModel, InteractionLog, 
    SessionSummary, KnowledgeItemModel, UserMemoryModel
)
from transcription_service import transcribe_video
from vision_service import analyze_image
from webhook_tasks import process_webhook_automation, sync_memory_to_vector, process_media_content_task

# Schemas re-exports
from .schemas import (
    WebhookConfigCreate,
    SimulateLoadRequest,
    WebhookConfigResponse,
    WebhookConfigUpdate,
    LeadHistoryItem,
    LeadHistoryResponse,
    BulkDeleteRequest,
    LeadBulkDeleteRequest,
    WebhookEventsPaginatedResponse,
    WebhookEventResponse
)

# Endpoint handlers from modular files
from .configs import (
    upload_followup_media,
    list_webhooks,
    get_chatwoot_global_config,
    get_webhook,
    create_webhook,
    update_webhook,
    toggle_webhook_active,
    delete_webhook
)
from .receiver import (
    check_webhook_active,
    receive_webhook,
    check_memory_webhook,
    receive_memory_webhook
)
from .events import (
    list_webhook_events,
    get_lead_history,
    delete_events_bulk,
    cancel_webhook_event_endpoint,
    retry_webhook_event_endpoint,
    get_webhook_event_detail,
    get_webhook_event_detail_by_id,
    explain_webhook_event_response,
    get_webhook_followup_metrics
)
from .leads import (
    full_purge_lead_by_phone,
    list_webhook_lead_ids,
    list_webhook_leads,
    delete_leads_batch,
    delete_single_lead,
    delete_all_leads,
    sync_all_leads_endpoint,
    get_lead_followup_pipeline,
    get_lead_variables,
    trigger_lead_followup_now,
    skip_lead_followup_step
)
from .tools import (
    simulate_webhook_load,
    get_webhook_whatsapp_templates,
    get_zapvoice_templates_custom
)
from .import_chat import import_chat_from_zapjords, get_chat_import_status, cancel_chat_import

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# 1. Configs & CRUD
router.add_api_route("/upload-media", upload_followup_media, methods=["POST"])
router.add_api_route("", list_webhooks, methods=["GET"], response_model=List[WebhookConfigResponse])
router.add_api_route("/chatwoot-config", get_chatwoot_global_config, methods=["GET"])
router.add_api_route("/{webhook_id}", get_webhook, methods=["GET"], response_model=WebhookConfigResponse)
router.add_api_route("", create_webhook, methods=["POST"], response_model=WebhookConfigResponse, status_code=201)
router.add_api_route("/{webhook_id}", update_webhook, methods=["PUT"], response_model=WebhookConfigResponse)
router.add_api_route("/{webhook_id}/toggle-active", toggle_webhook_active, methods=["PATCH"])
router.add_api_route("/{webhook_id}", delete_webhook, methods=["DELETE"], status_code=204)

# 2. Receiver
router.add_api_route("/receive/{token}", check_webhook_active, methods=["GET"], status_code=200, include_in_schema=False)
router.add_api_route("/receive/{token}", receive_webhook, methods=["POST"], status_code=200, include_in_schema=False)
router.add_api_route("/memory/{token}", check_memory_webhook, methods=["GET"], status_code=200, include_in_schema=False)
router.add_api_route("/memory/{token}", receive_memory_webhook, methods=["POST"], status_code=200, include_in_schema=False)

# 3. Events & History
router.add_api_route("/{webhook_id}/events", list_webhook_events, methods=["GET"], response_model=WebhookEventsPaginatedResponse)
router.add_api_route("/{webhook_id}/leads-by-phone/{phone}/history", get_lead_history, methods=["GET"], response_model=LeadHistoryResponse)
router.add_api_route("/{webhook_id}/events/bulk-delete", delete_events_bulk, methods=["POST"], status_code=204)
router.add_api_route("/{webhook_id}/events/{event_id}/cancel", cancel_webhook_event_endpoint, methods=["POST"], status_code=200)
router.add_api_route("/{webhook_id}/events/{event_id}/retry", retry_webhook_event_endpoint, methods=["POST"], status_code=200)
router.add_api_route("/{webhook_id}/events/{event_id}", get_webhook_event_detail, methods=["GET"])
router.add_api_route("/events/{event_id}", get_webhook_event_detail_by_id, methods=["GET"])
router.add_api_route("/events/{event_id}/explain-response", explain_webhook_event_response, methods=["POST"], include_in_schema=False)
router.add_api_route("/{webhook_id}/events/{event_id}/explain-response", explain_webhook_event_response, methods=["POST"], include_in_schema=False)
router.add_api_route("/{webhook_id}/followup-metrics", get_webhook_followup_metrics, methods=["GET"])

# 4. Leads & Pipelines
router.add_api_route("/{webhook_id}/leads-by-phone/{phone}/full-purge", full_purge_lead_by_phone, methods=["DELETE"], status_code=204)
router.add_api_route("/{webhook_id}/leads/ids", list_webhook_lead_ids, methods=["GET"])
router.add_api_route("/{webhook_id}/leads/all-ids", list_webhook_lead_ids, methods=["GET"])
router.add_api_route("/{webhook_id}/leads", list_webhook_leads, methods=["GET"])
router.add_api_route("/{webhook_id}/leads/delete-batch", delete_leads_batch, methods=["POST"], status_code=204)
router.add_api_route("/{webhook_id}/leads/{lead_id}", delete_single_lead, methods=["DELETE"], status_code=204)
router.add_api_route("/{webhook_id}/leads/all", delete_all_leads, methods=["DELETE"], status_code=204)
router.add_api_route("/{webhook_id}/leads/sync-all", sync_all_leads_endpoint, methods=["POST"])
router.add_api_route("/{webhook_id}/leads/import-zapjords", import_chat_from_zapjords, methods=["POST"])
router.add_api_route("/{webhook_id}/leads/import-status", get_chat_import_status, methods=["GET"])
router.add_api_route("/{webhook_id}/leads/cancel-import", cancel_chat_import, methods=["POST"])
router.add_api_route("/{webhook_id}/leads/{lead_id}/followup-pipeline", get_lead_followup_pipeline, methods=["GET"])
router.add_api_route("/{webhook_id}/leads/{lead_id}/variables", get_lead_variables, methods=["GET"])
router.add_api_route("/{webhook_id}/leads/{lead_id}/followup/trigger-now", trigger_lead_followup_now, methods=["POST"])
router.add_api_route("/{webhook_id}/leads/{lead_id}/followup/skip-step", skip_lead_followup_step, methods=["POST"])

# 5. Tools & Simulation
router.add_api_route("/{webhook_id}/simulate-load", simulate_webhook_load, methods=["POST"], status_code=200, include_in_schema=False)
router.add_api_route("/{webhook_id}/whatsapp-templates", get_webhook_whatsapp_templates, methods=["GET"])
router.add_api_route("/zapvoice/templates", get_zapvoice_templates_custom, methods=["GET"])

__all__ = [
    "router",
    "get_db",
    "WebhookConfigModel",
    "WebhookEventModel",
    "InteractionLog",
    "SessionSummary",
    "KnowledgeItemModel",
    "UserMemoryModel",
    "transcribe_video",
    "analyze_image",
    "process_webhook_automation",
    "sync_memory_to_vector",
    "process_media_content_task",
    "WebhookConfigCreate",
    "SimulateLoadRequest",
    "WebhookConfigResponse",
    "WebhookConfigUpdate",
    "LeadHistoryItem",
    "LeadHistoryResponse",
    "BulkDeleteRequest",
    "LeadBulkDeleteRequest",
    "WebhookEventsPaginatedResponse",
    "WebhookEventResponse",
    "upload_followup_media",
    "list_webhooks",
    "get_chatwoot_global_config",
    "get_webhook",
    "create_webhook",
    "update_webhook",
    "toggle_webhook_active",
    "delete_webhook",
    "check_webhook_active",
    "receive_webhook",
    "check_memory_webhook",
    "receive_memory_webhook",
    "list_webhook_events",
    "get_lead_history",
    "delete_events_bulk",
    "cancel_webhook_event_endpoint",
    "retry_webhook_event_endpoint",
    "get_webhook_event_detail",
    "get_webhook_event_detail_by_id",
    "full_purge_lead_by_phone",
    "list_webhook_lead_ids",
    "list_webhook_leads",
    "delete_leads_batch",
    "delete_single_lead",
    "delete_all_leads",
    "sync_all_leads_endpoint",
    "import_chat_from_zapjords",
    "get_chat_import_status",
    "cancel_chat_import",
    "get_lead_followup_pipeline",
    "get_lead_variables",
    "simulate_webhook_load",
    "get_webhook_whatsapp_templates",
    "get_zapvoice_templates_custom"
]
