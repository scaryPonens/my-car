"""
Smartcar API client with functional programming patterns.

Provides pure functions for vehicle data retrieval and control.
Uses safe API call wrappers for error handling.
"""

import logging
from datetime import datetime, timedelta
from functools import partial
from typing import Any, Callable, Optional, TypeVar

import smartcar

from config.settings import settings
from models.schemas import (
    TirePressure,
    Vehicle,
    VehicleBattery,
    VehicleData,
    VehicleFuel,
    VehicleLocation,
    VehicleOdometer,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# Error Handling Utilities
# =============================================================================


def safe_api_call(
    func: Callable[..., T],
    default: T,
    log_error: bool = True,
) -> Callable[..., T]:
    """
    Wrap an API function to return a default value on error.

    This is a higher-order function that creates safe versions
    of potentially failing API calls.

    Args:
        func: The function to wrap.
        default: Value to return on error.
        log_error: Whether to log errors.

    Returns:
        A wrapped function that never raises.

    Example:
        >>> safe_get_location = safe_api_call(get_location, default=None)
        >>> location = safe_get_location(vehicle_id)  # Never raises
    """
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)
        except smartcar.exceptions.SmartcarException as e:
            if log_error:
                logger.warning(f"Smartcar API error in {func.__name__}: {e}")
            return default
        except Exception as e:
            if log_error:
                logger.error(f"Unexpected error in {func.__name__}: {e}")
            return default
    return wrapper


# =============================================================================
# Client Creation
# =============================================================================


def create_smartcar_client() -> smartcar.AuthClient:
    """
    Create a Smartcar AuthClient for OAuth operations.

    Returns:
        A configured Smartcar AuthClient instance.
    """
    return smartcar.AuthClient(
        client_id=settings.smartcar_client_id,
        client_secret=settings.smartcar_client_secret,
        redirect_uri=settings.smartcar_redirect_uri,
        mode=settings.smartcar_mode,
    )


def get_auth_url(
    state: Optional[str] = None,
    force_prompt: bool = False,
) -> str:
    """
    Generate a Smartcar OAuth authorization URL.

    Args:
        state: Optional state parameter for CSRF protection.
        force_prompt: Whether to force the consent prompt.

    Returns:
        The authorization URL to redirect users to.
    """
    client = create_smartcar_client()

    # Define requested permissions
    scope = [
        "read_vehicle_info",
        "read_location",
        "read_odometer",
        "read_fuel",
        "read_battery",
        "read_tires",
        "control_security",
    ]

    # Build options dict (state and force_prompt go here per SDK docs)
    options: dict[str, Any] = {}
    if state:
        options["state"] = state
    if force_prompt:
        options["force_prompt"] = True

    return client.get_auth_url(scope=scope, options=options if options else None)


# =============================================================================
# Token Management
# =============================================================================


def exchange_code_for_tokens(code: str) -> Optional[dict[str, Any]]:
    """
    Exchange an authorization code for access tokens.

    Args:
        code: The authorization code from OAuth callback.

    Returns:
        Token data including access_token, refresh_token, and expiration,
        or None on error.
    """
    try:
        client = create_smartcar_client()
        tokens = client.exchange_code(code)

        return {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "expiration": datetime.utcnow() + timedelta(seconds=tokens.expires_in),
        }
    except smartcar.exceptions.SmartcarException as e:
        logger.error(f"Failed to exchange code for tokens: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error exchanging code: {e}")
        return None


def refresh_access_token(refresh_token: str) -> Optional[dict[str, Any]]:
    """
    Refresh an expired access token.

    Args:
        refresh_token: The refresh token.

    Returns:
        New token data including access_token, refresh_token, and expiration,
        or None on error.
    """
    try:
        client = create_smartcar_client()
        tokens = client.exchange_refresh_token(refresh_token)

        return {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "expiration": datetime.utcnow() + timedelta(seconds=tokens.expires_in),
        }
    except smartcar.exceptions.SmartcarException as e:
        logger.error(f"Failed to refresh token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error refreshing token: {e}")
        return None


def get_vehicles_for_token(access_token: str) -> list[str]:
    """
    Get all vehicle IDs associated with an access token.

    Args:
        access_token: A valid access token.

    Returns:
        List of Smartcar vehicle IDs.
    """
    try:
        response = smartcar.get_vehicles(access_token)
        return response.vehicles
    except smartcar.exceptions.SmartcarException as e:
        logger.error(f"Failed to get vehicles: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error getting vehicles: {e}")
        return []


# =============================================================================
# Vehicle Data Retrieval
# =============================================================================


