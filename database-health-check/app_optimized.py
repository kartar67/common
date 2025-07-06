#!/usr/bin/env python3
"""
High-Performance Database Health Check Web Application
Optimized for handling 100+ database connections with async processing,
connection pooling, caching, and horizontal scaling capabilities.
"""

import asyncio
import asyncpg
import aioredis
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import psutil
import uvloop

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncpg.pool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set uvloop as the event loop policy for better performance
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

app = FastAPI(title="Database Health Monitor", version="2.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
class Config:
    # Database settings
    DATABASE_URL = "postgresql+asyncpg://user:password@localhost/healthcheck"
    REDIS_URL = "redis://localhost:6379"
    
    # Connection pool settings
    DB_POOL_SIZE = 20
    DB_MAX_OVERFLOW = 50
    DB_POOL_TIMEOUT = 30
    DB_POOL_RECYCLE = 3600
    
    # Performance settings
    MAX_CONCURRENT_CHECKS = 100
    CHECK_INTERVAL = 30
    CACHE_TTL = 60
    BATCH_SIZE = 50
    
    # Monitoring settings
    MAX_HISTORY_DAYS = 30
    ALERT_THRESHOLDS = {
        'response_time': 5.0,
        'cpu_usage': 80.0,
        'memory_usage': 85.0,
        'disk_usage': 90.0
    }

@dataclass
class DatabaseConnection:
    id: str
    name: str
    host: str
    port: int
    database: str
    username: str
    password: str
    connection_type: str  # postgresql, mysql, sqlite
    max_connections: int = 10
    timeout: int = 30

@dataclass
class HealthCheckResult:
    timestamp: str
    database_id: str
    status: str
    response_time: float
    connection_count: int
    active_queries: int
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    error_message: Optional[str] = None

class ConnectionPoolManager:
    """Manages database connection pools for multiple databases"""
    
    def __init__(self):
        self.pools: Dict[str, asyncpg.Pool] = {}
        self.engines: Dict[str, Any] = {}
        
    async def create_pool(self, db_config: DatabaseConnection) -> asyncpg.Pool:
        """Create a connection pool for a database"""
        try:
            if db_config.connection_type == 'postgresql':
                pool = await asyncpg.create_pool(
                    host=db_config.host,
                    port=db_config.port,
                    user=db_config.username,
                    password=db_config.password,
                    database=db_config.database,
                    min_size=5,
                    max_size=db_config.max_connections,
                    command_timeout=db_config.timeout,
                    server_settings={
                        'application_name': 'health_monitor',
                        'tcp_keepalives_idle': '600',
                        'tcp_keepalives_interval': '30',
                        'tcp_keepalives_count': '3',
                    }
                )
                self.pools[db_config.id] = pool
                logger.info(f"Created connection pool for {db_config.name}")
                return pool
            else:
                # For other database types, create SQLAlchemy async engines
                engine = create_async_engine(
                    f"{db_config.connection_type}+asyncpg://{db_config.username}:{db_config.password}@{db_config.host}:{db_config.port}/{db_config.database}",
                    poolclass=QueuePool,
                    pool_size=Config.DB_POOL_SIZE,
                    max_overflow=Config.DB_MAX_OVERFLOW,
                    pool_timeout=Config.DB_POOL_TIMEOUT,
                    pool_recycle=Config.DB_POOL_RECYCLE,
                    echo=False
                )
                self.engines[db_config.id] = engine
                logger.info(f"Created async engine for {db_config.name}")
                return engine
                
        except Exception as e:
            logger.error(f"Failed to create pool for {db_config.name}: {e}")
            raise
    
    async def get_pool(self, database_id: str) -> Union[asyncpg.Pool, Any]:
        """Get connection pool for a database"""
        return self.pools.get(database_id) or self.engines.get(database_id)
    
    async def close_all_pools(self):
        """Close all connection pools"""
        for pool in self.pools.values():
            await pool.close()
        for engine in self.engines.values():
            await engine.dispose()

class CacheManager:
    """Redis-based caching for performance optimization"""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis = await aioredis.from_url(Config.REDIS_URL)
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self.redis = None
    
    async def get(self, key: str) -> Optional[Dict]:
        """Get cached data"""
        if not self.redis:
            return None
        try:
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Dict, ttl: int = Config.CACHE_TTL):
        """Set cached data"""
        if not self.redis:
            return
        try:
            await self.redis.setex(key, ttl, json.dumps(value, default=str))
        except Exception as e:
            logger.error(f"Cache set error: {e}")

