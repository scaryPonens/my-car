"""
Smart Car Virtual Assistant - Main Application.

FastAPI server with Telegram bot integration and Smartcar OAuth callback.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from config.settings import settings
from integrations.smartcar_client import (
    exchange_code_for_tokens,
    get_vehicle_info,
    get_vehicles_for_token,
)
from integrations.supabase_client import (
    create_vehicle,
    get_user_by_telegram_id,
    get_vehicle_by_smartcar_id,
    update_vehicle_tokens,
)
from services.telegram_bot import create_bot_application

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global bot application reference
bot_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown of the Telegram bot.
    """
    global bot_app

    logger.info("Starting Smart Car VA...")

    # Create and start the bot
    bot_app = create_bot_application()

    # Initialize the bot
    await bot_app.initialize()

    # Start polling in the background
    asyncio.create_task(start_bot_polling())

    logger.info("Smart Car VA started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Smart Car VA...")
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    logger.info("Smart Car VA shutdown complete")


async def start_bot_polling():
    """Start the Telegram bot polling in the background."""
    global bot_app
    if bot_app:
        try:
            await bot_app.start()
            await bot_app.updater.start_polling(drop_pending_updates=True)
            logger.info("Telegram bot polling started")
        except Exception as e:
            logger.error(f"Failed to start bot polling: {e}")


# Create FastAPI application
app = FastAPI(
    title="Smart Car Virtual Assistant",
    description="A Telegram bot for managing connected vehicles via Smartcar",
    version="1.0.0",
    lifespan=lifespan,
)


# =============================================================================
# Root Endpoint
# =============================================================================


@app.get("/", response_class=JSONResponse)
async def root():
    """
    Root endpoint with API information.

    Returns:
        JSON with API info and status.
    """
    return {
        "name": "Smart Car Virtual Assistant",
        "version": "1.0.0",
        "status": "running",
        "description": "Telegram bot for managing connected vehicles",
        "endpoints": {
            "health": "/health",
            "callback": "/callback",
        },
    }


# =============================================================================
# Health Check
# =============================================================================


@app.get("/health", response_class=JSONResponse)
async def health_check():
    """
    Health check endpoint for Railway/container orchestration.

    Returns:
        JSON with health status.
    """
    return {
        "status": "healthy",
        "bot_running": bot_app is not None,
        "environment": settings.environment,
    }


# =============================================================================
# Smartcar OAuth Callback
# =============================================================================


