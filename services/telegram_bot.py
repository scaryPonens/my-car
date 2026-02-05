"""
Telegram bot service for Smart Car VA.

Provides command handlers and natural language processing
for vehicle interaction through Telegram.
"""

import logging
from functools import wraps
from typing import Any, Callable, Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config.settings import settings
from integrations.smartcar_client import (
    get_auth_url,
    get_comprehensive_vehicle_data,
    lock_vehicle,
    unlock_vehicle,
    ensure_valid_token,
)
from integrations.supabase_client import (
    get_or_create_user,
    get_user_vehicles,
    update_vehicle_tokens,
)
from models.schemas import LLMAction, User, Vehicle
from services.llm_service import (
    generate_vehicle_summary,
    get_available_provider,
    process_llm_request,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Decorators
# =============================================================================


def require_user(func: Callable) -> Callable:
    """
    Decorator that ensures a user exists before executing a handler.

    Creates the user if they don't exist. Injects the User object
    into the handler's context.

    Args:
        func: The handler function to wrap.

    Returns:
        Wrapped handler with user injection.
    """
    @wraps(func)
    async def wrapper(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> Any:
        if not update.effective_user:
            return

        telegram_user = update.effective_user
        user = get_or_create_user(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
        )

        if not user:
            await update.message.reply_text(
                "Sorry, there was an error setting up your account. "
                "Please try again later."
            )
            return

        # Store user in context for handler access
        context.user_data["user"] = user
        return await func(update, context)

    return wrapper


def log_command(func: Callable) -> Callable:
    """
    Decorator that logs command execution.

    Args:
        func: The handler function to wrap.

    Returns:
        Wrapped handler with logging.
    """
    @wraps(func)
    async def wrapper(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> Any:
        user_id = update.effective_user.id if update.effective_user else "unknown"
        command = update.message.text if update.message else "unknown"
        logger.info(f"Command from {user_id}: {command}")
        return await func(update, context)

    return wrapper


# =============================================================================
# Command Handlers
# =============================================================================


@log_command
async def start_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Handle the /start command.

    Welcomes the user and provides initial instructions.
    """
    welcome_message = """
Welcome to Smart Car Assistant! 🚗

I can help you manage your connected vehicles. Here's what I can do:

/connect - Connect a new vehicle
/vehicles - List your connected vehicles
/status - Get your vehicle's current status
/help - Show available commands

You can also just send me a message in plain English, and I'll try to help!

To get started, use /connect to link your car.
"""
    await update.message.reply_text(welcome_message)

@log_command
@require_user
async def connect_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Handle the /connect command.

    Generates a Smartcar OAuth URL for the user to connect their vehicle.
    """
    user: User = context.user_data["user"]

    # Generate auth URL with user's telegram_id as state
    auth_url = get_auth_url(state=str(user.telegram_id))

    message = f"""
To connect your vehicle, please click the link below:

{auth_url}

This will take you to Smartcar where you can securely log in with your car's account (Tesla, Ford, etc.) and grant access.

After connecting, you'll be redirected back and your vehicle will be available!
"""
    await update.message.reply_text(message)


@log_command
@require_user
async def vehicles_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Handle the /vehicles command.

    Lists all vehicles connected to the user's account.
    """
    user: User = context.user_data["user"]

    if not user.id:
        await update.message.reply_text(
            "Error retrieving your account. Please try again."
        )
        return

    vehicles = get_user_vehicles(user.id)

    if not vehicles:
        await update.message.reply_text(
            "You don't have any vehicles connected yet.\n\n"
            "Use /connect to link your car!"
        )
        return

    message_parts = ["Your connected vehicles:\n"]
    for i, vehicle in enumerate(vehicles, 1):
        status_emoji = "✅" if vehicle.status.value == "active" else "⚠️"
        message_parts.append(
            f"{i}. {status_emoji} {vehicle.display_name} ({vehicle.status.value})"
        )

    await update.message.reply_text("\n".join(message_parts))


@log_command
@require_user
async def status_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Handle the /status command.

    Shows the current status of the user's primary vehicle.
    """
    user: User = context.user_data["user"]

    if not user.id:
        await update.message.reply_text(
            "Error retrieving your account. Please try again."
        )
        return

    vehicles = get_user_vehicles(user.id)

    if not vehicles:
        await update.message.reply_text(
            "You don't have any vehicles connected yet.\n\n"
            "Use /connect to link your car!"
        )
        return

    # Use the first vehicle (could be enhanced to allow selection)
    vehicle = vehicles[0]

    # Check and refresh token if needed
    await _ensure_vehicle_token(vehicle)

    if not vehicle.tokens:
        await update.message.reply_text(
            f"Unable to access {vehicle.display_name}. "
            "Please reconnect using /connect."
        )
        return

    # Fetch vehicle data
    await update.message.reply_text(
        f"Fetching status for {vehicle.display_name}..."
    )

    data = get_comprehensive_vehicle_data(
        vehicle.tokens.access_token,
        vehicle.smartcar_vehicle_id,
    )

    if not data:
        await update.message.reply_text(
            "Unable to retrieve vehicle data. "
            "Please try again later or reconnect using /connect."
        )
        return

    # Generate and send summary
    summary = generate_vehicle_summary(vehicle, data)
    await update.message.reply_text(summary, parse_mode="Markdown")


@log_command
async def help_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Handle the /help command.

    Shows available commands and usage instructions.
    """
    help_message = """
**Smart Car Assistant Commands**

/start - Welcome message and introduction
/connect - Connect a new vehicle via Smartcar
/vehicles - List all your connected vehicles
/status - Get current vehicle status (fuel, battery, odometer)
/help - Show this help message

**Natural Language**
You can also just type messages like:
- "What's my fuel level?"
- "Lock my car"
- "What's the battery status?"

I'll do my best to understand and help!

**Need Help?**
If you're having trouble, try disconnecting and reconnecting your vehicle with /connect.
"""
    await update.message.reply_text(help_message, parse_mode="Markdown")


# =============================================================================
# Message Handler (Natural Language)
# =============================================================================


@log_command
@require_user
async def message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Handle natural language messages.

    Uses the LLM service to process user messages and execute
    appropriate actions.
    """
    user: User = context.user_data["user"]
    user_message = update.message.text

    if not user.id:
        await update.message.reply_text(
            "Error retrieving your account. Please try again."
        )
        return

    # Check if LLM is available
    provider = get_available_provider()
    if not provider:
        await update.message.reply_text(
            "Natural language processing is not configured. "
            "Please use the available commands (/help for list)."
        )
        return

    # Get user's vehicles for context
    vehicles = get_user_vehicles(user.id)

    # Get current vehicle data if available
    vehicle_data = None
    primary_vehicle = None
    if vehicles:
        primary_vehicle = vehicles[0]
        await _ensure_vehicle_token(primary_vehicle)
        if primary_vehicle.tokens:
            vehicle_data = get_comprehensive_vehicle_data(
                primary_vehicle.tokens.access_token,
                primary_vehicle.smartcar_vehicle_id,
            )

    # Process through LLM
    response = process_llm_request(
        user_message=user_message,
        vehicles=vehicles,
        vehicle_data=vehicle_data,
        provider=provider,
    )

    # Execute action if confidence is high enough
    action_result = await _execute_action(
        response.action,
        response.parameters,
        user,
        primary_vehicle,
        vehicles,
    )

    # Send response
    final_message = response.message
    if action_result:
        final_message = f"{response.message}\n\n{action_result}"

    await update.message.reply_text(final_message, parse_mode="Markdown")


# =============================================================================
# Action Execution
# =============================================================================


async def _execute_action(
    action: LLMAction,
    parameters: dict,
    user: User,
    vehicle: Optional[Vehicle],
    vehicles: list[Vehicle],
) -> Optional[str]:
    """
    Execute an LLM-determined action.

    Args:
        action: The action to execute.
        parameters: Action parameters.
        user: The current user.
        vehicle: The primary vehicle (if any).
        vehicles: All user vehicles.

    Returns:
        Result message to append to response, or None.
    """
    if action == LLMAction.NONE:
        return None

    if action == LLMAction.LIST_VEHICLES:
        if not vehicles:
            return "You don't have any vehicles connected."
        vehicle_list = "\n".join(
            f"- {v.display_name} ({v.status.value})" for v in vehicles
        )
        return f"Your vehicles:\n{vehicle_list}"

    if action == LLMAction.HELP:
        return "Use /help to see all available commands."

    # Actions requiring a vehicle
    if not vehicle or not vehicle.tokens:
        return "No vehicle available. Please connect one with /connect."

    if action == LLMAction.GET_STATUS:
        data = get_comprehensive_vehicle_data(
            vehicle.tokens.access_token,
            vehicle.smartcar_vehicle_id,
        )
        if data:
            return generate_vehicle_summary(vehicle, data)
        return "Unable to retrieve vehicle status."

    if action == LLMAction.LOCK:
        success = lock_vehicle(
            vehicle.tokens.access_token,
            vehicle.smartcar_vehicle_id,
        )
        if success:
            return f"✅ {vehicle.display_name} has been locked."
        return f"❌ Failed to lock {vehicle.display_name}."

    if action == LLMAction.UNLOCK:
        success = unlock_vehicle(
            vehicle.tokens.access_token,
            vehicle.smartcar_vehicle_id,
        )
        if success:
            return f"🔓 {vehicle.display_name} has been unlocked."
        return f"❌ Failed to unlock {vehicle.display_name}."

    # Unsupported actions (location and tire pressure not available)
    if action == LLMAction.GET_LOCATION:
        return "📍 Location data is not currently available for this vehicle."

    if action == LLMAction.GET_TIRE_PRESSURE:
        return "🚗 Tire pressure data is not currently available for this vehicle."

    # Individual data actions
    if action in (
        LLMAction.GET_FUEL,
        LLMAction.GET_BATTERY,
        LLMAction.GET_ODOMETER,
    ):
        data = get_comprehensive_vehicle_data(
            vehicle.tokens.access_token,
            vehicle.smartcar_vehicle_id,
        )
        if not data:
            return "Unable to retrieve vehicle data."
        return _format_specific_data(action, data, vehicle)

    return None


def _format_specific_data(
    action: LLMAction,
    data: Any,
    vehicle: Vehicle,
) -> str:
    """Format specific vehicle data based on action type."""
    if action == LLMAction.GET_FUEL and data.fuel:
        result = f"⛽ {vehicle.display_name} fuel: {data.fuel.percent_remaining:.1f}%"
        if data.fuel.range:
            result += f" ({data.fuel.range:.0f} km range)"
        return result

    if action == LLMAction.GET_BATTERY and data.battery:
        result = f"🔋 {vehicle.display_name} battery: {data.battery.percent_remaining:.1f}%"
        if data.battery.range:
            result += f" ({data.battery.range:.0f} km range)"
        return result

    if action == LLMAction.GET_ODOMETER and data.odometer:
        return f"🛣️ {vehicle.display_name} odometer: {data.odometer.distance:,.1f} km"

    return "Data not available for this vehicle."


# =============================================================================
# Helper Functions
# =============================================================================


async def _ensure_vehicle_token(vehicle: Vehicle) -> None:
    """
    Ensure vehicle has a valid token, refreshing if needed.

    Updates the vehicle in the database if tokens are refreshed.

    Args:
        vehicle: The vehicle to check.
    """
    new_tokens = ensure_valid_token(vehicle)
    if new_tokens and vehicle.id:
        update_vehicle_tokens(
            vehicle.id,
            new_tokens["access_token"],
            new_tokens["refresh_token"],
            new_tokens.get("expiration"),
        )
        # Update local vehicle object
        if vehicle.tokens:
            vehicle.tokens.access_token = new_tokens["access_token"]
            vehicle.tokens.refresh_token = new_tokens["refresh_token"]
            vehicle.tokens.expiration = new_tokens.get("expiration")


# =============================================================================
# Bot Application Factory
# =============================================================================


def create_bot_application() -> Application:
    """
    Create and configure the Telegram bot application.

    Returns:
        A configured Application instance with all handlers registered.
    """
    # Create application
    application = Application.builder().token(settings.telegram_bot_token).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("connect", connect_handler))
    application.add_handler(CommandHandler("vehicles", vehicles_handler))
    application.add_handler(CommandHandler("status", status_handler))
    application.add_handler(CommandHandler("help", help_handler))

    # Register message handler for natural language
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    )

    logger.info("Telegram bot application created with all handlers")
    return application
