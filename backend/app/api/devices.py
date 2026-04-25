import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device
from app.dependencies import get_db
from app.schemas.device import DeviceCreate, DeviceRead, DeviceRegisterResponse

log = logging.getLogger(__name__)

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/register", response_model=DeviceRegisterResponse, status_code=201)
async def register_device(
    body: DeviceCreate,
    db: AsyncSession = Depends(get_db),
) -> DeviceRegisterResponse:
    """Register a new device (called by ESP32 on first boot)."""
    device = Device(
        name=body.name,
        room=body.room,
        registered_at=datetime.now(timezone.utc),
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    log.info("Device registered: id=%d name=%r room=%r", device.id, device.name, device.room)
    return DeviceRegisterResponse(device_id=device.id, name=device.name, room=device.room)


@router.get("", response_model=list[DeviceRead])
async def list_devices(db: AsyncSession = Depends(get_db)) -> list[DeviceRead]:
    """Return all registered devices."""
    result = await db.execute(select(Device).order_by(Device.registered_at.desc()))
    return [DeviceRead.model_validate(d) for d in result.scalars().all()]


@router.get("/{device_id}", response_model=DeviceRead)
async def get_device(device_id: int, db: AsyncSession = Depends(get_db)) -> DeviceRead:
    """Return a single device by ID."""
    device = await db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return DeviceRead.model_validate(device)
