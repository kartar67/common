#!/usr/bin/env python3
"""
Database Health Check Web Application
A comprehensive tool for monitoring database health, running query checks, and generating reports.
"""

import os
import time
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import json
import psutil

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Configuration
DATABASE_PATH = os.getenv('DATABASE_PATH', '/tmp/health_check.db')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '30'))  # seconds
MAX_HISTORY_DAYS = int(os.getenv('MAX_HISTORY_DAYS', '7'))

@dataclass
class HealthCheckResult:
    timestamp: str
    status: str  # 'healthy', 'warning', 'critical'
    response_time: float
    connection_count: int
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    error_message: Optional[str] = None

@dataclass
class QueryCheckResult:
    timestamp: str
    query_name: str
    execution_time: float
    rows_affected: int
    status: str  # 'success', 'warning', 'error'
    error_message: Optional[str] = None

class DatabaseHealthChecker:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.health_history: List[HealthCheckResult] = []
        self.query_history: List[QueryCheckResult] = []
        self.is_monitoring = False
        self.monitor_thread = None
        self.init_database()
        
    def init_database(self):
        """Initialize the database with required tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create health checks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS health_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_time REAL NOT NULL,
                    connection_count INTEGER NOT NULL,
                    cpu_usage REAL NOT NULL,
                    memory_usage REAL NOT NULL,
                    disk_usage REAL NOT NULL,
                    error_message TEXT
                )
            ''')
            
            # Create query checks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS query_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    query_name TEXT NOT NULL,
                    execution_time REAL NOT NULL,
                    rows_affected INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT
                )
            ''')
            
            # Create sample data table for testing
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sample_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    value INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # Insert some sample data if table is empty
            cursor.execute('SELECT COUNT(*) FROM sample_data')
            if cursor.fetchone()[0] == 0:
                sample_data = [
                    ('Test Record 1', 100, datetime.now().isoformat()),
                    ('Test Record 2', 200, datetime.now().isoformat()),
                    ('Test Record 3', 300, datetime.now().isoformat()),
                ]
                cursor.executemany(
                    'INSERT INTO sample_data (name, value, created_at) VALUES (?, ?, ?)',
                    sample_data
                )
            
            conn.commit()
            conn.close()
            print(f"Database initialized at {self.db_path}")
            
        except Exception as e:
            print(f"Error initializing database: {e}")
    
    def check_database_health(self) -> HealthCheckResult:
        """Perform a comprehensive health check of the database"""
        start_time = time.time()
        
        try:
            # Test database connection
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            cursor = conn.cursor()
            
            # Simple query to test responsiveness
            cursor.execute('SELECT 1')
            cursor.fetchone()
            
            # Count connections (for SQLite, this is always 1)
            connection_count = 1
            
            # Get system metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            response_time = time.time() - start_time
            
            # Determine status based on metrics
            status = 'healthy'
            if response_time > 2.0 or cpu_usage > 80 or memory.percent > 90:
                status = 'warning'
            if response_time > 5.0 or cpu_usage > 95 or memory.percent > 95:
                status = 'critical'
            
            result = HealthCheckResult(
                timestamp=datetime.now().isoformat(),
                status=status,
                response_time=response_time,
                connection_count=connection_count,
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=disk.percent
            )
            
            conn.close()
            return result
            
        except Exception as e:
            return HealthCheckResult(
                timestamp=datetime.now().isoformat(),
                status='critical',
                response_time=time.time() - start_time,
                connection_count=0,
                cpu_usage=0,
                memory_usage=0,
                disk_usage=0,
                error_message=str(e)
            )
    
    def run_query_check(self, query_name: str, query: str) -> QueryCheckResult:
        """Run a specific query and measure its performance"""
        start_time = time.time()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(query)
            rows_affected = cursor.rowcount
            
            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                rows_affected = len(results)
            
            execution_time = time.time() - start_time
            
            # Determine status based on execution time
            status = 'success'
            if execution_time > 1.0:
                status = 'warning'
            if execution_time > 5.0:
                status = 'error'
            
            result = QueryCheckResult(
                timestamp=datetime.now().isoformat(),
                query_name=query_name,
                execution_time=execution_time,
                rows_affected=rows_affected,
                status=status
            )
            
            conn.commit()
            conn.close()
            return result
            
        except Exception as e:
            return QueryCheckResult(
                timestamp=datetime.now().isoformat(),
                query_name=query_name,
                execution_time=time.time() - start_time,
                rows_affected=0,
                status='error',
                error_message=str(e)
            )
    
    def save_health_check(self, result: HealthCheckResult):
        """Save health check result to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO health_checks 
                (timestamp, status, response_time, connection_count, cpu_usage, memory_usage, disk_usage, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.timestamp, result.status, result.response_time,
                result.connection_count, result.cpu_usage, result.memory_usage,
                result.disk_usage, result.error_message
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error saving health check: {e}")
    
    def save_query_check(self, result: QueryCheckResult):
        """Save query check result to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO query_checks 
                (timestamp, query_name, execution_time, rows_affected, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                result.timestamp, result.query_name, result.execution_time,
                result.rows_affected, result.status, result.error_message
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error saving query check: {e}")
    
    def get_health_history(self, hours: int = 24) -> List[Dict]:
        """Get health check history for the specified number of hours"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            cursor.execute('''
                SELECT timestamp, status, response_time, connection_count, 
                       cpu_usage, memory_usage, disk_usage, error_message
                FROM health_checks 
                WHERE timestamp > ? 
                ORDER BY timestamp DESC
            ''', (since,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'timestamp': row[0],
                    'status': row[1],
                    'response_time': row[2],
                    'connection_count': row[3],
                    'cpu_usage': row[4],
                    'memory_usage': row[5],
                    'disk_usage': row[6],
                    'error_message': row[7]
                })
            
            conn.close()
            return results
            
        except Exception as e:
            print(f"Error getting health history: {e}")
            return []
    
    def get_query_history(self, hours: int = 24) -> List[Dict]:
        """Get query check history for the specified number of hours"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            cursor.execute('''
                SELECT timestamp, query_name, execution_time, rows_affected, status, error_message
                FROM query_checks 
                WHERE timestamp > ? 
                ORDER BY timestamp DESC
            ''', (since,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'timestamp': row[0],
                    'query_name': row[1],
                    'execution_time': row[2],
                    'rows_affected': row[3],
                    'status': row[4],
                    'error_message': row[5]
                })
            
            conn.close()
            return results
            
        except Exception as e:
            print(f"Error getting query history: {e}")
            return []
    
    def start_monitoring(self):
        """Start continuous health monitoring"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("Health monitoring started")
    
    def stop_monitoring(self):
        """Stop continuous health monitoring"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("Health monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Run health check
                health_result = self.check_database_health()
                self.save_health_check(health_result)
                self.health_history.append(health_result)
                
                # Keep only recent history in memory
                cutoff = datetime.now() - timedelta(hours=1)
                self.health_history = [
                    h for h in self.health_history 
                    if datetime.fromisoformat(h.timestamp) > cutoff
                ]
                
                # Run predefined query checks
                predefined_queries = [
                    ("Count Records", "SELECT COUNT(*) FROM sample_data"),
                    ("Recent Records", "SELECT * FROM sample_data ORDER BY created_at DESC LIMIT 5"),
                    ("Average Value", "SELECT AVG(value) FROM sample_data"),
                ]
                
                for query_name, query in predefined_queries:
                    query_result = self.run_query_check(query_name, query)
                    self.save_query_check(query_result)
                    self.query_history.append(query_result)
                
                # Keep only recent query history in memory
                self.query_history = [
                    q for q in self.query_history 
                    if datetime.fromisoformat(q.timestamp) > cutoff
                ]
                
                time.sleep(CHECK_INTERVAL)
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(CHECK_INTERVAL)

# Initialize the health checker
health_checker = DatabaseHealthChecker()

# Routes
@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/health/current')
def get_current_health():
    """Get current health status"""
    result = health_checker.check_database_health()
    return jsonify(asdict(result))

@app.route('/api/health/history')
def get_health_history():
    """Get health check history"""
    hours = request.args.get('hours', 24, type=int)
    history = health_checker.get_health_history(hours)
    return jsonify(history)

@app.route('/api/queries/history')
def get_query_history():
    """Get query check history"""
    hours = request.args.get('hours', 24, type=int)
    history = health_checker.get_query_history(hours)
    return jsonify(history)

@app.route('/api/queries/run', methods=['POST'])
def run_custom_query():
    """Run a custom query check"""
    data = request.get_json()
    query_name = data.get('name', 'Custom Query')
    query = data.get('query', '')
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    result = health_checker.run_query_check(query_name, query)
    health_checker.save_query_check(result)
    
    return jsonify(asdict(result))

@app.route('/api/monitoring/start', methods=['POST'])
def start_monitoring():
    """Start continuous monitoring"""
    health_checker.start_monitoring()
    return jsonify({'status': 'started'})

@app.route('/api/monitoring/stop', methods=['POST'])
def stop_monitoring():
    """Stop continuous monitoring"""
    health_checker.stop_monitoring()
    return jsonify({'status': 'stopped'})

@app.route('/api/monitoring/status')
def get_monitoring_status():
    """Get monitoring status"""
    return jsonify({'is_monitoring': health_checker.is_monitoring})

@app.route('/api/report')
def generate_report():
    """Generate a comprehensive health report"""
    hours = request.args.get('hours', 24, type=int)
    
    health_history = health_checker.get_health_history(hours)
    query_history = health_checker.get_query_history(hours)
    
    # Calculate statistics
    if health_history:
        avg_response_time = sum(h['response_time'] for h in health_history) / len(health_history)
        avg_cpu = sum(h['cpu_usage'] for h in health_history) / len(health_history)
        avg_memory = sum(h['memory_usage'] for h in health_history) / len(health_history)
        
        status_counts = {}
        for h in health_history:
            status_counts[h['status']] = status_counts.get(h['status'], 0) + 1
    else:
        avg_response_time = avg_cpu = avg_memory = 0
        status_counts = {}
    
    if query_history:
        avg_query_time = sum(q['execution_time'] for q in query_history) / len(query_history)
        query_status_counts = {}
        for q in query_history:
            query_status_counts[q['status']] = query_status_counts.get(q['status'], 0) + 1
    else:
        avg_query_time = 0
        query_status_counts = {}
    
    report = {
        'generated_at': datetime.now().isoformat(),
        'period_hours': hours,
        'health_summary': {
            'total_checks': len(health_history),
            'avg_response_time': round(avg_response_time, 3),
            'avg_cpu_usage': round(avg_cpu, 2),
            'avg_memory_usage': round(avg_memory, 2),
            'status_distribution': status_counts
        },
        'query_summary': {
            'total_queries': len(query_history),
            'avg_execution_time': round(avg_query_time, 3),
            'status_distribution': query_status_counts
        },
        'recent_health_checks': health_history[:10],
        'recent_query_checks': query_history[:10]
    }
    
    return jsonify(report)

if __name__ == '__main__':
    # Start monitoring by default
    health_checker.start_monitoring()
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=12000,
        debug=False,
        threaded=True
    )