def _get_smartcar_vehicle(
    access_token: str,
    vehicle_id: str,
) -> Optional[smartcar.Vehicle]:
    """
    Create a Smartcar Vehicle instance.

    Internal helper function.

    Args:
        access_token: Valid access token.
        vehicle_id: Smartcar vehicle ID.

    Returns:
        A Smartcar Vehicle instance, or None on error.
    """
    try:
        return smartcar.Vehicle(vehicle_id, access_token)
    except Exception as e:
        logger.error(f"Failed to create vehicle instance: {e}")
        return None


def get_vehicle_info(
    access_token: str,
    vehicle_id: str,
) -> Optional[dict[str, Any]]:
    """
    Get basic vehicle information.

    Args:
        access_token: Valid access token.
        vehicle_id: Smartcar vehicle ID.

    Returns:
        Dictionary with make, model, year, and id, or None on error.
    """
    vehicle = _get_smartcar_vehicle(access_token, vehicle_id)
    if not vehicle:
        return None

    try:
        attributes = vehicle.attributes()
        return {
            "id": attributes.id,
            "make": attributes.make,
            "model": attributes.model,
            "year": attributes.year,
        }
    except smartcar.exceptions.SmartcarException as e:
        logger.warning(f"Failed to get vehicle info: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting vehicle info: {e}")
        return None


def get_vehicle_location(
    access_token: str,
    vehicle_id: str,
) -> Optional[VehicleLocation]:
    """
    Get current vehicle location.

    Args:
        access_token: Valid access token.
        vehicle_id: Smartcar vehicle ID.

    Returns:
        VehicleLocation or None on error.
    """
    vehicle = _get_smartcar_vehicle(access_token, vehicle_id)
    if not vehicle:
        return None

    try:
        location = vehicle.location()
        return VehicleLocation(
            latitude=location.latitude,
            longitude=location.longitude,
            timestamp=datetime.utcnow(),
        )
    except smartcar.exceptions.SmartcarException as e:
        logger.warning(f"Failed to get vehicle location: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting location: {e}")
        return None


def get_vehicle_odometer(
    access_token: str,
    vehicle_id: str,
) -> Optional[VehicleOdometer]:
    """
    Get vehicle odometer reading.

    Args:
        access_token: Valid access token.
        vehicle_id: Smartcar vehicle ID.

    Returns:
        VehicleOdometer or None on error.
    """
    vehicle = _get_smartcar_vehicle(access_token, vehicle_id)
    if not vehicle:
        return None

    try:
        odometer = vehicle.odometer()
        return VehicleOdometer(
            distance=odometer.distance,
            timestamp=datetime.utcnow(),
        )
    except smartcar.exceptions.SmartcarException as e:
        logger.warning(f"Failed to get odometer: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting odometer: {e}")
        return None


def get_vehicle_fuel(
    access_token: str,
    vehicle_id: str,
) -> Optional[VehicleFuel]:
    """
    Get vehicle fuel level.

    Args:
        access_token: Valid access token.
        vehicle_id: Smartcar vehicle ID.

    Returns:
        VehicleFuel or None on error.
    """
    vehicle = _get_smartcar_vehicle(access_token, vehicle_id)
    if not vehicle:
        return None

    try:
        fuel = vehicle.fuel()
        return VehicleFuel(
            percent_remaining=fuel.percent_remaining,
            amount_remaining=getattr(fuel, "amount_remaining", None),
            range=getattr(fuel, "range", None),
        )
    except smartcar.exceptions.SmartcarException as e:
        # Fuel may not be available for EVs
        logger.debug(f"Fuel data not available: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting fuel: {e}")
        return None


def get_vehicle_battery(
    access_token: str,
    vehicle_id: str,
) -> Optional[VehicleBattery]:
    """
    Get vehicle battery level (for EVs/hybrids).

    Args:
        access_token: Valid access token.
        vehicle_id: Smartcar vehicle ID.

    Returns:
        VehicleBattery or None on error.
    """
    vehicle = _get_smartcar_vehicle(access_token, vehicle_id)
    if not vehicle:
        return None

    try:
        battery = vehicle.battery()
        return VehicleBattery(
            percent_remaining=battery.percent_remaining,
            range=getattr(battery, "range", None),
        )
    except smartcar.exceptions.SmartcarException as e:
        # Battery may not be available for non-EVs
        logger.debug(f"Battery data not available: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting battery: {e}")
        return None


