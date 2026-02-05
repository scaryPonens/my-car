"""
LLM service supporting multiple providers (OpenAI and Anthropic).

Provides a unified interface for processing natural language requests
with structured response parsing for vehicle control actions.
"""

import json
import logging
from enum import Enum
from typing import Any, Optional

from anthropic import Anthropic
from openai import OpenAI

from config.settings import settings
from models.schemas import (
    LLMAction,
    LLMResponse,
    Vehicle,
    VehicleData,
)

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


# =============================================================================
# System Prompts
# =============================================================================


VEHICLE_ASSISTANT_SYSTEM_PROMPT = """You are a helpful Smart Car Virtual Assistant. Your role is to help users interact with their connected vehicles through natural conversation.

You can help users with:
- Checking vehicle status (fuel/battery level, odometer, location, tire pressure)
- Locking and unlocking their vehicle
- Listing their connected vehicles
- Answering questions about their vehicle data

When a user makes a request, you must respond with a JSON object containing:
- "message": A friendly response message to show the user
- "action": One of the following actions (or "none" if no action needed):
  - "get_status" - Get comprehensive vehicle status
  - "get_location" - Get vehicle location
  - "get_fuel" - Get fuel level
  - "get_battery" - Get battery level (for EVs)
  - "get_odometer" - Get odometer reading
  - "get_tire_pressure" - Get tire pressure
  - "lock" - Lock the vehicle
  - "unlock" - Unlock the vehicle
  - "list_vehicles" - List all connected vehicles
  - "help" - Show help information
  - "none" - No action needed (just conversation)
- "parameters": Any parameters needed for the action (usually empty object {})
- "confidence": A number between 0 and 1 indicating how confident you are in understanding the request

Always respond with valid JSON. Be friendly and helpful. If you're unsure what the user wants, ask for clarification with action "none".

Important safety notes:
- Always confirm before unlocking a vehicle
- Provide clear, accurate information about vehicle status
- If an action fails, explain what happened in a user-friendly way

Current context will be provided in the user message, including vehicle information if available."""


# =============================================================================
# OpenAI Provider
# =============================================================================


def call_openai(
    messages: list[dict[str, str]],
    model: str = "gpt-4-turbo-preview",
) -> Optional[str]:
    """
    Call OpenAI's API.

    Args:
        messages: List of message dicts with role and content.
        model: The model to use.

    Returns:
        The assistant's response text, or None on error.
    """
    if not settings.openai_api_key:
        logger.error("OpenAI API key not configured")
        return None

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            temperature=0.7,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return None


# =============================================================================
# Anthropic Provider
# =============================================================================


def call_anthropic(
    messages: list[dict[str, str]],
    system_prompt: str,
    model: str = "claude-3-5-sonnet-20241022",
) -> Optional[str]:
    """
    Call Anthropic's API.

    Args:
        messages: List of message dicts with role and content.
        system_prompt: The system prompt to use.
        model: The model to use.

    Returns:
        The assistant's response text, or None on error.
    """
    if not settings.anthropic_api_key:
        logger.error("Anthropic API key not configured")
        return None

    try:
        client = Anthropic(api_key=settings.anthropic_api_key)

        # Filter out system messages (handled separately in Anthropic)
        user_messages = [m for m in messages if m["role"] != "system"]

        response = client.messages.create(
            model=model,
            max_tokens=1000,
            system=system_prompt,
            messages=user_messages,  # type: ignore
        )

        # Extract text from response
        if response.content and len(response.content) > 0:
            return response.content[0].text
        return None
    except Exception as e:
        logger.error(f"Anthropic API error: {e}")
        return None


# =============================================================================
# Response Parsing
# =============================================================================


def parse_llm_response(raw_response: str) -> LLMResponse:
    """
    Parse an LLM response into a structured LLMResponse.

    Handles various response formats and provides fallbacks.

    Args:
        raw_response: The raw text response from the LLM.

    Returns:
        A structured LLMResponse object.
    """
    try:
        # Try to parse as JSON
        data = json.loads(raw_response)

        # Extract action
        action_str = data.get("action", "none").lower()
        try:
            action = LLMAction(action_str)
        except ValueError:
            action = LLMAction.NONE

        return LLMResponse(
            message=data.get("message", "I'm not sure how to respond to that."),
            action=action,
            parameters=data.get("parameters", {}),
            confidence=float(data.get("confidence", 0.8)),
            raw_response=raw_response,
        )
    except json.JSONDecodeError:
        # Fallback: treat the whole response as a message
        logger.warning("Failed to parse LLM response as JSON")
        return LLMResponse(
            message=raw_response,
            action=LLMAction.NONE,
            parameters={},
            confidence=0.5,
            raw_response=raw_response,
        )
    except Exception as e:
        logger.error(f"Error parsing LLM response: {e}")
        return LLMResponse(
            message="I encountered an error processing your request.",
            action=LLMAction.NONE,
            parameters={},
            confidence=0.0,
            raw_response=raw_response,
        )


# =============================================================================
# Context Building
# =============================================================================