class HighPerformanceHealthChecker:
    """Optimized health checker for handling 100+ database connections"""
    
    def __init__(self):
        self.pool_manager = ConnectionPoolManager()
        self.cache_manager = CacheManager()
        self.semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_CHECKS)
        self.executor = ThreadPoolExecutor(max_workers=50)
        self.databases: Dict[str, DatabaseConnection] = {}
        
    async def initialize(self):
        """Initialize the health checker"""
        await self.cache_manager.connect()
        logger.info("Health checker initialized")
    
    async def add_database(self, db_config: DatabaseConnection):
        """Add a database to monitor"""
        self.databases[db_config.id] = db_config
        await self.pool_manager.create_pool(db_config)
    
    async def check_database_health(self, database_id: str) -> HealthCheckResult:
        """Check health of a single database with connection pooling"""
        async with self.semaphore:
            start_time = time.time()
            
            # Check cache first
            cache_key = f"health:{database_id}"
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                return HealthCheckResult(**cached_result)
            
            db_config = self.databases.get(database_id)
            if not db_config:
                raise HTTPException(status_code=404, message=f"Database {database_id} not found")
            
            pool = await self.pool_manager.get_pool(database_id)
            if not pool:
                raise HTTPException(status_code=500, message=f"No pool available for {database_id}")
            
            try:
                # Perform health check using connection pool
                async with pool.acquire() as connection:
                    # Basic connectivity test
                    await connection.fetchval("SELECT 1")
                    
                    # Get connection stats
                    connection_count = len(pool._holders) if hasattr(pool, '_holders') else 0
                    active_queries = await self._get_active_queries(connection)
                    
                response_time = time.time() - start_time
                
                # Get system metrics asynchronously
                system_metrics = await self._get_system_metrics()
                
                # Determine status based on thresholds
                status = self._determine_status(response_time, system_metrics)
                
                result = HealthCheckResult(
                    timestamp=datetime.utcnow().isoformat(),
                    database_id=database_id,
                    status=status,
                    response_time=response_time,
                    connection_count=connection_count,
                    active_queries=active_queries,
                    **system_metrics
                )
                
                # Cache the result
                await self.cache_manager.set(cache_key, asdict(result))
                
                return result
                
            except Exception as e:
                logger.error(f"Health check failed for {database_id}: {e}")
                return HealthCheckResult(
                    timestamp=datetime.utcnow().isoformat(),
                    database_id=database_id,
                    status='critical',
                    response_time=time.time() - start_time,
                    connection_count=0,
                    active_queries=0,
                    cpu_usage=0,
                    memory_usage=0,
                    disk_usage=0,
                    error_message=str(e)
                )
    
    async def check_all_databases(self) -> List[HealthCheckResult]:
        """Check health of all databases concurrently"""
        tasks = [
            self.check_database_health(db_id) 
            for db_id in self.databases.keys()
        ]
        
        # Process in batches to avoid overwhelming the system
        results = []
        for i in range(0, len(tasks), Config.BATCH_SIZE):
            batch = tasks[i:i + Config.BATCH_SIZE]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch check error: {result}")
                else:
                    results.append(result)
        
        return results
    
    async def _get_active_queries(self, connection) -> int:
        """Get number of active queries"""
        try:
            result = await connection.fetchval(
                "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
            )
            return result or 0
        except:
            return 0
    
    async def _get_system_metrics(self) -> Dict[str, float]:
        """Get system metrics asynchronously"""
        loop = asyncio.get_event_loop()
        
        def get_metrics():
            return {
                'cpu_usage': psutil.cpu_percent(interval=0.1),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent
            }
        
        return await loop.run_in_executor(self.executor, get_metrics)
    
    def _determine_status(self, response_time: float, metrics: Dict[str, float]) -> str:
        """Determine overall status based on metrics"""
        thresholds = Config.ALERT_THRESHOLDS
        
        if (response_time > thresholds['response_time'] or
            metrics['cpu_usage'] > thresholds['cpu_usage'] or
            metrics['memory_usage'] > thresholds['memory_usage'] or
            metrics['disk_usage'] > thresholds['disk_usage']):
            return 'critical'
        elif (response_time > thresholds['response_time'] * 0.7 or
              metrics['cpu_usage'] > thresholds['cpu_usage'] * 0.8 or
              metrics['memory_usage'] > thresholds['memory_usage'] * 0.8):
            return 'warning'
        else:
            return 'healthy'

