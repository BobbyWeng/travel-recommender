from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.destination import (
    Airport,
    Base,
    Destination,
    DestinationMonthlyClimate,
    DestinationTag,
)


def init_db(db_url: str | None = None) -> None:
    engine = create_engine(db_url or settings.DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)

    data_path = Path(__file__).parent.parent.parent.parent / "data" / "destinations.json"
    if not data_path.exists():
        print(f"数据文件不存在: {data_path}")
        return

    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    with Session(engine) as session:
        existing = session.query(Destination).count()
        if existing > 0:
            print(f"数据库已有 {existing} 个目的地，跳过初始化")
            return

        for d in data.get("destinations", []):
            dest = Destination(
                id=d["id"],
                city=d["city"],
                state=d["state"],
                country=d.get("country", "United States"),
                country_code=d.get("country_code", "US"),
                iata_code=d["iata_code"],
                latitude=d["latitude"],
                longitude=d["longitude"],
                timezone=d["timezone"],
                cost_level=d["cost_level"],
                public_transport_score=d["public_transport_score"],
                walkability_score=d.get("walkability_score", 5),
                active=d.get("active", True),
            )
            session.add(dest)

            for tag in d.get("tags", []):
                session.add(DestinationTag(destination_id=d["id"], tag=tag))

            for c in d.get("monthly_climate", []):
                session.add(
                    DestinationMonthlyClimate(
                        destination_id=d["id"],
                        month=c["month"],
                        temp_avg_c=c.get("temp_avg_c"),
                        temp_max_avg_c=c.get("temp_max_avg_c"),
                        temp_min_avg_c=c.get("temp_min_avg_c"),
                        precip_days=c.get("precip_days"),
                        precip_mm=c.get("precip_mm"),
                        sunshine_hours=c.get("sunshine_hours"),
                        uv_index_avg=c.get("uv_index_avg"),
                        wind_speed_avg_kmh=c.get("wind_speed_avg_kmh"),
                    )
                )

            session.add(
                Airport(
                    iata_code=d["iata_code"],
                    name=f"{d['city']} Airport",
                    city=d["city"],
                    state=d["state"],
                    country_code=d.get("country_code", "US"),
                    latitude=d["latitude"],
                    longitude=d["longitude"],
                    is_hub=d["iata_code"] in {"ATL", "ORD", "DFW", "DEN", "LAX", "JFK"},
                )
            )

        session.commit()
        print(f"已初始化 {len(data.get('destinations', []))} 个目的地到数据库")


if __name__ == "__main__":
    init_db()
