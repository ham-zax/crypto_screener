"""
Data Fetching Service for Project Omega V2

Orchestrates API calls to fetch and process cryptocurrency data from CoinGecko.
Filters projects by market cap and volume criteria, applies automated scoring,
and transforms data to match AutomatedProject model format.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import time

from .coingecko import CoinGeckoClient, APIError, RateLimitError
from ..models.api_responses import (
    CoinGeckoMarket, 
    CoinGeckoCoinDetails, 
    APIResponseValidator
)
from ..scoring.automated_scoring import AutomatedScoringEngine, ScoringValidator

logger = logging.getLogger(__name__)


class DataFetchingService:
    # Celery task callback for progress updates
    @staticmethod
    def update_task_progress(task_id: str, current: int, total: int, status: str):
        """
        Update Celery task progress
        
        Args:
            task_id: Celery task ID
            current: Current progress count
            total: Total items to process
            status: Status message
        """
        try:
            # Use Celery's AsyncResult to update task state directly
            from celery import current_app
            from celery.result import AsyncResult
            
            # Create an AsyncResult for the task
            task = AsyncResult(task_id, app=current_app)
            
            # Update task state directly if backend is available
            if task.backend:
                task.backend.store_result(
                    task_id,
                    {
                        'current': current,
                        'total': total,
                        'status': status,
                        'percentage': round((current / max(total, 1)) * 100, 1)
                    },
                    'PROGRESS'
                )
            else:
                logger.debug(f"Task backend unavailable for {task_id}")
        except Exception as e:
            logger.debug(f"Failed to update task progress: {e}")
    """
    Service class to orchestrate cryptocurrency data fetching and processing
    
    Features:
    - Fetch market data with filtering criteria
    - Apply automated scoring algorithms  
    - Transform data to AutomatedProject format
    - Handle pagination for large datasets
    - Comprehensive error handling and retry logic
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize data fetching service
        
        Args:
            api_key: Optional CoinGecko Pro API key
        """
        self.client = CoinGeckoClient(api_key=api_key)
        self.scoring_engine = AutomatedScoringEngine()
        self.validator = APIResponseValidator()
        
        # Default filtering criteria
        self.default_filters = {
            'min_market_cap': 1_000_000,      # $1M minimum
            'max_market_cap': None,           # No maximum
            'min_volume_24h': 100_000,        # $100K minimum daily volume
            'max_results': 1000               # Limit to top 1000 projects
        }
        
        logger.info("Data fetching service initialized")
    
    def fetch_projects_bulk(
        self,
        filters: Optional[Dict[str, Any]] = None,
        include_detailed_data: bool = False,
        task_id: Optional[str] = None,
        batch_size: int = 100
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Fetch and process bulk cryptocurrency projects with Celery integration
        
        Args:
            filters: Filtering criteria (market cap, volume, etc.)
            include_detailed_data: Whether to fetch detailed coin data
            task_id: Celery task ID for progress updates
            batch_size: Number of projects to process per batch
            
        Returns:
            Tuple of (processed_projects, fetch_metadata)
        """
        # Merge filters with defaults
        active_filters = {**self.default_filters, **(filters or {})}
        
        logger.info(f"Starting bulk project fetch with filters: {active_filters}")
        start_time = time.time()
        
        try:
            # Step 1: Fetch market data
            logger.info("Fetching market data from CoinGecko...")
            if task_id:
                DataFetchingService.update_task_progress(task_id, 0, 100, "Fetching market data...")
            
            raw_markets = self._fetch_filtered_markets(active_filters)
            
            if not raw_markets:
                logger.warning("No market data retrieved")
                return [], self._create_fetch_metadata(start_time, 0, 0, "No data retrieved")
            
            logger.info(f"Retrieved {len(raw_markets)} market entries")
            
            # Step 2: Validate and filter market data
            logger.info("Validating market data...")
            if task_id:
                DataFetchingService.update_task_progress(task_id, 10, 100, "Validating market data...")
            
            validated_markets = self.validator.validate_markets_response(raw_markets)
            
            # Apply additional filters
            filtered_markets = self._apply_additional_filters(validated_markets, active_filters)
            
            logger.info(f"After validation and filtering: {len(filtered_markets)} projects")
            
            # Step 3: Process projects with scoring in batches
            logger.info("Processing projects with automated scoring...")
            if task_id:
                DataFetchingService.update_task_progress(task_id, 20, 100, "Processing projects...")
            
            processed_projects = []
            errors = []
            total_projects = len(filtered_markets)
            
            # Process in batches for better performance and progress tracking
            for batch_start in range(0, total_projects, batch_size):
                batch_end = min(batch_start + batch_size, total_projects)
                batch = filtered_markets[batch_start:batch_end]
                
                logger.info(f"--- Starting batch {batch_start//batch_size + 1}/{(total_projects-1)//batch_size + 1} ---")
                logger.info(f"Batch range: projects {batch_start + 1}-{batch_end}")

                # Update progress
                progress_percent = 20 + int((batch_start / total_projects) * 70)
                if task_id:
                    DataFetchingService.update_task_progress(
                        task_id,
                        progress_percent,
                        100,
                        f"Processing batch {batch_start//batch_size + 1}/{(total_projects-1)//batch_size + 1}..."
                    )
                
                # Process batch
                batch_processed, batch_errors = self._process_project_batch(
                    batch, include_detailed_data, task_id
                )
                
                logger.info(f"Batch {batch_start//batch_size + 1} processed: {len(batch_processed)} projects, {len(batch_errors)} errors")
                if batch_errors:
                    for err in batch_errors:
                        logger.error(f"Batch error: {err}")

                processed_projects.extend(batch_processed)
                errors.extend(batch_errors)
                
                # Rate limiting between batches
                if batch_end < total_projects:
                    logger.debug(f"Sleeping for 0.5s between batches")
                    time.sleep(0.5)  # Brief pause between batches
            
            # Final progress update
            if task_id:
                DataFetchingService.update_task_progress(task_id, 95, 100, "Finalizing results...")
            
            fetch_metadata = self._create_fetch_metadata(
                start_time,
                len(processed_projects),
                len(errors),
                f"Successfully processed {len(processed_projects)} projects"
            )
            
            if errors:
                fetch_metadata['processing_errors'] = errors[:10]  # Limit error list
                fetch_metadata['total_errors'] = len(errors)
            
            fetch_metadata['batch_size'] = batch_size
            fetch_metadata['total_batches'] = (total_projects - 1) // batch_size + 1
            
            logger.info(f"Bulk fetch completed: {len(processed_projects)} projects processed "
                       f"in {time.time() - start_time:.1f}s")
            
            return processed_projects, fetch_metadata
            
        except Exception as e:
            error_msg = f"Bulk fetch failed: {e}"
            logger.error(error_msg)
            fetch_metadata = self._create_fetch_metadata(start_time, 0, 1, error_msg)
            return [], fetch_metadata
    
    def fetch_single_project(
        self,
        coingecko_id: str,
        include_detailed_data: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch and process a single cryptocurrency project
        
        Args:
            coingecko_id: CoinGecko identifier for the project
            include_detailed_data: Whether to fetch detailed coin data
            
        Returns:
            Processed project data or None if failed
        """
        logger.info(f"Fetching single project: {coingecko_id}")
        
        try:
            # Fetch coin data directly from CoinGecko
            raw_details_with_market = self.client.get_coin_data(
                coingecko_id,
                market_data=True
            )
            if not raw_details_with_market:
                logger.warning(f"Project {coingecko_id} not found in coin data")
                return None

            market_data_from_details = raw_details_with_market.get('market_data', {})
            market_data_for_model = {
                'id': raw_details_with_market.get('id'),
                'symbol': raw_details_with_market.get('symbol'),
                'name': raw_details_with_market.get('name'),
                'current_price': market_data_from_details.get('current_price', {}).get('usd'),
                'market_cap': market_data_from_details.get('market_cap', {}).get('usd'),
                'circulating_supply': market_data_from_details.get('circulating_supply'),
                'total_supply': market_data_from_details.get('total_supply'),
                # ... add any other required fields from the 'market_data' sub-object
            }
            target_market = CoinGeckoMarket.from_coingecko_response(market_data_for_model)
            coin_details = CoinGeckoCoinDetails.from_coingecko_response(raw_details_with_market) if include_detailed_data else None

            # Validate market data
            if not ScoringValidator.validate_market_data_for_scoring(target_market):
                logger.warning(f"Project {coingecko_id} failed validation")
                return None

            # Process and return
            project_data = self._process_project(target_market, coin_details)
            logger.info(f"Successfully processed single project: {coingecko_id}")
            return project_data

        except Exception as e:
            logger.error(f"Failed to fetch single project {coingecko_id}: {e}")
            return None
    
    def refresh_project_data(
        self, 
        coingecko_ids: List[str]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Refresh data for specific projects
        
        Args:
            coingecko_ids: List of CoinGecko IDs to refresh
            
        Returns:
            Tuple of (updated_projects, failed_ids)
        """
        logger.info(f"Refreshing data for {len(coingecko_ids)} projects")
        
        updated_projects = []
        failed_ids = []
        
        for coingecko_id in coingecko_ids:
            try:
                project_data = self.fetch_single_project(coingecko_id, include_detailed_data=True)
                if project_data:
                    updated_projects.append(project_data)
                else:
                    failed_ids.append(coingecko_id)
            except Exception as e:
                logger.error(f"Failed to refresh {coingecko_id}: {e}")
                failed_ids.append(coingecko_id)
        
        logger.info(f"Refresh completed: {len(updated_projects)} successful, {len(failed_ids)} failed")
        return updated_projects, failed_ids
    
    def _fetch_filtered_markets(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch market data with initial filtering
        
        Args:
            filters: Filtering criteria
            
        Returns:
            List of raw market data dictionaries
        """
        max_results = filters.get('max_results', 1000)
        min_market_cap = filters.get('min_market_cap')
        
        # Fetch bulk market data
        raw_markets = self.client.get_markets_data_bulk(
            vs_currency="usd",
            max_results=max_results,
            min_market_cap=min_market_cap,
            order="market_cap_desc"
        )
        
        return raw_markets
    
    def _apply_additional_filters(
        self, 
        markets: List[CoinGeckoMarket], 
        filters: Dict[str, Any]
    ) -> List[CoinGeckoMarket]:
        """
        Apply additional filtering criteria to validated markets
        
        Args:
            markets: List of validated CoinGeckoMarket instances
            filters: Filtering criteria
            
        Returns:
            Filtered list of markets
        """
        filtered = markets
        
        # Apply market cap filters
        min_market_cap = filters.get('min_market_cap')
        max_market_cap = filters.get('max_market_cap')
        
        if min_market_cap or max_market_cap:
            filtered = self.validator.filter_by_market_cap(
                filtered, min_market_cap, max_market_cap
            )
        
        # Apply volume filters
        min_volume = filters.get('min_volume_24h')
        if min_volume:
            filtered = self.validator.filter_by_volume(filtered, min_volume)
        
        # Apply max results limit
        max_results = filters.get('max_results', len(filtered))
        filtered = filtered[:max_results]
        
        return filtered
    
    def _process_project_batch(
        self,
        markets_batch: List[CoinGeckoMarket],
        include_detailed_data: bool,
        task_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Process a batch of projects with error handling
        
        Args:
            markets_batch: Batch of market data to process
            include_detailed_data: Whether to fetch detailed data
            task_id: Celery task ID for progress updates
            
        Returns:
            Tuple of (processed_projects, errors)
        """
        processed_projects = []
        errors = []
        
        for i, market in enumerate(markets_batch):
            try:
                logger.info(f"Processing project {i+1}/{len(markets_batch)}: {market.id}")
                # Optionally fetch detailed data
                coin_details = None
                if include_detailed_data:
                    try:
                        coin_details = self._fetch_coin_details(market.id)
                        logger.debug(f"Fetched details for {market.id}")
                    except Exception as e:
                        logger.warning(f"Failed to fetch details for {market.id}: {e}")
                
                # Process and score the project
                project_data = self._process_project(market, coin_details)
                logger.info(f"Project processed: {market.id}")
                processed_projects.append(project_data)
                
                # Brief pause to respect rate limits
                if i > 0 and i % 10 == 0:
                    logger.debug(f"Sleeping for 0.1s after processing 10 projects")
                    time.sleep(0.1)
            
            except Exception as e:
                error_msg = f"Failed to process {market.id}: {e}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
                continue
        
        logger.info(f"Batch completed: {len(processed_projects)} projects, {len(errors)} errors")
        return processed_projects, errors
    
    def _fetch_coin_details(self, coingecko_id: str) -> Optional[CoinGeckoCoinDetails]:
        """
        Fetch detailed coin information
        
        Args:
            coingecko_id: CoinGecko identifier
            
        Returns:
            CoinGeckoCoinDetails instance or None if failed
        """
        try:
            raw_details = self.client.get_coin_data(coingecko_id)
            return self.validator.validate_coin_details_response(raw_details)
        except Exception as e:
            logger.warning(f"Failed to fetch coin details for {coingecko_id}: {e}")
            return None
    
    def _process_project(
        self, 
        market: CoinGeckoMarket, 
        coin_details: Optional[CoinGeckoCoinDetails] = None
    ) -> Dict[str, Any]:
        """
        Process a project with automated scoring
        
        Args:
            market: CoinGeckoMarket instance
            coin_details: Optional detailed coin information
            
        Returns:
            Dictionary with processed project data
        """
        # Start with base project data
        logger.debug(f"Transforming market data for {market.id}")
        project_data = market.to_automated_project_dict()
        
        # Add category from details if available
        if coin_details:
            project_data['category'] = coin_details.get_primary_category()
            logger.debug(f"Category set for {market.id}: {project_data['category']}")
        
        # Calculate automated scores
        scores = self.scoring_engine.calculate_all_automated_scores(market, coin_details)
        logger.debug(f"Scores calculated for {market.id}: {scores}")
        
        # Validate scores
        if not ScoringValidator.validate_scoring_results(scores):
            logger.warning(f"Invalid scores calculated for {market.id}")
        
        # Merge scores into project data
        project_data.update(scores)
        
        # Add timestamps
        project_data['last_updated'] = datetime.utcnow()
        project_data['created_at'] = datetime.utcnow()
        
        logger.info(f"Project data finalized for {market.id}")
        return project_data
    
    def _create_fetch_metadata(
        self, 
        start_time: float, 
        success_count: int, 
        error_count: int, 
        status_message: str
    ) -> Dict[str, Any]:
        """
        Create metadata about the fetch operation
        
        Args:
            start_time: Operation start timestamp
            success_count: Number of successful operations
            error_count: Number of failed operations
            status_message: Overall status description
            
        Returns:
            Fetch metadata dictionary
        """
        duration = time.time() - start_time
        
        return {
            'fetched_at': datetime.utcnow().isoformat(),
            'duration_seconds': round(duration, 2),
            'success_count': success_count,
            'error_count': error_count,
            'total_processed': success_count + error_count,
            'success_rate': round(success_count / max(success_count + error_count, 1) * 100, 1),
            'status': 'success' if error_count == 0 else 'partial' if success_count > 0 else 'failed',
            'message': status_message,
            'api_cache_stats': self.client.get_cache_stats()
        }
    
    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get service statistics and status
        
        Returns:
            Service statistics dictionary
        """
        return {
            'service_status': 'active',
            'api_client_stats': self.client.get_cache_stats(),
            'default_filters': self.default_filters,
            'rate_limit_info': {
                'calls_per_minute': self.client.calls_per_minute,
                'recent_calls': len(self.client.call_timestamps)
            }
        }
    
    def clear_cache(self):
        """Clear API client cache"""
        self.client.clear_cache()
        logger.info("Data fetching service cache cleared")


class ProjectIngestionManager:
    """
    High-level manager for project ingestion workflows
    
    Handles scheduled ingestion, data refresh cycles, and error recovery
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize ingestion manager
        
        Args:
            api_key: Optional CoinGecko Pro API key
        """
        self.fetcher = DataFetchingService(api_key=api_key)
        self.last_ingestion = None
        self.ingestion_history = []
        
        logger.info("Project ingestion manager initialized")
    
    def run_full_ingestion(
        self,
        filters: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Run a complete project ingestion cycle with Celery integration
        
        Args:
            filters: Custom filtering criteria
            task_id: Celery task ID for progress updates
            batch_size: Batch size for processing
            
        Returns:
            Ingestion results and metadata
        """
        logger.info("Starting full project ingestion")
        start_time = time.time()
        
        try:
            # Perform bulk fetch with Celery integration
            projects, metadata = self.fetcher.fetch_projects_bulk(
                filters=filters,
                include_detailed_data=True,
                task_id=task_id,
                batch_size=batch_size
            )
            
            # Record ingestion
            ingestion_record = {
                'timestamp': datetime.utcnow(),
                'projects_count': len(projects),
                'duration': time.time() - start_time,
                'status': metadata['status'],
                'metadata': metadata,
                'batch_size': batch_size,
                'task_id': task_id
            }
            
            self.last_ingestion = ingestion_record
            self.ingestion_history.append(ingestion_record)
            
            # Keep only last 10 ingestion records
            if len(self.ingestion_history) > 10:
                self.ingestion_history = self.ingestion_history[-10:]
            
            logger.info(f"Full ingestion completed: {len(projects)} projects in {time.time() - start_time:.1f}s")
            
            return {
                'projects': projects,
                'ingestion_record': ingestion_record
            }
            
        except Exception as e:
            error_msg = f"Full ingestion failed: {e}"
            logger.error(error_msg)
            
            error_record = {
                'timestamp': datetime.utcnow(),
                'projects_count': 0,
                'duration': time.time() - start_time,
                'status': 'failed',
                'error': error_msg,
                'task_id': task_id
            }
            
            self.last_ingestion = error_record
            self.ingestion_history.append(error_record)
            
            return {
                'projects': [],
                'ingestion_record': error_record
            }
    
    def get_ingestion_status(self) -> Dict[str, Any]:
        """
        Get current ingestion status and history
        
        Returns:
            Ingestion status information
        """
        return {
            'last_ingestion': self.last_ingestion,
            'ingestion_history': self.ingestion_history,
            'service_stats': self.fetcher.get_service_stats()
        }