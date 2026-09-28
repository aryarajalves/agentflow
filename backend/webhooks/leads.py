"""
webhooks/leads.py — Roteador e orquestrador de operações com contatos capturados/leads.

Módulo refatorado e modularizado em submódulos especializados dentro de:
- webhooks.leads_modules.listing (list_webhook_leads, list_webhook_lead_ids)
- webhooks.leads_modules.deletion (delete_single_lead, delete_leads_batch, delete_all_leads, full_purge_lead_by_phone)
- webhooks.leads_modules.sync (sync_all_leads_endpoint)
- webhooks.leads_modules.pipeline_info (get_lead_followup_pipeline)
- webhooks.leads_modules.variables (get_lead_variables)
"""

import logging
from fastapi import APIRouter
from .schemas import LeadBulkDeleteRequest
from .service import delete_contact_data
from .leads_modules import (
    listing_router,
    list_webhook_lead_ids,
    list_webhook_leads,
    deletion_router,
    full_purge_lead_by_phone,
    delete_leads_batch,
    delete_single_lead,
    delete_all_leads,
    sync_router,
    sync_all_leads_endpoint,
    pipeline_info_router,
    get_lead_followup_pipeline,
    variables_router,
    get_lead_variables,
    followup_actions_router,
    trigger_lead_followup_now,
    skip_lead_followup_step,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Inclusão dos sub-roteadores especializados
router.include_router(deletion_router)
router.include_router(listing_router)
router.include_router(sync_router)
router.include_router(pipeline_info_router)
router.include_router(variables_router)
router.include_router(followup_actions_router)

__all__ = [
    "router",
    "LeadBulkDeleteRequest",
    "delete_contact_data",
    "full_purge_lead_by_phone",
    "list_webhook_lead_ids",
    "list_webhook_leads",
    "delete_leads_batch",
    "delete_single_lead",
    "delete_all_leads",
    "sync_all_leads_endpoint",
    "get_lead_followup_pipeline",
    "get_lead_variables",
    "followup_actions_router",
    "trigger_lead_followup_now",
    "skip_lead_followup_step",
]
