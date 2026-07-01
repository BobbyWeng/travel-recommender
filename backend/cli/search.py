import asyncio
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.search import SearchConstraints, SearchRequestSchema
from app.providers.factory import create_flight_provider, create_hotel_provider, create_weather_provider
from app.services.destination_service import DestinationService
from app.services.flight_service import FlightService
from app.services.hotel_service import HotelService
from app.services.scoring_service import ScoringService
from app.services.search_orchestrator import SearchOrchestrator
from app.services.weather_service import WeatherService
from app.core.cache import flight_cache, hotel_cache, weather_cache


def build_orchestrator(data_path: str) -> SearchOrchestrator:
    dest_svc = DestinationService(data_path)

    flight_cache.clear()
    hotel_cache.clear()
    weather_cache.clear()

    return SearchOrchestrator(
        destination_service=dest_svc,
        flight_service=FlightService(create_flight_provider(dest_svc)),
        hotel_service=HotelService(create_hotel_provider(dest_svc)),
        weather_service=WeatherService(create_weather_provider(dest_svc)),
        scoring_service=ScoringService(),
    )


def format_result(response) -> None:
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    console.print()
    console.print(
        f"[bold cyan]搜索完成[/] - "
        f"评估了 {response.total_candidates_evaluated} 个候选，"
        f"过滤了 {response.total_candidates_filtered} 个"
    )
    console.print(f"数据来源: [yellow]{response.data_source}[/]")
    console.print()

    if not response.top_results:
        console.print("[red]没有找到符合条件的目的地[/]")
        return

    console.rule("[bold green]Top 5 推荐目的地[/bold green]")

    for i, r in enumerate(response.top_results, 1):
        content_lines = [
            f"[bold]{i}. {r.city}, {r.state}[/]",
            f"最佳日期: {r.departure_date} ~ {r.return_date} ({r.nights}晚)",
            f"机票: ${r.flight_price:.0f}  酒店: ${r.hotel_price:.0f}  总计: [bold]${r.estimated_total:.0f}[/]",
            f"天气: {r.weather_summary}",
            f"总分: [bold green]{r.total_score:.1f}[/]  来源: [dim]{r.data_source}[/]",
        ]

        if r.pros:
            content_lines.append("[green]优点:[/]")
            for p in r.pros:
                content_lines.append(f"  ✅ {p}")
        if r.cons:
            content_lines.append("[red]缺点:[/]")
            for c in r.cons:
                content_lines.append(f"  ⚠️ {c}")

        content_lines.append(f"[dim]推荐理由: {r.recommendation_reason}[/]")

        panel = Panel("\n".join(content_lines), border_style="green" if i <= 2 else "blue")
        console.print(panel)

    console.rule()


async def run_search(params: dict) -> None:
    data_path = Path(__file__).parent.parent.parent / "data" / "destinations.json"
    orchestrator = build_orchestrator(str(data_path))

    request = SearchRequestSchema(
        origin=params["origin"],
        preferred_departure_date=date.fromisoformat(params["date"]),
        date_flexibility_days=params["flex"],
        trip_length_min=params["min_nights"],
        trip_length_max=params["max_nights"],
        budget=params["budget"],
        preferences=params.get("preferences", []),
        constraints=SearchConstraints(
            max_flight_hours=params.get("max_flight_hours"),
            max_stops=params.get("max_stops"),
            avoid_hot_weather=params.get("avoid_hot_weather", False),
            avoid_cold_weather=params.get("avoid_cold_weather", False),
            no_car_rental=params.get("no_car_rental", False),
            domestic_only=True,
        ),
    )

    response = await orchestrator.execute(request)
    format_result(response)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="AI 旅行目的地推荐系统")
    parser.add_argument("--origin", required=True, help="出发机场 IATA 代码 (如 ATL)")
    parser.add_argument("--date", required=True, help="首选出发日期 (YYYY-MM-DD)")
    parser.add_argument("--flex", type=int, default=5, help="日期浮动天数 (默认 5)")
    parser.add_argument("--min-nights", type=int, default=4, help="最短旅行天数 (默认 4)")
    parser.add_argument("--max-nights", type=int, default=6, help="最长旅行天数 (默认 6)")
    parser.add_argument("--budget", type=float, required=True, help="总预算 (USD)")
    parser.add_argument("--preferences", nargs="*", default=[], help="旅行偏好标签")
    parser.add_argument("--max-flight-hours", type=int, help="最大飞行时间 (小时)")
    parser.add_argument("--max-stops", type=int, help="最大中转次数")
    parser.add_argument("--avoid-hot-weather", action="store_true", help="避免炎热天气")
    parser.add_argument("--avoid-cold-weather", action="store_true", help="避免寒冷天气")
    parser.add_argument("--no-car-rental", action="store_true", help="不租车")

    args = parser.parse_args()

    params = {
        "origin": args.origin.upper(),
        "date": args.date,
        "flex": args.flex,
        "min_nights": args.min_nights,
        "max_nights": args.max_nights,
        "budget": args.budget,
        "preferences": args.preferences,
        "max_flight_hours": args.max_flight_hours,
        "max_stops": args.max_stops,
        "avoid_hot_weather": args.avoid_hot_weather,
        "avoid_cold_weather": args.avoid_cold_weather,
        "no_car_rental": args.no_car_rental,
    }

    asyncio.run(run_search(params))


if __name__ == "__main__":
    main()
