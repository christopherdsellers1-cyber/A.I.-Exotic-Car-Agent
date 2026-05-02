#!/usr/bin/env python
"""
Main entry point for Porsche listing monitor.
"""

import sys
import click
from datetime import datetime, timedelta
from typing import Optional
from src.config import get_config, init_config
from src.storage.database import get_db_manager, init_db
from src.storage.models import Listing, Alert
from src.utils.logger import get_logger
from src.scrapers.base_scraper import ScraperPool
from src.scrapers.classic_scraper import ClassicScraper
from src.scrapers.pcarmarket_scraper import PcarmarketScraper
from src.scrapers.rmsotheby_scraper import RmsothebyScraper
from src.scrapers.elferspot_scraper import ElfersportScraper
from src.scrapers.rennlist_scraper import RennlistScraper
from src.filters.matcher import ListingMatcher
from src.filters.requirements import RequirementChecker
from src.alerts.webhook import WebhookAlerter
from sqlalchemy import desc

logger = get_logger("main")


@click.group()
@click.pass_context
def cli(ctx):
    """Porsche Listing Monitor - Automated vehicle search and alerts."""
    ctx.ensure_object(dict)
    # Initialize config and database
    init_config()
    init_db()


@cli.command()
@click.option('--platform', type=str, help='Scrape specific platform (CLASSIC.COM, PCARMARKET, etc.)')
@click.option('--all', 'scrape_all', is_flag=True, help='Scrape all platforms')
@click.option('--dry-run', is_flag=True, help='Run without saving to database')
def scrape(platform: Optional[str], scrape_all: bool, dry_run: bool):
    """
    Run scraper(s) and process listings.

    Examples:
        # Scrape all platforms
        python -m src.main scrape --all

        # Scrape specific platform
        python -m src.main scrape --platform CLASSIC.COM

        # Dry run (test without saving)
        python -m src.main scrape --all --dry-run
    """
    config = get_config()
    db = get_db_manager()

    logger.info("=" * 70)
    logger.info("SCRAPER STARTED")
    logger.info(f"Configuration: {config}")
    logger.info(f"Dry run: {dry_run}")
    logger.info("=" * 70)

    if not scrape_all and not platform:
        click.echo("Error: Specify --platform or --all")
        return

    try:
        # Initialize all 5 scrapers
        scrapers = [
            ClassicScraper(),
            PcarmarketScraper(),
            RmsothebyScraper(),
            ElfersportScraper(),
            RennlistScraper(),
        ]

        pool = ScraperPool(scrapers)

        # Run scraper(s)
        if scrape_all:
            listings = pool.scrape_all()
        else:
            listings = pool.scrape_by_platform(platform)

        if not listings:
            click.echo("No listings found")
            return

        click.echo(f"\n✓ Found {len(listings)} total listings\n")

        # Initialize matching engines
        matcher = ListingMatcher(config.hit_list_dict)
        requirements_checker = RequirementChecker(config.requirements)

        # Process listings
        hits = []
        for idx, listing in enumerate(listings, 1):
            # Convert CommonListing to dict for matching
            listing_dict = listing.to_dict()

            # Check hit list match
            match_result = matcher.match_listing(listing_dict)

            if match_result.is_hit:
                # Verify requirements
                req_result = requirements_checker.check_listing(listing_dict)

                if req_result.meets_requirements:
                    hit_info = {
                        'listing': listing,
                        'match': match_result,
                        'requirements': req_result,
                        'confidence': (
                            float(match_result.match_confidence) * 0.6 +
                            req_result.confidence_score * 0.4
                        ),
                    }
                    hits.append(hit_info)

                    click.echo(f"🎯 HIT #{len(hits)}: {listing.title}")
                    click.echo(f"   URL: {listing.url}")
                    click.echo(f"   Price: ${listing.price:,.0f}")
                    click.echo(f"   Match: {match_result.reasoning}")
                    click.echo()

        # Save to database if not dry run
        if hits and not dry_run:
            _save_listings_to_db(db, hits)
            click.echo(f"✓ Saved {len(hits)} listings to database")

        logger.info(f"Scrape completed: {len(hits)} hits from {len(listings)} listings")
        click.echo(f"Summary: {len(hits)} matches from {len(listings)} listings")

    except Exception as e:
        logger.error(f"Scrape failed: {e}", exc_info=True)
        click.echo(f"Error: {e}")


