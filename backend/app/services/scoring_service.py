from __future__ import annotations

from app.schemas.search import (
    FlightResult,
    HotelResult,
    ScoreBreakdown,
    ScoredDestination,
    SearchConstraints,
    WeatherDay,
    WeatherResult,
)
from app.services.destination_service import ClimateInfo, DestinationInfo


WEIGHTS = {
    "flight": 0.30,
    "hotel": 0.20,
    "weather": 0.20,
    "preference_match": 0.15,
    "transport": 0.10,
    "activities": 0.05,
}

COMFORT_TEMP_RANGE = (18, 28)
HOT_TEMP_THRESHOLD = 35
COLD_TEMP_THRESHOLD = 5


class ScoringService:
    def score_flight(self, flight_price: float, budget: float) -> float:
        if budget <= 0:
            return 0
        ratio = flight_price / budget
        if ratio <= 0.4:
            return 100
        elif ratio <= 0.6:
            return 90
        elif ratio <= 0.8:
            return 70
        elif ratio <= 1.0:
            return 50
        else:
            return max(0, 50 - (ratio - 1.0) * 100)

    def score_hotel(self, hotel_total: float, budget: float, flight_price: float) -> float:
        remaining = budget - flight_price
        if remaining <= 0:
            return 0
        ratio = hotel_total / remaining
        if ratio <= 0.4:
            return 100
        elif ratio <= 0.6:
            return 90
        elif ratio <= 0.8:
            return 70
        elif ratio <= 1.0:
            return 50
        else:
            return max(0, 50 - (ratio - 1.0) * 100)

    def score_weather(
        self,
        weather: WeatherResult | list[WeatherDay],
        constraints: SearchConstraints,
    ) -> float:
        days = weather.days if isinstance(weather, WeatherResult) else weather
        if not days:
            return 50

        score = 70.0

        avg_max = sum(d.temp_max_c for d in days) / len(days)
        avg_min = sum(d.temp_min_c for d in days) / len(days)
        avg_precip_prob = sum(d.precip_probability for d in days) / len(days)

        if COMFORT_TEMP_RANGE[0] <= avg_max <= COMFORT_TEMP_RANGE[1]:
            score += 15
        elif COMFORT_TEMP_RANGE[0] - 5 <= avg_max <= COMFORT_TEMP_RANGE[1] + 5:
            score += 8

        if avg_precip_prob < 30:
            score += 10
        elif avg_precip_prob < 50:
            score += 5
        elif avg_precip_prob > 70:
            score -= 10

        if constraints.avoid_hot_weather and any(d.temp_max_c > HOT_TEMP_THRESHOLD for d in days):
            score -= 30

        if constraints.avoid_cold_weather and any(d.temp_min_c < COLD_TEMP_THRESHOLD for d in days):
            score -= 30

        return max(0, min(100, score))

    def score_preference_match(self, destination: DestinationInfo, preferences: list[str]) -> float:
        if not preferences:
            return 70
        matched = len(set(preferences) & set(destination.tags))
        ratio = matched / len(preferences)
        base_score = ratio * 80

        if destination.public_transport_score >= 7 and "public_transport" in preferences:
            base_score += 10

        return min(100, base_score)

    def score_transport(self, destination: DestinationInfo, constraints: SearchConstraints) -> float:
        score = destination.public_transport_score * 8 + destination.walkability_score * 2

        if constraints.no_car_rental and destination.public_transport_score < 5:
            score *= 0.3

        return min(100, max(0, score))

    def score_activities(self, destination: DestinationInfo, preferences: list[str]) -> float:
        tag_count = len(destination.tags)
        score = min(100, tag_count * 12)

        matched = len(set(preferences) & set(destination.tags))
        score += matched * 5

        return min(100, score)

    def compute_total_score(self, breakdown: ScoreBreakdown) -> float:
        return round(
            breakdown.flight * WEIGHTS["flight"]
            + breakdown.hotel * WEIGHTS["hotel"]
            + breakdown.weather * WEIGHTS["weather"]
            + breakdown.preference_match * WEIGHTS["preference_match"]
            + breakdown.transport * WEIGHTS["transport"]
            + breakdown.activities * WEIGHTS["activities"],
            1,
        )

    def check_hard_constraints(
        self,
        flight: FlightResult | None,
        hotel: HotelResult | None,
        weather: WeatherResult | None,
        destination: DestinationInfo,
        budget: float,
        constraints: SearchConstraints,
    ) -> tuple[bool, list[str]]:
        warnings: list[str] = []

        if flight is None:
            return False, ["无法获取航班数据"]

        if hotel is None:
            return False, ["无法获取酒店数据"]

        total = flight.price + hotel.total_price
        if total > budget:
            warnings.append(f"总费用 ${total:.0f} 超出预算 ${budget:.0f}")
            return False, warnings

        if constraints.max_flight_hours is not None:
            flight_hours = flight.total_duration_min / 60
            if flight_hours > constraints.max_flight_hours:
                warnings.append(f"飞行时间 {flight_hours:.1f}h 超出限制 {constraints.max_flight_hours}h")
                return False, warnings

        if constraints.max_stops is not None:
            if flight.stops > constraints.max_stops:
                warnings.append(f"中转 {flight.stops} 次超出限制 {constraints.max_stops}")
                return False, warnings

        if constraints.avoid_hot_weather and weather:
            if any(d.temp_max_c > HOT_TEMP_THRESHOLD for d in weather.days):
                warnings.append(f"存在最高温超过 {HOT_TEMP_THRESHOLD}°C 的日期")
                return False, warnings

        if constraints.avoid_cold_weather and weather:
            if any(d.temp_min_c < COLD_TEMP_THRESHOLD for d in weather.days):
                warnings.append(f"存在最低温低于 {COLD_TEMP_THRESHOLD}°C 的日期")
                return False, warnings

        if constraints.no_car_rental and destination.public_transport_score < 5:
            warnings.append("目的地公共交通不便，但用户不愿租车")
            return False, warnings

        return True, warnings

    def generate_pros_cons_reason(
        self,
        destination: DestinationInfo,
        flight: FlightResult,
        hotel: HotelResult,
        weather: WeatherResult | None,
        scores: ScoreBreakdown,
        preferences: list[str],
        budget: float,
    ) -> tuple[list[str], list[str], str]:
        pros: list[str] = []
        cons: list[str] = []

        total = flight.price + hotel.total_price
        budget_ratio = total / budget if budget > 0 else 1

        if budget_ratio <= 0.7:
            pros.append(f"预算宽裕，预计花费 ${total:.0f}")
        elif budget_ratio <= 0.9:
            pros.append(f"在预算范围内，预计花费 ${total:.0f}")
        else:
            cons.append(f"接近预算上限，预计花费 ${total:.0f}")

        if scores.flight >= 80:
            pros.append("机票价格合理")
        elif scores.flight < 50:
            cons.append("机票较贵")

        if scores.hotel >= 80:
            pros.append("住宿性价比高")
        elif scores.hotel < 50:
            cons.append("住宿费用偏高")

        if scores.weather >= 80:
            pros.append("天气舒适")
        elif scores.weather < 50:
            cons.append("天气不太理想")

        matched_prefs = set(preferences) & set(destination.tags)
        if matched_prefs:
            pros.append(f"符合偏好: {', '.join(matched_prefs)}")

        unmatched = set(preferences) - set(destination.tags)
        if "public_transport" in unmatched and destination.public_transport_score < 7:
            cons.append("公共交通不够便利")

        if destination.public_transport_score >= 7:
            pros.append("公共交通便利，无需租车")
        elif destination.public_transport_score < 5:
            cons.append("可能需要租车")

        if flight.stops == 0:
            pros.append("直飞航班")
        elif flight.stops >= 2:
            cons.append(f"需要中转 {flight.stops} 次")

        reason_parts = []
        if matched_prefs:
            reason_parts.append(f"满足 {', '.join(matched_prefs)} 偏好")
        if scores.weather >= 70:
            reason_parts.append("天气适宜")
        if budget_ratio <= 0.8:
            reason_parts.append("价格合理")
        reason = "；".join(reason_parts) if reason_parts else "综合评分较高"

        return pros, cons, reason
