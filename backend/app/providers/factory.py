from __future__ import annotations

from app.core.config import settings
from app.providers.base import FlightProvider, HotelProvider, WeatherProvider
from app.providers.fallback import (
    FallbackFlightProvider,
    FallbackHotelProvider,
    FallbackWeatherProvider,
)
from app.providers.mock_flight import MockFlightProvider, set_coordinates as set_flight_coords
from app.providers.mock_hotel import MockHotelProvider, set_cost_levels
from app.providers.mock_weather import MockWeatherProvider, set_climate_data
from app.services.destination_service import DestinationService
from app.schemas.search import ClimateAverage


def _setup_mock_data(dest_svc: DestinationService) -> None:
    coords: dict[str, tuple[float, float]] = {}
    cost_levels: dict[str, int] = {}
    climate_data: dict[str, dict[int, ClimateAverage]] = {}

    for d in dest_svc.get_all_destinations():
        coords[d.iata_code] = (d.latitude, d.longitude)
        cost_levels[d.iata_code] = d.cost_level
        month_data = {}
        for c in dest_svc._climates.get(d.id, []):
            month_data[c.month] = ClimateAverage(
                destination_iata=d.iata_code,
                month=c.month,
                temp_avg_c=c.temp_avg_c,
                temp_max_avg_c=c.temp_max_avg_c,
                temp_min_avg_c=c.temp_min_avg_c,
                precip_days=c.precip_days,
                precip_mm=c.precip_mm,
                sunshine_hours=c.sunshine_hours,
                uv_index_avg=c.uv_index_avg,
                wind_speed_avg_kmh=c.wind_speed_avg_kmh,
            )
        climate_data[d.iata_code] = month_data

    set_flight_coords(coords)
    set_cost_levels(cost_levels)
    set_climate_data(climate_data)


def create_flight_provider(dest_svc: DestinationService) -> FlightProvider:
    _setup_mock_data(dest_svc)
    mock = MockFlightProvider()

    provider_setting = settings.FLIGHT_PROVIDER

    if provider_setting == "mock":
        if settings.APP_ENV == "production":
            from app.providers.errors import ProviderError, ProviderErrorCode
            raise ProviderError("factory", ProviderErrorCode.CONFIGURATION_ERROR, detail="Mock provider not allowed in production")
        return mock

    if provider_setting == "duffel" or (provider_setting == "auto" and settings.DUFFEL_ENABLED and settings.DUFFEL_ACCESS_TOKEN):
        from app.providers.duffel_flight import DuffelFlightProvider
        primary = DuffelFlightProvider()
        return FallbackFlightProvider(primary=primary, fallback=mock)

    if provider_setting == "amadeus" or (provider_setting == "auto" and settings.AMADEUS_CLIENT_ID and settings.AMADEUS_CLIENT_SECRET):
        from app.providers.amadeus_flight import AmadeusFlightProvider
        primary = AmadeusFlightProvider()
        return FallbackFlightProvider(primary=primary, fallback=mock)

    if settings.APP_ENV == "production":
        from app.providers.errors import ProviderError, ProviderErrorCode
        raise ProviderError("factory", ProviderErrorCode.CONFIGURATION_ERROR, detail="No flight provider configured for production")

    return mock


def create_hotel_provider(dest_svc: DestinationService) -> HotelProvider:
    _setup_mock_data(dest_svc)
    mock = MockHotelProvider()

    if settings.AMADEUS_CLIENT_ID and settings.AMADEUS_CLIENT_SECRET:
        from app.providers.amadeus_hotel import AmadeusHotelProvider
        return FallbackHotelProvider(primary=AmadeusHotelProvider(), fallback=mock)

    return mock


def create_weather_provider(dest_svc: DestinationService) -> WeatherProvider:
    _setup_mock_data(dest_svc)
    mock = MockWeatherProvider()

    return FallbackWeatherProvider(
        primary=_create_real_weather_provider(dest_svc),
        fallback=mock,
    )


def _create_real_weather_provider(dest_svc: DestinationService | None = None) -> WeatherProvider:
    from app.providers.openmeteo_weather import OpenMeteoWeatherProvider
    return OpenMeteoWeatherProvider(destination_service=dest_svc)