@app.get("/callback", response_class=HTMLResponse)
async def smartcar_callback(
    code: Optional[str] = Query(None, description="Authorization code from Smartcar"),
    state: Optional[str] = Query(None, description="State parameter (telegram_id)"),
    error: Optional[str] = Query(None, description="Error from Smartcar"),
    error_description: Optional[str] = Query(None, description="Error description"),
):
    """
    Handle Smartcar OAuth callback.

    This endpoint:
    1. Receives the authorization code from Smartcar
    2. Exchanges it for access tokens
    3. Fetches the user's vehicles
    4. Saves vehicles to the database

    Args:
        code: The authorization code from Smartcar.
        state: The state parameter containing the user's telegram_id.
        error: Error code if authorization failed.
        error_description: Human-readable error description.

    Returns:
        HTML page showing success or error message.
    """
    # Handle errors from Smartcar
    if error:
        logger.error(f"Smartcar OAuth error: {error} - {error_description}")
        return _render_callback_page(
            success=False,
            message=f"Authorization failed: {error_description or error}",
        )

    # Validate required parameters
    if not code:
        return _render_callback_page(
            success=False,
            message="No authorization code received.",
        )

    if not state:
        return _render_callback_page(
            success=False,
            message="Invalid state parameter. Please try connecting again.",
        )

    # Parse telegram_id from state
    try:
        telegram_id = int(state)
    except ValueError:
        logger.error(f"Invalid state parameter: {state}")
        return _render_callback_page(
            success=False,
            message="Invalid state parameter.",
        )

    # Get user from database
    user = get_user_by_telegram_id(telegram_id)
    if not user or not user.id:
        logger.error(f"User not found for telegram_id: {telegram_id}")
        return _render_callback_page(
            success=False,
            message="User not found. Please start the bot with /start first.",
        )

    # Exchange code for tokens
    token_data = exchange_code_for_tokens(code)
    if not token_data:
        return _render_callback_page(
            success=False,
            message="Failed to exchange authorization code. Please try again.",
        )

    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    expiration = token_data.get("expiration")

    # Get vehicles for this token
    vehicle_ids = get_vehicles_for_token(access_token)
    if not vehicle_ids:
        return _render_callback_page(
            success=False,
            message="No vehicles found on your account.",
        )

    # Process each vehicle
    vehicles_added = 0
    vehicles_updated = 0

    for vehicle_id in vehicle_ids:
        # Get vehicle info
        vehicle_info = get_vehicle_info(access_token, vehicle_id)

        # Check if vehicle already exists
        existing = get_vehicle_by_smartcar_id(vehicle_id)

        if existing and existing.id:
            # Update existing vehicle tokens
            update_vehicle_tokens(
                existing.id,
                access_token,
                refresh_token,
                expiration,
            )
            vehicles_updated += 1
            logger.info(f"Updated vehicle: {vehicle_id}")
        else:
            # Create new vehicle
            create_vehicle(
                user_id=user.id,
                smartcar_vehicle_id=vehicle_id,
                make=vehicle_info.get("make") if vehicle_info else None,
                model=vehicle_info.get("model") if vehicle_info else None,
                year=vehicle_info.get("year") if vehicle_info else None,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expiration=expiration,
            )
            vehicles_added += 1
            logger.info(f"Added vehicle: {vehicle_id}")

    # Build success message
    message_parts = []
    if vehicles_added > 0:
        message_parts.append(f"{vehicles_added} vehicle(s) connected")
    if vehicles_updated > 0:
        message_parts.append(f"{vehicles_updated} vehicle(s) updated")

    return _render_callback_page(
        success=True,
        message=" and ".join(message_parts) + "!",
    )


# =============================================================================
# Optional: Generate Auth URL Endpoint
# =============================================================================


@app.get("/auth/smartcar", response_class=JSONResponse)
async def get_smartcar_auth_url(
    telegram_id: int = Query(..., description="User's Telegram ID"),
):
    """
    Generate a Smartcar authorization URL.

    Alternative to the /connect bot command for web-based flows.

    Args:
        telegram_id: The user's Telegram ID.

    Returns:
        JSON with the authorization URL.
    """
    from integrations.smartcar_client import get_auth_url

    auth_url = get_auth_url(state=str(telegram_id))

    return {
        "auth_url": auth_url,
        "telegram_id": telegram_id,
    }


# =============================================================================
# Helper Functions
# =============================================================================


def _render_callback_page(success: bool, message: str) -> str:
    """
    Render an HTML page for the OAuth callback result.

    Args:
        success: Whether the operation was successful.
        message: Message to display.

    Returns:
        HTML string.
    """
    status_emoji = "✅" if success else "❌"
    status_color = "#22c55e" if success else "#ef4444"
    status_text = "Success" if success else "Error"

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Car VA - {status_text}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
        }}
        .container {{
            text-align: center;
            padding: 2rem;
            max-width: 400px;
        }}
        .status-icon {{
            font-size: 4rem;
            margin-bottom: 1rem;
        }}
        .status-text {{
            font-size: 1.5rem;
            font-weight: 600;
            color: {status_color};
            margin-bottom: 0.5rem;
        }}
        .message {{
            font-size: 1rem;
            color: #a0aec0;
            margin-bottom: 2rem;
            line-height: 1.5;
        }}
        .instruction {{
            font-size: 0.9rem;
            color: #718096;
            padding: 1rem;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
        }}
        .telegram-link {{
            color: #0088cc;
            text-decoration: none;
        }}
        .telegram-link:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="status-icon">{status_emoji}</div>
        <div class="status-text">{status_text}</div>
        <div class="message">{message}</div>
        <div class="instruction">
            You can close this window and return to
            <a href="https://t.me/" class="telegram-link">Telegram</a>
            to continue using Smart Car Assistant.
        </div>
    </div>
</body>
</html>
"""


# =============================================================================
# Main Entry Point
# =============================================================================


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
