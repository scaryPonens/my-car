"""Integrations package for Smart Car VA."""

from integrations.supabase_client import (
    get_user_by_telegram_id,
    create_user,
    get_or_create_user,
    get_user_vehicles,
    create_vehicle,
    update_vehicle_tokens,
    get_vehicle_by_id,
)
from integrations.smartcar_client import (
    create_smartcar_client,
    get_auth_url,
    exchange_code_for_tokens,
    refresh_access_token,
    get_vehicle_info,
    get_vehicle_odometer,
    get_vehicle_fuel,
    get_vehicle_battery,
    lock_vehicle,
    unlock_vehicle,
    get_comprehensive_vehicle_data,
)

__all__ = [
    # Supabase
    "get_user_by_telegram_id",
    "create_user",
    "get_or_create_user",
    "get_user_vehicles",
    "create_vehicle",
    "update_vehicle_tokens",
    "get_vehicle_by_id",
    # Smartcar
    "create_smartcar_client",
    "get_auth_url",
    "exchange_code_for_tokens",
    "refresh_access_token",
    "get_vehicle_info",
    "get_vehicle_location",
    "get_vehicle_odometer",
    "get_vehicle_fuel",
    "get_vehicle_battery",
    "get_tire_pressure",
    "lock_vehicle",
    "unlock_vehicle",
    "get_comprehensive_vehicle_data",
]
