"""
Supabase database client with functional programming patterns.

Uses decorator pattern for client injection and pure functions
for all database operations. All functions are designed to be
composable and side-effect free (except for the database itself).
"""

import logging
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from supabase import Client, create_client

from config.settings import settings
from models.schemas import User, Vehicle, VehicleStatus, VehicleTokens

logger = logging.getLogger(__name__)

T = TypeVar("T")


def get_supabase_client() -> Client:
    """
    Create a Supabase client instance.

    Uses the service key if available for admin operations,
    otherwise falls back to the anon key.

    Returns:
        A configured Supabase client.
    """
    key = settings.supabase_service_key or settings.supabase_key
    return create_client(settings.supabase_url, key)


def with_supabase_client(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator that injects a Supabase client as the first argument.

    This pattern allows functions to be pure (no global state)
    while still having access to the database client.

    Args:
        func: Function expecting a Supabase client as first arg.

    Returns:
        Wrapped function that creates and injects the client.

    Example:
        >>> @with_supabase_client
        ... def get_users(client: Client) -> list[User]:
        ...     return client.table("users").select("*").execute()
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        client = get_supabase_client()
        return func(client, *args, **kwargs)
    return wrapper


def safe_db_operation(
    func: Callable[..., T],
    default: Optional[T] = None,
) -> Callable[..., Optional[T]]:
    """
    Wrap a database function to handle errors gracefully.

    Args:
        func: Database function to wrap.
        default: Value to return on error.

    Returns:
        Wrapped function that catches exceptions.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            return default
    return wrapper


# =============================================================================
# User Operations
# =============================================================================


@with_supabase_client
def get_user_by_telegram_id(
    client: Client,
    telegram_id: int,
) -> Optional[User]:
    """
    Fetch a user by their Telegram ID.

    Args:
        client: Supabase client (injected by decorator).
        telegram_id: The Telegram user ID.

    Returns:
        The User if found, None otherwise.
    """
    try:
        response = (
            client.table("users")
            .select("*")
            .eq("telegram_id", telegram_id)
            .maybe_single()
            .execute()
        )
        if response.data:
            return User(**response.data)
        return None
    except Exception as e:
        logger.error(f"Error fetching user by telegram_id {telegram_id}: {e}")
        return None


@with_supabase_client
def create_user(
    client: Client,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> Optional[User]:
    """
    Create a new user in the database.

    Args:
        client: Supabase client (injected by decorator).
        telegram_id: The Telegram user ID.
        username: Optional Telegram username.
        first_name: Optional first name.
        last_name: Optional last name.

    Returns:
        The created User, or None on error.
    """
    try:
        data = {
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
        }
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        response = client.table("users").insert(data).execute()
        if response.data:
            return User(**response.data[0])
        return None
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return None


def get_or_create_user(
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> Optional[User]:
    """
    Get an existing user or create a new one.

    This is a compound operation that first attempts to fetch
    the user, and creates them if they don't exist.

    Args:
        telegram_id: The Telegram user ID.
        username: Optional Telegram username.
        first_name: Optional first name.
        last_name: Optional last name.

    Returns:
        The existing or newly created User.
    """
    user = get_user_by_telegram_id(telegram_id)
    if user:
        return user
    return create_user(telegram_id, username, first_name, last_name)


@with_supabase_client
def update_user(
    client: Client,
    user_id: str,
    **updates: Any,
) -> Optional[User]:
    """
    Update a user's information.

    Args:
        client: Supabase client (injected by decorator).
        user_id: The user's database ID.
        **updates: Fields to update.

    Returns:
        The updated User, or None on error.
    """
    try:
        # Filter out None values
        data = {k: v for k, v in updates.items() if v is not None}
        if not data:
            return None

        response = (
            client.table("users")
            .update(data)
            .eq("id", user_id)
            .execute()
        )
        if response.data:
            return User(**response.data[0])
        return None
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        return None


# =============================================================================
# Vehicle Operations
# =============================================================================


@with_supabase_client
def get_user_vehicles(
    client: Client,
    user_id: str,
) -> list[Vehicle]:
    """
    Get all vehicles for a user.

    Args:
        client: Supabase client (injected by decorator).
        user_id: The user's database ID.

    Returns:
        List of vehicles owned by the user.
    """
    try:
        response = (
            client.table("vehicles")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        return [_parse_vehicle(v) for v in response.data] if response.data else []
    except Exception as e:
        logger.error(f"Error fetching vehicles for user {user_id}: {e}")
        return []


@with_supabase_client
def get_vehicle_by_id(
    client: Client,
    vehicle_id: str,
) -> Optional[Vehicle]:
    """
    Get a vehicle by its database ID.

    Args:
        client: Supabase client (injected by decorator).
        vehicle_id: The vehicle's database ID.

    Returns:
        The Vehicle if found, None otherwise.
    """
    try:
        response = (
            client.table("vehicles")
            .select("*")
            .eq("id", vehicle_id)
            .maybe_single()
            .execute()
        )
        if response.data:
            return _parse_vehicle(response.data)
        return None
    except Exception as e:
        logger.error(f"Error fetching vehicle {vehicle_id}: {e}")
        return None


@with_supabase_client
def get_vehicle_by_smartcar_id(
    client: Client,
    smartcar_vehicle_id: str,
) -> Optional[Vehicle]:
    """
    Get a vehicle by its Smartcar vehicle ID.

    Args:
        client: Supabase client (injected by decorator).
        smartcar_vehicle_id: The Smartcar vehicle ID.

    Returns:
        The Vehicle if found, None otherwise.
    """
    try:
        response = (
            client.table("vehicles")
            .select("*")
            .eq("smartcar_vehicle_id", smartcar_vehicle_id)
            .maybe_single()
            .execute()
        )
        if response.data:
            return _parse_vehicle(response.data)
        return None
    except Exception as e:
        logger.error(f"Error fetching vehicle by smartcar_id {smartcar_vehicle_id}: {e}")
        return None


@with_supabase_client
def create_vehicle(
    client: Client,
    user_id: str,
    smartcar_vehicle_id: str,
    make: Optional[str] = None,
    model: Optional[str] = None,
    year: Optional[int] = None,
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
    token_expiration: Optional[datetime] = None,
) -> Optional[Vehicle]:
    """
    Create a new vehicle record.

    Args:
        client: Supabase client (injected by decorator).
        user_id: The owner's user ID.
        smartcar_vehicle_id: The Smartcar vehicle ID.
        make: Vehicle manufacturer.
        model: Vehicle model.
        year: Vehicle year.
        access_token: OAuth access token.
        refresh_token: OAuth refresh token.
        token_expiration: Token expiration timestamp.

    Returns:
        The created Vehicle, or None on error.
    """
    try:
        data = {
            "user_id": user_id,
            "smartcar_vehicle_id": smartcar_vehicle_id,
            "make": make,
            "model": model,
            "year": year,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expiration": token_expiration.isoformat() if token_expiration else None,
            "status": VehicleStatus.ACTIVE.value,
        }
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        response = client.table("vehicles").insert(data).execute()
        if response.data:
            return _parse_vehicle(response.data[0])
        return None
    except Exception as e:
        logger.error(f"Error creating vehicle: {e}")
        return None


@with_supabase_client
def update_vehicle_tokens(
    client: Client,
    vehicle_id: str,
    access_token: str,
    refresh_token: str,
    expiration: Optional[datetime] = None,
) -> Optional[Vehicle]:
    """
    Update a vehicle's OAuth tokens.

    Args:
        client: Supabase client (injected by decorator).
        vehicle_id: The vehicle's database ID.
        access_token: New access token.
        refresh_token: New refresh token.
        expiration: New token expiration time.

    Returns:
        The updated Vehicle, or None on error.
    """
    try:
        data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expiration": expiration.isoformat() if expiration else None,
            "status": VehicleStatus.ACTIVE.value,
        }

        response = (
            client.table("vehicles")
            .update(data)
            .eq("id", vehicle_id)
            .execute()
        )
        if response.data:
            return _parse_vehicle(response.data[0])
        return None
    except Exception as e:
        logger.error(f"Error updating vehicle tokens for {vehicle_id}: {e}")
        return None


@with_supabase_client
def update_vehicle_status(
    client: Client,
    vehicle_id: str,
    status: VehicleStatus,
) -> Optional[Vehicle]:
    """
    Update a vehicle's connection status.

    Args:
        client: Supabase client (injected by decorator).
        vehicle_id: The vehicle's database ID.
        status: New status.

    Returns:
        The updated Vehicle, or None on error.
    """
    try:
        response = (
            client.table("vehicles")
            .update({"status": status.value})
            .eq("id", vehicle_id)
            .execute()
        )
        if response.data:
            return _parse_vehicle(response.data[0])
        return None
    except Exception as e:
        logger.error(f"Error updating vehicle status for {vehicle_id}: {e}")
        return None


@with_supabase_client
def delete_vehicle(
    client: Client,
    vehicle_id: str,
) -> bool:
    """
    Delete a vehicle record.

    Args:
        client: Supabase client (injected by decorator).
        vehicle_id: The vehicle's database ID.

    Returns:
        True if deleted, False otherwise.
    """
    try:
        client.table("vehicles").delete().eq("id", vehicle_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error deleting vehicle {vehicle_id}: {e}")
        return False


# =============================================================================
# Helper Functions
# =============================================================================


def _parse_vehicle(data: dict[str, Any]) -> Vehicle:
    """
    Parse a vehicle record from the database.

    Handles token parsing and status conversion.

    Args:
        data: Raw database record.

    Returns:
        A Vehicle model instance.
    """
    # Build tokens if present
    tokens = None
    if data.get("access_token") and data.get("refresh_token"):
        expiration = None
        if data.get("token_expiration"):
            try:
                expiration = datetime.fromisoformat(
                    data["token_expiration"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass
        tokens = VehicleTokens(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expiration=expiration,
        )

    # Parse status
    status = VehicleStatus.PENDING
    if data.get("status"):
        try:
            status = VehicleStatus(data["status"])
        except ValueError:
            pass

    return Vehicle(
        id=data.get("id"),
        user_id=data["user_id"],
        smartcar_vehicle_id=data["smartcar_vehicle_id"],
        make=data.get("make"),
        model=data.get("model"),
        year=data.get("year"),
        tokens=tokens,
        status=status,
        created_at=_parse_datetime(data.get("created_at")),
        updated_at=_parse_datetime(data.get("updated_at")),
    )


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO datetime string."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
