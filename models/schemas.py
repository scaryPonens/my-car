"""
Pydantic data models for Smart Car VA.

All models are designed to be immutable and used as data transfer objects.
Uses strict type hints and validation for data integrity.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class VehicleStatus(str, Enum):
    """Vehicle connection status enumeration."""

    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    PENDING = "pending"
    ERROR = "error"


class LLMAction(str, Enum):
    """Supported LLM actions for vehicle control."""

    GET_STATUS = "get_status"
    GET_LOCATION = "get_location"
    GET_FUEL = "get_fuel"
    GET_BATTERY = "get_battery"
    GET_ODOMETER = "get_odometer"
    GET_TIRE_PRESSURE = "get_tire_pressure"
    LOCK = "lock"
    UNLOCK = "unlock"
    LIST_VEHICLES = "list_vehicles"
    HELP = "help"
    NONE = "none"


class User(BaseModel):
    """
    User model representing a Telegram user.

    Attributes:
        id: Database primary key (UUID).
        telegram_id: Unique Telegram user ID.
        username: Optional Telegram username.
        first_name: Optional user's first name.
        last_name: Optional user's last name.
        created_at: Timestamp of user creation.
        updated_at: Timestamp of last update.
    """

    id: Optional[str] = Field(default=None, description="Database UUID")
    telegram_id: int = Field(..., description="Telegram user ID")
    username: Optional[str] = Field(default=None, description="Telegram username")
    first_name: Optional[str] = Field(default=None, description="User's first name")
    last_name: Optional[str] = Field(default=None, description="User's last name")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")

    class Config:
        from_attributes = True


class VehicleTokens(BaseModel):
    """
    OAuth tokens for Smartcar API access.

    Attributes:
        access_token: Current access token.
        refresh_token: Token for refreshing access.
        expiration: Token expiration timestamp.
    """

    access_token: str = Field(..., description="Smartcar access token")
    refresh_token: str = Field(..., description="Smartcar refresh token")
    expiration: Optional[datetime] = Field(default=None, description="Token expiration time")

    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        if self.expiration is None:
            return True
        return datetime.utcnow() >= self.expiration


class Vehicle(BaseModel):
    """
    Vehicle model representing a connected car.

    Attributes:
        id: Database primary key (UUID).
        user_id: Foreign key to User.
        smartcar_vehicle_id: Unique Smartcar vehicle ID.
        make: Vehicle manufacturer.
        model: Vehicle model name.
        year: Vehicle model year.
        tokens: OAuth tokens for API access.
        status: Current connection status.
        created_at: Timestamp of vehicle registration.
        updated_at: Timestamp of last update.
    """

    id: Optional[str] = Field(default=None, description="Database UUID")
    user_id: str = Field(..., description="Owner's user ID")
    smartcar_vehicle_id: str = Field(..., description="Smartcar vehicle ID")
    make: Optional[str] = Field(default=None, description="Vehicle manufacturer")
    model: Optional[str] = Field(default=None, description="Vehicle model")
    year: Optional[int] = Field(default=None, description="Vehicle year")
    tokens: Optional[VehicleTokens] = Field(default=None, description="OAuth tokens")
    status: VehicleStatus = Field(default=VehicleStatus.PENDING, description="Connection status")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")

    class Config:
        from_attributes = True

    @property
    def display_name(self) -> str:
        """Get a human-readable vehicle name."""
        parts = [p for p in [self.year, self.make, self.model] if p]
        return " ".join(str(p) for p in parts) if parts else "Unknown Vehicle"


class VehicleLocation(BaseModel):
    """
    Vehicle location data.

    Attributes:
        latitude: GPS latitude coordinate.
        longitude: GPS longitude coordinate.
        timestamp: When the location was recorded.
    """

    latitude: float = Field(..., description="GPS latitude")
    longitude: float = Field(..., description="GPS longitude")
    timestamp: Optional[datetime] = Field(default=None, description="Location timestamp")


class VehicleFuel(BaseModel):
    """
    Vehicle fuel level data.

    Attributes:
        percent_remaining: Fuel level as percentage (0-100).
        amount_remaining: Fuel amount in liters (optional).
        range: Estimated range in kilometers (optional).
    """

    percent_remaining: Optional[float] = Field(default=None, description="Fuel percentage")
    amount_remaining: Optional[float] = Field(default=None, description="Fuel in liters")
    range: Optional[float] = Field(default=None, description="Estimated range in km")


class VehicleBattery(BaseModel):
    """
    Vehicle battery data (for EVs and hybrids).

    Attributes:
        percent_remaining: Battery level as percentage (0-100).
        range: Estimated range in kilometers.
        is_plugged_in: Whether the vehicle is plugged in.
        charging_state: Current charging state.
    """

    percent_remaining: Optional[float] = Field(default=None, description="Battery percentage")
    range: Optional[float] = Field(default=None, description="Estimated range in km")
    is_plugged_in: Optional[bool] = Field(default=None, description="Plugged in status")
    charging_state: Optional[str] = Field(default=None, description="Charging state")


class VehicleOdometer(BaseModel):
    """
    Vehicle odometer data.

    Attributes:
        distance: Total distance traveled in kilometers.
        timestamp: When the reading was taken.
    """

    distance: float = Field(..., description="Distance in kilometers")
    timestamp: Optional[datetime] = Field(default=None, description="Reading timestamp")


class TirePressure(BaseModel):
    """
    Vehicle tire pressure data.

    Attributes:
        front_left: Front left tire pressure in kPa.
        front_right: Front right tire pressure in kPa.
        rear_left: Rear left tire pressure in kPa.
        rear_right: Rear right tire pressure in kPa.
    """

    front_left: Optional[float] = Field(default=None, description="Front left pressure (kPa)")
    front_right: Optional[float] = Field(default=None, description="Front right pressure (kPa)")
    rear_left: Optional[float] = Field(default=None, description="Rear left pressure (kPa)")
    rear_right: Optional[float] = Field(default=None, description="Rear right pressure (kPa)")


class VehicleData(BaseModel):
    """
    Comprehensive vehicle data aggregating all telemetry.

    Attributes:
        vehicle_id: The vehicle this data belongs to.
        location: Current location data.
        fuel: Fuel level data.
        battery: Battery data (for EVs).
        odometer: Odometer reading.
        tire_pressure: Tire pressure readings.
        timestamp: When the data was collected.
    """

    vehicle_id: str = Field(..., description="Vehicle ID")
    location: Optional[VehicleLocation] = Field(default=None, description="Location data")
    fuel: Optional[VehicleFuel] = Field(default=None, description="Fuel data")
    battery: Optional[VehicleBattery] = Field(default=None, description="Battery data")
    odometer: Optional[VehicleOdometer] = Field(default=None, description="Odometer data")
    tire_pressure: Optional[TirePressure] = Field(default=None, description="Tire pressure data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Data timestamp")


class ConversationMessage(BaseModel):
    """
    A message in a conversation with the LLM.

    Attributes:
        role: The message role (user, assistant, system).
        content: The message content.
        timestamp: When the message was sent.
    """

    role: str = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")


class LLMResponse(BaseModel):
    """
    Structured response from the LLM.

    Attributes:
        message: The response message to display to user.
        action: The action to execute (if any).
        parameters: Parameters for the action.
        confidence: Confidence score for the action (0-1).
        raw_response: The raw LLM response for debugging.
    """

    message: str = Field(..., description="Response message")
    action: LLMAction = Field(default=LLMAction.NONE, description="Action to execute")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Action confidence")
    raw_response: Optional[str] = Field(default=None, description="Raw LLM response")


class VehicleTelemetry(BaseModel):
    """
    Historical vehicle telemetry record.

    Attributes:
        id: Database primary key.
        vehicle_id: Foreign key to Vehicle.
        data: The telemetry data snapshot.
        recorded_at: When the data was recorded.
    """

    id: Optional[str] = Field(default=None, description="Database UUID")
    vehicle_id: str = Field(..., description="Vehicle ID")
    data: VehicleData = Field(..., description="Telemetry data")
    recorded_at: datetime = Field(default_factory=datetime.utcnow, description="Record timestamp")

    class Config:
        from_attributes = True


class Conversation(BaseModel):
    """
    Conversation history for LLM context.

    Attributes:
        id: Database primary key.
        user_id: Foreign key to User.
        messages: List of conversation messages.
        created_at: When the conversation started.
        updated_at: Last message timestamp.
    """

    id: Optional[str] = Field(default=None, description="Database UUID")
    user_id: str = Field(..., description="User ID")
    messages: list[ConversationMessage] = Field(default_factory=list, description="Messages")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    class Config:
        from_attributes = True
