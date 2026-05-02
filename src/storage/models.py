from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, ForeignKey, Text, JSON, Index, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import os

Base = declarative_base()


class Listing(Base):
    __tablename__ = 'listings'

    id = Column(Integer, primary_key=True)
    platform = Column(String(50), nullable=False)
    platform_id = Column(String(255), unique=True, nullable=False)
    url = Column(Text, nullable=False)
    title = Column(String(255))
    model = Column(String(100))
    generation = Column(String(50))
    year = Column(Integer)
    price = Column(Numeric(10, 2))
    price_currency = Column(String(3), default='USD')
    mileage = Column(Integer)
    mileage_unit = Column(String(5), default='miles')
    condition = Column(String(50))
    transmission = Column(String(20))
    title_status = Column(String(50))
    owner_count = Column(Integer)
    features_json = Column(JSON)
    has_service_records = Column(Boolean, default=False)
    has_accidents = Column(Boolean, default=False)
    seller_name = Column(String(255))
    seller_location = Column(String(255))
    image_urls = Column(JSON)
    raw_html = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String(20), default='active')

    history = relationship('ListingHistory', back_populates='listing', cascade='all, delete-orphan')
    alerts = relationship('Alert', back_populates='listing', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_platform_id', 'platform', 'platform_id'),
        Index('idx_created_at', 'created_at'),
        Index('idx_model_year', 'model', 'year'),
        Index('idx_price', 'price'),
        Index('idx_status', 'status'),
    )

    def __repr__(self):
        return f"<Listing(platform='{self.platform}', model='{self.model}', year={self.year}, price=${self.price})>"


class ListingHistory(Base):
    __tablename__ = 'listing_history'

    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey('listings.id', ondelete='CASCADE'), nullable=False)
    price = Column(Numeric(10, 2))
    mileage = Column(Integer)
    condition = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow)

    listing = relationship('Listing', back_populates='history')

    __table_args__ = (
        Index('idx_listing_timestamp', 'listing_id', 'timestamp'),
    )

    def __repr__(self):
        return f"<ListingHistory(listing_id={self.listing_id}, price=${self.price}, timestamp={self.timestamp})>"


class Alert(Base):
    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey('listings.id', ondelete='CASCADE'), nullable=False)
    alert_type = Column(String(50), default='new_match')  # new_match, price_drop, new_feature
    reason = Column(Text)
    steal_indicators = Column(JSON)
    confidence_score = Column(Numeric(3, 2))
    sent_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime)
    user_acknowledged = Column(Boolean, default=False)

    listing = relationship('Listing', back_populates='alerts')

    __table_args__ = (
        Index('idx_alert_sent', 'sent_at'),
        Index('idx_alert_listing', 'listing_id', 'sent_at'),
    )

    def __repr__(self):
        return f"<Alert(listing_id={self.listing_id}, type='{self.alert_type}', score={self.confidence_score})>"


class DedupLog(Base):
    __tablename__ = 'dedup_log'

    id = Column(Integer, primary_key=True)
    listing_hash = Column(String(64), unique=True, nullable=False)
    platform = Column(String(50))
    listing_id = Column(Integer, ForeignKey('listings.id', ondelete='SET NULL'))
    last_checked = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_dedup_created', 'created_at'),
    )

    def __repr__(self):
        return f"<DedupLog(hash={self.listing_hash}, platform='{self.platform}')>"


class MarketBaseline(Base):
    __tablename__ = 'market_baseline'

    id = Column(Integer, primary_key=True)
    model = Column(String(100), nullable=False)
    generation = Column(String(50))
    year_start = Column(Integer)
    year_end = Column(Integer)
    market_price = Column(Numeric(10, 2))
    updated_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String(255))

    __table_args__ = (
        Index('idx_market_model_year', 'model', 'year_start'),
    )

    def __repr__(self):
        return f"<MarketBaseline(model='{self.model}', years={self.year_start}-{self.year_end}, price=${self.market_price})>"


class ScraperLog(Base):
    __tablename__ = 'scraper_logs'

    id = Column(Integer, primary_key=True)
    platform = Column(String(50))
    status = Column(String(20))  # success, error, partial
    listings_found = Column(Integer, default=0)
    listings_processed = Column(Integer, default=0)
    errors = Column(Integer, default=0)
    runtime_seconds = Column(Integer)
    run_at = Column(DateTime, default=datetime.utcnow)
    error_message = Column(Text)

    __table_args__ = (
        Index('idx_scraper_logs_platform', 'platform', 'run_at'),
    )

    def __repr__(self):
        return f"<ScraperLog(platform='{self.platform}', status='{self.status}', run_at={self.run_at})>"