def get_tire_pressure(
    access_token: str,
    vehicle_id: str,
) -> Optional[TirePressure]:
    """
    Get vehicle tire pressure readings.

    Args:
        access_token: Valid access token.
        vehicle_id: Smartcar vehicle ID.

    Returns:
        TirePressure or None on error.
    """
    vehicle = _get_smartcar_vehicle(access_token, vehicle_id)
    if not vehicle:
        return None

    try:
        tires = vehicle.tire_pressure()
        return TirePressure(
            front_left=getattr(tires, "front_left", None),
            front_right=getattr(tires, "front_right", None),
            rear_left=getattr(tires, "rear_left", None),
            rear_right=getattr(tires, "rear_right", None),
        )
    except smartcar.exceptions.SmartcarException as e:
        logger.warning(f"Failed to get tire pressure: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting tire pressure: {e}")
        return None


# =============================================================================
# Vehicle Control
# =============================================================================


def lock_vehicle(access_token: str, vehicle_id: str) -> bool:
    """
    Lock the vehicle.

    Args:
        access_token: Valid access token.
        vehicle_id: Smartcar vehicle ID.

    Returns:
        True if successful, False otherwise.
    """
    vehicle = _get_smartcar_vehicle(access_token, vehicle_id)
    if not vehicle:
        return False

    try:
        vehicle.lock()
        logger.info(f"Vehicle {vehicle_id} locked successfully")
        return True
    except smartcar.exceptions.SmartcarException as e:
        logger.error(f"Failed to lock vehicle: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error locking vehicle: {e}")
        return False


def unlock_vehicle(access_token: str, vehicle_id: str) -> bool:
    """
    Unlock the vehicle.

    Args:
        access_token: Valid access token.
        vehicle_id: Smartcar vehicle ID.

    Returns:
        True if successful, False otherwise.
    """
    vehicle = _get_smartcar_vehicle(access_token, vehicle_id)
    if not vehicle:
        return False

    try:
        vehicle.unlock()
        logger.info(f"Vehicle {vehicle_id} unlocked successfully")
        return True
    except smartcar.exceptions.SmartcarException as e:
        logger.error(f"Failed to unlock vehicle: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error unlocking vehicle: {e}")
        return False


# =============================================================================
# Comprehensive Data Retrieval
# =============================================================================


def get_comprehensive_vehicle_data(
    access_token: str,
    vehicle_id: str,
) -> Optional[VehicleData]:
    """
    Get all available vehicle data in one call.

    Uses partial application to create fetchers for each data type,
    then collects all available data into a single VehicleData object.

    Args:
        access_token: Valid access token.
        vehicle_id: Smartcar vehicle ID.

    Returns:
        VehicleData with all available telemetry, or None on total failure.
    """
    # Create partial functions for each data type
    data_fetchers: dict[str, Callable[[], Any]] = {
        "location": partial(get_vehicle_location, access_token, vehicle_id),
        "odometer": partial(get_vehicle_odometer, access_token, vehicle_id),
        "fuel": partial(get_vehicle_fuel, access_token, vehicle_id),
        "battery": partial(get_vehicle_battery, access_token, vehicle_id),
        "tire_pressure": partial(get_tire_pressure, access_token, vehicle_id),
    }

    # Fetch all data (None values are acceptable)
    data = {key: fetcher() for key, fetcher in data_fetchers.items()}

    # Check if we got any data at all
    if all(v is None for v in data.values()):
        logger.warning(f"No data available for vehicle {vehicle_id}")
        return None

    return VehicleData(
        vehicle_id=vehicle_id,
        location=data["location"],
        odometer=data["odometer"],
        fuel=data["fuel"],
        battery=data["battery"],
        tire_pressure=data["tire_pressure"],
        timestamp=datetime.utcnow(),
    )


# =============================================================================
# Token Validation
# =============================================================================


def ensure_valid_token(vehicle: Vehicle) -> Optional[dict[str, Any]]:
    """
    Ensure a vehicle has a valid access token, refreshing if needed.

    Args:
        vehicle: The vehicle to check.

    Returns:
        New token data if refreshed, None if still valid or refresh failed.
    """
    if not vehicle.tokens:
        logger.warning(f"Vehicle {vehicle.id} has no tokens")
        return None

    # Check if token is expired or will expire soon (5 min buffer)
    if vehicle.tokens.expiration:
        buffer = timedelta(minutes=5)
        if datetime.utcnow() + buffer < vehicle.tokens.expiration:
            # Token is still valid
            return None

    # Token needs refresh
    logger.info(f"Refreshing token for vehicle {vehicle.id}")
    return refresh_access_token(vehicle.tokens.refresh_token)