# Global health checker instance
health_checker = HighPerformanceHealthChecker()

@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    await health_checker.initialize()
    
    # Add sample databases (replace with your actual database configurations)
    sample_dbs = [
        DatabaseConnection(
            id="db1",
            name="Production DB",
            host="localhost",
            port=5432,
            database="production",
            username="monitor",
            password="password",
            connection_type="postgresql",
            max_connections=20
        ),
        # Add more databases as needed
    ]
    
    for db in sample_dbs:
        try:
            await health_checker.add_database(db)
        except Exception as e:
            logger.error(f"Failed to add database {db.name}: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await health_checker.pool_manager.close_all_pools()

# API Endpoints
@app.get("/api/health")
async def get_health_status():
    """Get health status of all databases"""
    try:
        results = await health_checker.check_all_databases()
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "databases": [asdict(result) for result in results],
            "summary": {
                "total": len(results),
                "healthy": len([r for r in results if r.status == 'healthy']),
                "warning": len([r for r in results if r.status == 'warning']),
                "critical": len([r for r in results if r.status == 'critical'])
            }
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health/{database_id}")
async def get_database_health(database_id: str):
    """Get health status of a specific database"""
    try:
        result = await health_checker.check_database_health(database_id)
        return {"status": "success", "data": asdict(result)}
    except Exception as e:
        logger.error(f"Database health check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metrics")
async def get_system_metrics():
    """Get system-wide metrics"""
    try:
        metrics = await health_checker._get_system_metrics()
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/databases")
async def add_database(db_config: dict):
    """Add a new database to monitor"""
    try:
        database = DatabaseConnection(**db_config)
        await health_checker.add_database(database)
        return {"status": "success", "message": f"Database {database.name} added successfully"}
    except Exception as e:
        logger.error(f"Add database error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def dashboard():
    """Serve the dashboard"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>High-Performance Database Health Monitor</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .status-healthy { border-left: 4px solid #27ae60; }
            .status-warning { border-left: 4px solid #f39c12; }
            .status-critical { border-left: 4px solid #e74c3c; }
            .metric-value { font-size: 2em; font-weight: bold; margin: 10px 0; }
            .metric-label { color: #666; font-size: 0.9em; }
            .performance-info { background: #3498db; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 High-Performance Database Health Monitor</h1>
                <p>Optimized for 100+ database connections with async processing, connection pooling, and caching</p>
            </div>
            
            <div class="performance-info">
                <h3>🔧 Performance Features</h3>
                <ul>
                    <li>✅ Async/await architecture with FastAPI</li>
                    <li>✅ Connection pooling for all databases</li>
                    <li>✅ Redis caching layer</li>
                    <li>✅ Concurrent health checks (100+ simultaneous)</li>
                    <li>✅ Batch processing and rate limiting</li>
                    <li>✅ uvloop for enhanced performance</li>
                </ul>
            </div>
            
            <div id="metrics" class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Loading health data...</div>
                </div>
            </div>
        </div>
        
        <script>
            async function loadMetrics() {
                try {
                    const response = await fetch('/api/health');
                    const data = await response.json();
                    
                    const metricsDiv = document.getElementById('metrics');
                    metricsDiv.innerHTML = '';
                    
                    if (data.databases) {
                        data.databases.forEach(db => {
                            const card = document.createElement('div');
                            card.className = `metric-card status-${db.status}`;
                            card.innerHTML = `
                                <div class="metric-label">Database: ${db.database_id}</div>
                                <div class="metric-value">${db.status.toUpperCase()}</div>
                                <div class="metric-label">Response Time: ${db.response_time.toFixed(3)}s</div>
                                <div class="metric-label">Connections: ${db.connection_count}</div>
                                <div class="metric-label">Active Queries: ${db.active_queries}</div>
                                <div class="metric-label">CPU: ${db.cpu_usage.toFixed(1)}%</div>
                                <div class="metric-label">Memory: ${db.memory_usage.toFixed(1)}%</div>
                            `;
                            metricsDiv.appendChild(card);
                        });
                    }
                } catch (error) {
                    console.error('Error loading metrics:', error);
                }
            }
            
            // Load metrics on page load and refresh every 30 seconds
            loadMetrics();
            setInterval(loadMetrics, 30000);
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app_optimized:app",
        host="0.0.0.0",
        port=8080,
        workers=4,
        loop="uvloop",
        access_log=True,
        reload=False
    )