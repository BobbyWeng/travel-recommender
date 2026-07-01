from abc import ABC, abstractmethod
from datetime import date

from app.schemas.search import ClimateAverage, FlightResult, HotelResult, WeatherResult


class FlightProvider(ABC):
    @abstractmethod
    async def search_flights(
        self, origin: str, destination: str, depart_date: date, return_date: date
    ) -> FlightResult | None:
        ...

    @abstractmethod
    async def search_cheapest_dates(
        self, origin: str, destination: str, start_date: date, end_date: date
    ) -> list[FlightResult]:
        ...


class HotelProvider(ABC):
    @abstractmethod
    async def search_hotels(
        self, city_iata: str, check_in: date, check_out: date, adults: int = 2
    ) -> HotelResult | None:
        ...


class WeatherProvider(ABC):
    @abstractmethod
    async def get_forecast(
        self, lat: float, lon: float, start_date: date, end_date: date
    ) -> WeatherResult:
        ...

    @abstractmethod
    async def get_climate_average(self, lat: float, lon: float, month: int) -> ClimateAverage | None:
        ...
