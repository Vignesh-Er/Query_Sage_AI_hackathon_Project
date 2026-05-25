from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict
from app.database import get_db
from app.models import Settings
from app.schemas import SettingsResponse, SettingsPatch
from app.config import settings

router = APIRouter(prefix="/api/settings", tags=["Settings"])

@router.get("")
async def get_all_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settings))
    db_settings = result.scalars().all()
    
    # If settings are empty, pre-populate from Pydantic config values
    if not db_settings:
        defaults = {
            "ai_provider": settings.QUERYSAGE_AI_PROVIDER,
            "anthropic_api_key": settings.QUERYSAGE_ANTHROPIC_API_KEY,
            "anthropic_model": settings.QUERYSAGE_ANTHROPIC_MODEL,
            "ollama_host": settings.QUERYSAGE_OLLAMA_HOST,
            "ollama_model": settings.QUERYSAGE_OLLAMA_MODEL,
            "playwright_timeout": str(settings.QUERYSAGE_PLAYWRIGHT_TIMEOUT),
            "redaction_enabled": "true"
        }
        for k, v in defaults.items():
            db.add(Settings(key=k, value=v))
        await db.commit()
        result = await db.execute(select(Settings))
        db_settings = result.scalars().all()
        
    return db_settings

@router.patch("/{key}", response_model=SettingsResponse)
async def patch_setting(key: str, data: SettingsPatch, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settings).filter(Settings.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        # Create it if it doesn't exist
        setting = Settings(key=key, value=data.value)
        db.add(setting)
    else:
        setting.value = data.value
        
    await db.commit()
    await db.refresh(setting)
    
    # Synchronize updated settings to global Pydantic config objects dynamically
    if key == "ai_provider":
        settings.QUERYSAGE_AI_PROVIDER = data.value
    elif key == "anthropic_api_key":
        settings.QUERYSAGE_ANTHROPIC_API_KEY = data.value
    elif key == "anthropic_model":
        settings.QUERYSAGE_ANTHROPIC_MODEL = data.value
    elif key == "ollama_host":
        settings.QUERYSAGE_OLLAMA_HOST = data.value
    elif key == "ollama_model":
        settings.QUERYSAGE_OLLAMA_MODEL = data.value
    elif key == "playwright_timeout":
        settings.QUERYSAGE_PLAYWRIGHT_TIMEOUT = int(data.value)
        
    return setting
