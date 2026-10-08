import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models import SaleModel
from api.deps import verify_api_key
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sales", tags=["Sales"])

class SaleCreatePayload(BaseModel):
    email: Optional[str] = None
    telefone: Optional[str] = None
    valor: float = 0.0
    plataforma: Optional[str] = None # Kiwify, Hotmart, etc.

@router.post("/receive", status_code=201, include_in_schema=False)
async def receive_sale_webhook(payload: SaleCreatePayload, db: AsyncSession = Depends(get_db)):
    """
    Endpoint para receber eventos de vendas de plataformas de checkout/afiliados.
    Registra a venda no banco de dados.
    """
    try:
        new_sale = SaleModel(
            email=payload.email,
            telefone=payload.telefone,
            valor=payload.valor,
            plataforma=payload.plataforma or "Desconhecida",
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_sale)
        await db.commit()
        await db.refresh(new_sale)
        
        logger.info(f"💰 Venda registrada com sucesso! ID: {new_sale.id} | Email: {new_sale.email} | Valor: R$ {new_sale.valor} | Plataforma: {new_sale.plataforma}")
        return {"success": True, "sale_id": new_sale.id}
    except Exception as e:
        logger.error(f"Erro ao registrar venda: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao registrar venda: {str(e)}")

@router.get(
    "",
    status_code=200,
    summary="Listar Vendas Registradas",
    description="Lista todo o histórico de vendas e transações integradas via plataformas de checkout (Kiwify, Hotmart, etc.)."
)
async def list_sales(db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    """
    Lista todas as vendas registradas no banco de dados.
    Requer chave de API interna para segurança.
    """
    try:
        result = await db.execute(select(SaleModel).order_by(SaleModel.created_at.desc()))
        sales = result.scalars().all()
        return sales
    except Exception as e:
        logger.error(f"Erro ao listar vendas: {e}")
        raise HTTPException(status_code=500, detail=str(e))
