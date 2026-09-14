from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import Session
from app.db.models.weather import RawWeatherRecord, BlockWeatherForecast, WeatherObservation
from app.db.models.spatial import Block
from app.core.logging import logger


class WeatherRepository:
    """
    Data access repository for weather entities (Raw records, Block forecasts, and AWS observations).
    """

    def __init__(self, db: Session):
        self.db = db

    def insert_raw_record(
        self,
        source: str,
        raw_payload: Dict[str, Any],
        source_file: Optional[str] = None,
        checksum: Optional[str] = None,
        records_count: int = 0,
        processing_status: str = "PROCESSED"
    ) -> RawWeatherRecord:
        """Stores untouched raw input payload for provenance tracking."""
        record = RawWeatherRecord(
            source=source,
            source_file=source_file,
            checksum=checksum,
            raw_payload=raw_payload,
            records_count=records_count,
            processing_status=processing_status,
            ingested_at=datetime.utcnow(),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def find_block_by_identifier(self, identifier: str) -> Optional[Block]:
        """Finds block by LGD code or case-insensitive name."""
        clean_id = str(identifier).strip()
        stmt = select(Block).where(
            (Block.lgd_code == clean_id) | (func.lower(Block.name) == clean_id.lower())
        )
        return self.db.scalars(stmt).first()

    def get_or_create_block_placeholder(self, block_name_or_code: str) -> Block:
        """Finds existing Block or creates an unmapped placeholder Block for ingestion."""
        existing = self.find_block_by_identifier(block_name_or_code)
        if existing:
            return existing

        # Create unmapped placeholder block for newly discovered forecast territory
        new_block = Block(
            lgd_code=f"BLOCK_{block_name_or_code.upper().replace(' ', '_')}",
            name=block_name_or_code.title(),
            district_name="Unassigned District",
            state_name="Unassigned State",
        )
        self.db.add(new_block)
        self.db.commit()
        self.db.refresh(new_block)
        logger.info(f"Created placeholder Block record: ID {new_block.id}, Name: {new_block.name}")
        return new_block

    def find_existing_forecast(
        self,
        block_id: int,
        forecast_date: datetime,
        issue_time: datetime,
        source_model: str
    ) -> Optional[BlockWeatherForecast]:
        """Identifies duplicate forecast run for the same block, valid_time, issue_time, and model."""
        stmt = select(BlockWeatherForecast).where(
            and_(
                BlockWeatherForecast.block_id == block_id,
                BlockWeatherForecast.forecast_date == forecast_date,
                BlockWeatherForecast.issue_time == issue_time,
                BlockWeatherForecast.source_model == source_model,
            )
        )
        return self.db.scalars(stmt).first()

    def insert_forecast(self, forecast: BlockWeatherForecast) -> BlockWeatherForecast:
        """Persists a single validated/normalized forecast record."""
        self.db.add(forecast)
        self.db.commit()
        self.db.refresh(forecast)
        return forecast

    def bulk_insert_forecasts(self, forecasts: List[BlockWeatherForecast]) -> int:
        """Persists multiple forecasts in a single transaction."""
        if not forecasts:
            return 0
        self.db.add_all(forecasts)
        self.db.commit()
        return len(forecasts)

    def find_existing_observation(
        self,
        station_id: str,
        observation_time: datetime,
        source: str
    ) -> Optional[WeatherObservation]:
        """Checks for duplicate station observation."""
        stmt = select(WeatherObservation).where(
            and_(
                WeatherObservation.station_id == station_id,
                WeatherObservation.observation_time == observation_time,
                WeatherObservation.source == source,
            )
        )
        return self.db.scalars(stmt).first()

    def insert_observation(self, observation: WeatherObservation) -> WeatherObservation:
        """Persists a single station observation."""
        self.db.add(observation)
        self.db.commit()
        self.db.refresh(observation)
        return observation

    def bulk_insert_observations(self, observations: List[WeatherObservation]) -> int:
        """Persists multiple observations in a single transaction."""
        if not observations:
            return 0
        self.db.add_all(observations)
        self.db.commit()
        return len(observations)

    def get_forecasts(
        self,
        block_id: Optional[int] = None,
        block_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        source_model: Optional[str] = None,
        quality_flag: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[BlockWeatherForecast], int]:
        """Queries paginated block weather forecasts with optional filters."""
        query = select(BlockWeatherForecast).join(BlockWeatherForecast.block)

        conditions = []
        if block_id:
            conditions.append(BlockWeatherForecast.block_id == block_id)
        if block_name:
            conditions.append(func.lower(Block.name).like(f"%{block_name.lower()}%"))
        if start_time:
            conditions.append(BlockWeatherForecast.forecast_date >= start_time)
        if end_time:
            conditions.append(BlockWeatherForecast.forecast_date <= end_time)
        if source_model:
            conditions.append(BlockWeatherForecast.source_model == source_model)
        if quality_flag:
            conditions.append(BlockWeatherForecast.quality_flag == quality_flag.upper())

        if conditions:
            query = query.where(and_(*conditions))

        # Total count query
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.scalar(count_query) or 0

        # Paginated results
        offset = (page - 1) * page_size
        results = self.db.scalars(
            query.order_by(desc(BlockWeatherForecast.forecast_date), desc(BlockWeatherForecast.issue_time))
            .offset(offset)
            .limit(page_size)
        ).all()

        return list(results), total

    def get_observations(
        self,
        station_id: Optional[str] = None,
        block_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        source: Optional[str] = None,
        quality_flag: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[WeatherObservation], int]:
        """Queries paginated station/AWS observations with optional filters."""
        query = select(WeatherObservation)

        conditions = []
        if station_id:
            conditions.append(WeatherObservation.station_id == station_id)
        if block_id:
            conditions.append(WeatherObservation.block_id == block_id)
        if start_time:
            conditions.append(WeatherObservation.observation_time >= start_time)
        if end_time:
            conditions.append(WeatherObservation.observation_time <= end_time)
        if source:
            conditions.append(WeatherObservation.source == source)
        if quality_flag:
            conditions.append(WeatherObservation.quality_flag == quality_flag.upper())

        if conditions:
            query = query.where(and_(*conditions))

        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.scalar(count_query) or 0

        offset = (page - 1) * page_size
        results = self.db.scalars(
            query.order_by(desc(WeatherObservation.observation_time))
            .offset(offset)
            .limit(page_size)
        ).all()

        return list(results), total

    def get_stats(self) -> Dict[str, Any]:
        """Returns summary statistics on weather database tables."""
        total_forecasts = self.db.scalar(select(func.count(BlockWeatherForecast.id))) or 0
        valid_forecasts = self.db.scalar(
            select(func.count(BlockWeatherForecast.id)).where(BlockWeatherForecast.quality_flag == "VALID")
        ) or 0
        suspicious_forecasts = self.db.scalar(
            select(func.count(BlockWeatherForecast.id)).where(BlockWeatherForecast.quality_flag == "SUSPICIOUS")
        ) or 0
        total_observations = self.db.scalar(select(func.count(WeatherObservation.id))) or 0
        total_raw_batches = self.db.scalar(select(func.count(RawWeatherRecord.id))) or 0

        return {
            "total_block_forecasts": total_forecasts,
            "valid_forecasts": valid_forecasts,
            "suspicious_forecasts": suspicious_forecasts,
            "total_observations": total_observations,
            "raw_ingestion_batches": total_raw_batches,
        }
