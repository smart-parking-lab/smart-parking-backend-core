from datetime import datetime
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.model.invoices import Invoice
from app.model.parking_sessions import ParkingSession
from app.model.pricing_rules import PricingRule
from app.model.vehicle_type import VehicleType
from app.model.vehicle import Vehicle
from app.model.user import User
from app.schemas.invoices import InvoiceCreate, InvoiceCheckout, InvoicePay, RevenueResponse, InvoiceResponse
from app.utils.mqtt_client import mqtt_client

async def create_invoice(db: AsyncSession, payload: InvoiceCreate):
    result = await db.execute(select(ParkingSession).filter(ParkingSession.id == payload.session_id))
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session không tồn tại")
    
    invoice = Invoice(**payload.dict())
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return invoice

async def checkout_invoice(db: AsyncSession, payload: InvoiceCheckout):
    result = await db.execute(select(Invoice).filter(Invoice.id == payload.id))
    invoice = result.scalars().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice không tồn tại")
    if invoice.status != "unpaid":
        raise HTTPException(status_code=400, detail="Invoice đã được thanh toán")
    
    now = datetime.now()
    day_of_week = now.weekday()
    current_time = now.time()
    if day_of_week == 5 or day_of_week == 6:
        day_of_week = "SAT-SUN"
    else:
        day_of_week = "MON-FRI"
    
    pr_result = await db.execute(
        select(PricingRule).filter(
            and_(
                PricingRule.days_of_week == day_of_week,
                PricingRule.start_time <= current_time,
                PricingRule.end_time >= current_time
            )
        )
    )
    pricing_rule = pr_result.scalars().first()
    if not pricing_rule:
        raise HTTPException(status_code=404, detail="Pricing rule không tồn tại")
        
    invoice.pricing_rule_id = pricing_rule.id
    invoice.duration_minutes = payload.time_total
    if invoice.duration_minutes > 1440:
        invoice.amount = invoice.duration_minutes / 1440 * pricing_rule.price_per_day
    else:
        invoice.amount = invoice.duration_minutes / 60 * pricing_rule.price_per_hour
        
    await db.commit()
    await db.refresh(invoice)
    return invoice

async def pay_invoice(db: AsyncSession, payload: InvoicePay):
    result = await db.execute(select(Invoice).filter(Invoice.id == payload.id))
    invoice = result.scalars().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice không tồn tại")
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail="Invoice đã được thanh toán")
    
    invoice.status = "paid"
    invoice.paid_at = datetime.now()
    invoice.payment_method = payload.payment_method
    
    await db.commit()
    await db.refresh(invoice)
    mqtt_client.open_servo("SERVO_OUT")
    return invoice

async def get_revenue(db: AsyncSession, user_id: UUID):
    user_result = await db.execute(select(User).options(selectinload(User.role)).filter(User.id == user_id))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role.name != "Admin":
        raise HTTPException(status_code=403, detail="You are not authorized to perform this action")
        
    result = await db.execute(select(Invoice))
    invoices = result.scalars().all()
    
    total_revenue = 0
    total_paid_invoices = 0
    list_invoices = []
    for invoice in invoices:
        amount = invoice.amount or 0
        total_revenue += amount
        if invoice.status == "paid":
            total_paid_invoices += amount
        list_invoices.append(InvoiceResponse.model_validate(invoice))
        
    return RevenueResponse(
        total_revenue=total_revenue,
        total_paid_invoices=total_paid_invoices,
        list_invoices=list_invoices
    )