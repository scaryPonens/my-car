"""
Unit tests for Smart Car VA models and utilities.

Uses pytest with async support for testing Pydantic models
and functional utilities.
"""

from datetime import datetime, timedelta

import pytest

from models.schemas import (
    ConversationMessage,
    LLMAction,
    LLMResponse,
    TirePressure,
    User,
    Vehicle,
    VehicleBattery,
    VehicleData,
    VehicleFuel,
    VehicleLocation,
    VehicleOdometer,
    VehicleStatus,
    VehicleTokens,
)
from utils.helpers import (
    Maybe,
    compose,
    filter_dict,
    filter_none,
    flatten,
    identity,
    map_dict,
    memoize,
    partition,
    pipe,
    safe_get,
)


# =============================================================================
# User Model Tests
# =============================================================================


class TestUserModel:
    """Tests for the User model."""

    def test_user_creation_minimal(self):
        """Test creating a user with minimal fields."""
        user = User(telegram_id=123456789)
        assert user.telegram_id == 123456789
        assert user.username is None
        assert user.first_name is None

    def test_user_creation_full(self):
        """Test creating a user with all fields."""
        user = User(
            id="uuid-123",
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert user.id == "uuid-123"
        assert user.telegram_id == 123456789
        assert user.username == "testuser"
        assert user.first_name == "Test"
        assert user.last_name == "User"

    def test_user_validation(self):
        """Test user validation requirements."""
        with pytest.raises(Exception):
            User()  # telegram_id is required


# =============================================================================
# Vehicle Model Tests
# =============================================================================


class TestVehicleModel:
    """Tests for the Vehicle model."""

    def test_vehicle_creation(self):
        """Test creating a vehicle."""
        vehicle = Vehicle(
            user_id="user-uuid",
            smartcar_vehicle_id="sc-vehicle-123",
            make="Tesla",
            model="Model 3",
            year=2023,
        )
        assert vehicle.user_id == "user-uuid"
        assert vehicle.smartcar_vehicle_id == "sc-vehicle-123"
        assert vehicle.make == "Tesla"
        assert vehicle.status == VehicleStatus.PENDING

    def test_vehicle_display_name(self):
        """Test vehicle display name property."""
        vehicle = Vehicle(
            user_id="user-uuid",
            smartcar_vehicle_id="sc-123",
            make="Ford",
            model="Mustang Mach-E",
            year=2024,
        )
        assert vehicle.display_name == "2024 Ford Mustang Mach-E"

    def test_vehicle_display_name_partial(self):
        """Test display name with missing fields."""
        vehicle = Vehicle(
            user_id="user-uuid",
            smartcar_vehicle_id="sc-123",
            make="Tesla",
        )
        assert vehicle.display_name == "Tesla"

    def test_vehicle_display_name_empty(self):
        """Test display name with no vehicle info."""
        vehicle = Vehicle(
            user_id="user-uuid",
            smartcar_vehicle_id="sc-123",
        )
        assert vehicle.display_name == "Unknown Vehicle"


# =============================================================================
# Vehicle Tokens Tests
# =============================================================================


class TestVehicleTokens:
    """Tests for the VehicleTokens model."""

    def test_tokens_creation(self):
        """Test creating vehicle tokens."""
        tokens = VehicleTokens(
            access_token="access-123",
            refresh_token="refresh-456",
            expiration=datetime.utcnow() + timedelta(hours=2),
        )
        assert tokens.access_token == "access-123"
        assert tokens.refresh_token == "refresh-456"
        assert not tokens.is_expired()

    def test_tokens_expired(self):
        """Test token expiration check."""
        tokens = VehicleTokens(
            access_token="access-123",
            refresh_token="refresh-456",
            expiration=datetime.utcnow() - timedelta(hours=1),
        )
        assert tokens.is_expired()

    def test_tokens_no_expiration(self):
        """Test tokens without expiration are considered expired."""
        tokens = VehicleTokens(
            access_token="access-123",
            refresh_token="refresh-456",
        )
        assert tokens.is_expired()


# =============================================================================
# Vehicle Data Models Tests
# =============================================================================


class TestVehicleDataModels:
    """Tests for vehicle data models."""

    def test_vehicle_location(self):
        """Test VehicleLocation model."""
        location = VehicleLocation(
            latitude=37.7749,
            longitude=-122.4194,
        )
        assert location.latitude == 37.7749
        assert location.longitude == -122.4194

    def test_vehicle_fuel(self):
        """Test VehicleFuel model."""
        fuel = VehicleFuel(
            percent_remaining=75.5,
            amount_remaining=45.0,
            range=450.0,
        )
        assert fuel.percent_remaining == 75.5
        assert fuel.range == 450.0

    def test_vehicle_battery(self):
        """Test VehicleBattery model."""
        battery = VehicleBattery(
            percent_remaining=85.0,
            range=320.0,
            is_plugged_in=True,
            charging_state="charging",
        )
        assert battery.percent_remaining == 85.0
        assert battery.is_plugged_in is True

    def test_vehicle_odometer(self):
        """Test VehicleOdometer model."""
        odometer = VehicleOdometer(distance=15234.5)
        assert odometer.distance == 15234.5

    def test_tire_pressure(self):
        """Test TirePressure model."""
        tires = TirePressure(
            front_left=220.0,
            front_right=220.0,
            rear_left=230.0,
            rear_right=230.0,
        )
        assert tires.front_left == 220.0
        assert tires.rear_right == 230.0

    def test_vehicle_data_composite(self):
        """Test VehicleData composite model."""
        data = VehicleData(
            vehicle_id="vehicle-123",
            location=VehicleLocation(latitude=37.7749, longitude=-122.4194),
            fuel=VehicleFuel(percent_remaining=50.0),
            odometer=VehicleOdometer(distance=10000.0),
        )
        assert data.vehicle_id == "vehicle-123"
        assert data.location.latitude == 37.7749
        assert data.fuel.percent_remaining == 50.0


# =============================================================================
# LLM Response Tests
# =============================================================================


class TestLLMResponse:
    """Tests for LLM response models."""

    def test_llm_response_creation(self):
        """Test creating an LLM response."""
        response = LLMResponse(
            message="Your car is locked.",
            action=LLMAction.LOCK,
            confidence=0.95,
        )
        assert response.message == "Your car is locked."
        assert response.action == LLMAction.LOCK
        assert response.confidence == 0.95

    def test_llm_response_defaults(self):
        """Test LLM response default values."""
        response = LLMResponse(message="Hello!")
        assert response.action == LLMAction.NONE
        assert response.parameters == {}
        assert response.confidence == 1.0

    def test_llm_action_enum(self):
        """Test LLMAction enum values."""
        assert LLMAction.GET_STATUS.value == "get_status"
        assert LLMAction.LOCK.value == "lock"
        assert LLMAction.UNLOCK.value == "unlock"

    def test_conversation_message(self):
        """Test ConversationMessage model."""
        msg = ConversationMessage(
            role="user",
            content="What's my fuel level?",
        )
        assert msg.role == "user"
        assert msg.content == "What's my fuel level?"


# =============================================================================
# Functional Utilities Tests
# =============================================================================


class TestPipeAndCompose:
    """Tests for pipe and compose utilities."""

    def test_pipe(self):
        """Test left-to-right function composition."""
        add_one = lambda x: x + 1
        double = lambda x: x * 2
        pipeline = pipe(add_one, double)
        assert pipeline(5) == 12  # (5 + 1) * 2

    def test_compose(self):
        """Test right-to-left function composition."""
        add_one = lambda x: x + 1
        double = lambda x: x * 2
        composed = compose(add_one, double)
        assert composed(5) == 11  # (5 * 2) + 1

    def test_identity(self):
        """Test identity function."""
        assert identity(42) == 42
        assert identity("hello") == "hello"
        assert identity(None) is None


class TestMaybe:
    """Tests for Maybe monad."""

    def test_maybe_just(self):
        """Test Maybe with a value."""
        m = Maybe(42)
        assert m.is_just
        assert not m.is_nothing
        assert m.get_or(0) == 42

    def test_maybe_nothing(self):
        """Test Maybe with None."""
        m = Maybe(None)
        assert m.is_nothing
        assert not m.is_just
        assert m.get_or(0) == 0

    def test_maybe_map(self):
        """Test Maybe map operation."""
        m = Maybe(5)
        result = m.map(lambda x: x * 2)
        assert result.get_or(0) == 10

    def test_maybe_map_nothing(self):
        """Test Maybe map with Nothing."""
        m = Maybe(None)
        result = m.map(lambda x: x * 2)
        assert result.is_nothing

    def test_maybe_flat_map(self):
        """Test Maybe flat_map operation."""
        m = Maybe(5)
        result = m.flat_map(lambda x: Maybe(x * 2))
        assert result.get_or(0) == 10

    def test_maybe_filter(self):
        """Test Maybe filter operation."""
        m = Maybe(10)
        assert m.filter(lambda x: x > 5).get_or(0) == 10
        assert m.filter(lambda x: x > 15).is_nothing

    def test_maybe_get_or_else(self):
        """Test Maybe get_or_else with lazy default."""
        m = Maybe(None)
        result = m.get_or_else(lambda: "computed")
        assert result == "computed"


class TestDictOperations:
    """Tests for dictionary operations."""

    def test_filter_dict(self):
        """Test filtering dictionary entries."""
        d = {"a": 1, "b": 2, "c": 3}
        result = filter_dict(lambda k, v: v > 1, d)
        assert result == {"b": 2, "c": 3}

    def test_filter_none(self):
        """Test removing None values from dictionary."""
        d = {"a": 1, "b": None, "c": 3, "d": None}
        result = filter_none(d)
        assert result == {"a": 1, "c": 3}

    def test_map_dict(self):
        """Test mapping over dictionary entries."""
        d = {"a": 1, "b": 2}
        result = map_dict(lambda k, v: (k.upper(), v * 2), d)
        assert result == {"A": 2, "B": 4}

    def test_safe_get(self):
        """Test safe nested dictionary access."""
        d = {"user": {"profile": {"name": "Alice"}}}
        assert safe_get(d, "user", "profile", "name") == "Alice"
        assert safe_get(d, "user", "settings", "theme", default="dark") == "dark"
        assert safe_get(d, "nonexistent") is None


class TestListOperations:
    """Tests for list operations."""

    def test_flatten(self):
        """Test flattening nested lists."""
        nested = [[1, 2], [3, 4], [5]]
        assert flatten(nested) == [1, 2, 3, 4, 5]

    def test_flatten_empty(self):
        """Test flattening empty nested lists."""
        assert flatten([[], [], []]) == []

    def test_partition(self):
        """Test partitioning a list."""
        items = [1, 2, 3, 4, 5, 6]
        evens, odds = partition(lambda x: x % 2 == 0, items)
        assert evens == [2, 4, 6]
        assert odds == [1, 3, 5]


class TestMemoize:
    """Tests for memoization decorator."""

    def test_memoize_caches_result(self):
        """Test that memoize caches function results."""
        call_count = 0

        @memoize
        def expensive(n):
            nonlocal call_count
            call_count += 1
            return n * 2

        assert expensive(5) == 10
        assert expensive(5) == 10
        assert call_count == 1  # Only called once

    def test_memoize_different_args(self):
        """Test that memoize distinguishes arguments."""
        @memoize
        def add(a, b):
            return a + b

        assert add(1, 2) == 3
        assert add(2, 3) == 5
        assert add(1, 2) == 3  # Cached

    def test_memoize_clear_cache(self):
        """Test clearing memoize cache."""
        @memoize
        def func(x):
            return x

        func(1)
        assert len(func.cache) == 1
        func.clear_cache()
        assert len(func.cache) == 0


# =============================================================================
# Integration Test Examples
# =============================================================================


class TestModelIntegration:
    """Integration tests combining multiple models."""

    def test_user_with_vehicles(self):
        """Test user with associated vehicles."""
        user = User(
            id="user-123",
            telegram_id=123456789,
            username="carowner",
        )

        vehicle = Vehicle(
            id="vehicle-456",
            user_id=user.id,
            smartcar_vehicle_id="sc-vehicle-123",
            make="Tesla",
            model="Model 3",
            year=2023,
            tokens=VehicleTokens(
                access_token="token-123",
                refresh_token="refresh-456",
                expiration=datetime.utcnow() + timedelta(hours=2),
            ),
            status=VehicleStatus.ACTIVE,
        )

        assert vehicle.user_id == user.id
        assert vehicle.status == VehicleStatus.ACTIVE
        assert not vehicle.tokens.is_expired()

    def test_complete_vehicle_data(self):
        """Test complete vehicle data assembly."""
        data = VehicleData(
            vehicle_id="vehicle-123",
            location=VehicleLocation(latitude=37.7749, longitude=-122.4194),
            fuel=VehicleFuel(percent_remaining=65.0, range=520.0),
            battery=VehicleBattery(percent_remaining=80.0, range=400.0),
            odometer=VehicleOdometer(distance=25000.0),
            tire_pressure=TirePressure(
                front_left=220.0,
                front_right=222.0,
                rear_left=228.0,
                rear_right=230.0,
            ),
        )

        assert data.location.latitude == 37.7749
        assert data.fuel.percent_remaining == 65.0
        assert data.tire_pressure.front_left == 220.0


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