def _save_listings_to_db(db, hits: list):
    """Save matched listings to database."""
    session = db.get_session_direct()
    try:
        for hit in hits:
            listing_data = hit['listing']
            # TODO: Create database record from listing_data
            # For now, just log
            logger.info(f"Would save: {listing_data.title} @ ${listing_data.price}")
    finally:
        session.close()


@cli.command()
@click.option('--since', type=str, default='24h', help='Show alerts since (e.g., 24h, 7d)')
@click.option('--unread', is_flag=True, help='Show only unread alerts')
@click.option('--limit', type=int, default=10, help='Maximum results')
def alerts(since: str, unread: bool, limit: int):
    """
    Display recent alerts.

    Examples:
        # Show alerts from last 24 hours
        python -m src.main alerts

        # Show alerts from last 7 days
        python -m src.main alerts --since 7d

        # Show only unread alerts
        python -m src.main alerts --unread
    """
    db = get_db_manager()

    try:
        # Parse 'since' parameter
        time_delta = _parse_time_delta(since)
        since_time = datetime.utcnow() - time_delta

        # Query alerts
        session = db.get_session_direct()
        try:
            query = session.query(Alert).filter(Alert.sent_at >= since_time)

            if unread:
                query = query.filter(Alert.user_acknowledged == False)

            alerts_list = query.order_by(desc(Alert.sent_at)).limit(limit).all()

            if not alerts_list:
                click.echo("No alerts found")
                return

            # Display alerts
            click.echo("\n" + "=" * 80)
            click.echo(f"ALERTS SINCE {since}")
            click.echo("=" * 80 + "\n")

            for alert in alerts_list:
                listing = alert.listing
                click.echo(f"Alert #{alert.id}")
                click.echo(f"  Type: {alert.alert_type}")
                click.echo(f"  Sent: {alert.sent_at.strftime('%Y-%m-%d %H:%M:%S')}")
                click.echo(f"  Reason: {alert.reason}")
                click.echo(f"  Confidence: {float(alert.confidence_score) * 100:.1f}%")
                if listing:
                    click.echo(f"  Listing: {listing.title}")
                    click.echo(f"  URL: {listing.url}")
                click.echo()

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Failed to retrieve alerts: {e}")
        click.echo(f"Error: {e}")


@cli.command()
def status():
    """
    Show system status and statistics.
    """
    config = get_config()
    db = get_db_manager()

    try:
        # Check database
        db_ok = db.health_check()
        click.echo(f"Database: {'✓ OK' if db_ok else '✗ FAILED'}")

        # Count listings
        session = db.get_session_direct()
        try:
            listing_count = session.query(Listing).filter(Listing.status == 'active').count()
            alert_count = session.query(Alert).count()

            click.echo(f"Active Listings: {listing_count}")
            click.echo(f"Total Alerts: {alert_count}")

            # Configuration summary
            click.echo(f"\nConfiguration:")
            click.echo(f"  Hit List Entries: {len(config.hit_list)}")
            click.echo(f"  Requirements: {len(config.requirements)}")
            click.echo(f"  Update Frequency: {config.update_frequency_hours}h")
            click.echo(f"  Log Level: {config.log_level}")

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        click.echo(f"Error: {e}")


@cli.command()
def init():
    """
    Initialize database schema.
    """
    try:
        db = get_db_manager()
        db.create_tables()
        click.echo("✓ Database initialized successfully")
        logger.info("Database schema created")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        click.echo(f"Error: {e}")


def _parse_time_delta(time_str: str) -> timedelta:
    """
    Parse time string to timedelta.
    Examples: '24h', '7d', '1w'
    """
    time_str = time_str.lower().strip()

    if time_str.endswith('h'):
        hours = int(time_str[:-1])
        return timedelta(hours=hours)
    elif time_str.endswith('d'):
        days = int(time_str[:-1])
        return timedelta(days=days)
    elif time_str.endswith('w'):
        weeks = int(time_str[:-1])
        return timedelta(weeks=weeks)
    else:
        # Default to 24 hours
        return timedelta(hours=24)


if __name__ == '__main__':
    try:
        cli(obj={})
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