def build_vehicle_context(
    vehicles: list[Vehicle],
    current_data: Optional[VehicleData] = None,
) -> str:
    """
    Build context string with vehicle information for the LLM.

    Args:
        vehicles: List of user's vehicles.
        current_data: Optional current vehicle data.

    Returns:
        A formatted context string.
    """
    if not vehicles:
        return "No vehicles connected."

    context_parts = ["Connected vehicles:"]

    for i, vehicle in enumerate(vehicles, 1):
        context_parts.append(
            f"{i}. {vehicle.display_name} (Status: {vehicle.status.value})"
        )

    if current_data:
        context_parts.append("\nCurrent vehicle data:")

        if current_data.fuel:
            if current_data.fuel.percent_remaining is not None:
                context_parts.append(
                    f"- Fuel: {current_data.fuel.percent_remaining:.1f}%"
                )

        if current_data.battery:
            if current_data.battery.percent_remaining is not None:
                context_parts.append(
                    f"- Battery: {current_data.battery.percent_remaining:.1f}%"
                )
            if current_data.battery.range is not None:
                context_parts.append(
                    f"- Range: {current_data.battery.range:.1f} km"
                )

        if current_data.odometer:
            context_parts.append(
                f"- Odometer: {current_data.odometer.distance:.1f} km"
            )

        if current_data.location:
            context_parts.append(
                f"- Location: {current_data.location.latitude:.4f}, "
                f"{current_data.location.longitude:.4f}"
            )

        if current_data.tire_pressure:
            tp = current_data.tire_pressure
            pressures = []
            if tp.front_left:
                pressures.append(f"FL: {tp.front_left:.0f}")
            if tp.front_right:
                pressures.append(f"FR: {tp.front_right:.0f}")
            if tp.rear_left:
                pressures.append(f"RL: {tp.rear_left:.0f}")
            if tp.rear_right:
                pressures.append(f"RR: {tp.rear_right:.0f}")
            if pressures:
                context_parts.append(f"- Tire Pressure (kPa): {', '.join(pressures)}")

    return "\n".join(context_parts)


def build_messages(
    user_message: str,
    vehicles: list[Vehicle],
    vehicle_data: Optional[VehicleData] = None,
    conversation_history: Optional[list[dict[str, str]]] = None,
) -> list[dict[str, str]]:
    """
    Build the message list for the LLM.

    Args:
        user_message: The user's message.
        vehicles: List of user's vehicles.
        vehicle_data: Optional current vehicle data.
        conversation_history: Optional previous messages.

    Returns:
        List of message dicts for the LLM.
    """
    messages = [{"role": "system", "content": VEHICLE_ASSISTANT_SYSTEM_PROMPT}]

    # Add conversation history if provided
    if conversation_history:
        messages.extend(conversation_history)

    # Build context
    context = build_vehicle_context(vehicles, vehicle_data)

    # Add user message with context
    full_message = f"Context:\n{context}\n\nUser message: {user_message}"
    messages.append({"role": "user", "content": full_message})

    return messages


# =============================================================================
# Main Processing Function
# =============================================================================


def process_llm_request(
    user_message: str,
    vehicles: list[Vehicle],
    vehicle_data: Optional[VehicleData] = None,
    conversation_history: Optional[list[dict[str, str]]] = None,
    provider: Optional[LLMProvider] = None,
) -> LLMResponse:
    """
    Process a user message through the LLM and return a structured response.

    This is the main entry point for LLM processing. It:
    1. Builds the message context
    2. Calls the appropriate LLM provider
    3. Parses the response into a structured format

    Args:
        user_message: The user's natural language message.
        vehicles: List of user's vehicles for context.
        vehicle_data: Optional current vehicle telemetry.
        conversation_history: Optional previous conversation messages.
        provider: Which LLM provider to use (defaults to settings).

    Returns:
        A structured LLMResponse with message, action, and parameters.
    """
    # Determine provider
    if provider is None:
        provider = LLMProvider(settings.default_llm_provider)

    # Build messages
    messages = build_messages(
        user_message,
        vehicles,
        vehicle_data,
        conversation_history,
    )

    # Call appropriate provider
    raw_response: Optional[str] = None

    if provider == LLMProvider.OPENAI:
        raw_response = call_openai(messages)
    elif provider == LLMProvider.ANTHROPIC:
        raw_response = call_anthropic(
            messages,
            VEHICLE_ASSISTANT_SYSTEM_PROMPT,
        )

    if raw_response is None:
        return LLMResponse(
            message="I'm having trouble processing your request. Please try again.",
            action=LLMAction.NONE,
            parameters={},
            confidence=0.0,
        )

    return parse_llm_response(raw_response)


# =============================================================================
# Helper Functions
# =============================================================================


def generate_vehicle_summary(vehicle: Vehicle, data: VehicleData) -> str:
    """
    Generate a human-readable summary of vehicle status.

    Args:
        vehicle: The vehicle model.
        data: Current vehicle data.

    Returns:
        A formatted status summary string.
    """
    parts = [f"**{vehicle.display_name}**\n"]

    if data.fuel and data.fuel.percent_remaining is not None:
        parts.append(f"Fuel: {data.fuel.percent_remaining:.1f}%")
        if data.fuel.range:
            parts.append(f" ({data.fuel.range:.0f} km range)")
        parts.append("\n")

    if data.battery and data.battery.percent_remaining is not None:
        parts.append(f"Battery: {data.battery.percent_remaining:.1f}%")
        if data.battery.range:
            parts.append(f" ({data.battery.range:.0f} km range)")
        parts.append("\n")

    if data.odometer:
        parts.append(f"Odometer: {data.odometer.distance:,.1f} km\n")

    return "".join(parts)


def get_available_provider() -> Optional[LLMProvider]:
    """
    Get an available LLM provider based on configured API keys.

    Returns:
        The first available provider, or None if none configured.
    """
    if settings.openai_api_key:
        return LLMProvider.OPENAI
    if settings.anthropic_api_key:
        return LLMProvider.ANTHROPIC
    return None
