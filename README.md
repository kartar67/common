# Database Health Check Web Application

A comprehensive web application for monitoring database health, running performance checks, and generating detailed reports.

## Features

### 🔍 Real-time Health Monitoring
- **Database Connection Status**: Monitor database connectivity and response times
- **System Metrics**: Track CPU usage, memory consumption, and disk space
- **Automatic Health Checks**: Continuous monitoring with configurable intervals
- **Status Indicators**: Visual health status (Healthy, Warning, Critical)

### 📊 Performance Analytics
- **Query Performance Monitoring**: Track execution times and row counts
- **Historical Data**: Store and visualize health check history
- **Interactive Charts**: Real-time charts showing trends and patterns
- **Custom Query Testing**: Run and monitor custom SQL queries

### 📋 Comprehensive Reporting
- **Health Reports**: Generate detailed health summaries
- **Performance Statistics**: Average response times, CPU/memory usage
- **Status Distribution**: Breakdown of health check results
- **Export Functionality**: Download reports in JSON format

### 🛠️ Management Features
- **Start/Stop Monitoring**: Control automatic health checking
- **Custom Query Runner**: Execute and monitor custom SQL queries
- **Real-time Dashboard**: Live updates every 30 seconds
- **Responsive Design**: Works on desktop and mobile devices

## Quick Start

### Prerequisites
- Python 3.7+
- pip package manager

### Installation

1. **Clone or download the application files**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Access the dashboard:**
   - Open your browser and navigate to `http://localhost:8080`
   - The application will automatically start monitoring your database

## Configuration

### Environment Variables

- `DATABASE_PATH`: Path to SQLite database file (default: `/tmp/health_check.db`)
- `CHECK_INTERVAL`: Health check interval in seconds (default: `30`)
- `MAX_HISTORY_DAYS`: Maximum days to keep history (default: `7`)

### Example Configuration
```bash
export DATABASE_PATH="/path/to/your/database.db"
export CHECK_INTERVAL="60"
export MAX_HISTORY_DAYS="30"
python app.py
```

## API Endpoints

### Health Monitoring
- `GET /api/health/current` - Get current health status
- `GET /api/health/history?hours=24` - Get health check history
- `GET /api/monitoring/status` - Get monitoring status
- `POST /api/monitoring/start` - Start continuous monitoring
- `POST /api/monitoring/stop` - Stop continuous monitoring

### Query Management
- `GET /api/queries/history?hours=24` - Get query check history
- `POST /api/queries/run` - Run a custom query check

### Reporting
- `GET /api/report?hours=24` - Generate comprehensive health report

## Dashboard Features

### Main Dashboard
- **Current Health Status**: Real-time database health indicators
- **System Metrics**: CPU, memory, and disk usage monitoring
- **Monitoring Controls**: Start/stop monitoring, refresh data

### Health History Tab
- **Interactive Charts**: Visualize response times and CPU usage over time
- **Historical Data**: View detailed health check history
- **Trend Analysis**: Identify patterns and potential issues

### Query Checks Tab
- **Performance Charts**: Monitor query execution times
- **Query History**: Track all executed queries and their performance
- **Status Monitoring**: Success/warning/error status tracking

### Custom Query Tab
- **SQL Query Runner**: Execute custom queries against the database
- **Performance Measurement**: Automatic timing and row count tracking
- **Result Display**: View query results and performance metrics

### Reports Tab
- **Comprehensive Reports**: Generate detailed health and performance reports
- **Configurable Periods**: Reports for 1 hour to 7 days
- **Export Functionality**: Download reports as JSON files

## Database Schema

The application automatically creates the following tables:

### health_checks
- `id`: Primary key
- `timestamp`: Check timestamp
- `status`: Health status (healthy/warning/critical)
- `response_time`: Database response time
- `connection_count`: Number of active connections
- `cpu_usage`: CPU usage percentage
- `memory_usage`: Memory usage percentage
- `disk_usage`: Disk usage percentage
- `error_message`: Error details (if any)

### query_checks
- `id`: Primary key
- `timestamp`: Query execution timestamp
- `query_name`: Name/description of the query
- `execution_time`: Query execution time
- `rows_affected`: Number of rows affected/returned
- `status`: Query status (success/warning/error)
- `error_message`: Error details (if any)

### sample_data
- `id`: Primary key
- `name`: Sample record name
- `value`: Sample numeric value
- `created_at`: Creation timestamp

## Health Status Criteria

### Healthy ✅
- Response time < 2 seconds
- CPU usage < 80%
- Memory usage < 90%
- No connection errors

### Warning ⚠️
- Response time 2-5 seconds
- CPU usage 80-95%
- Memory usage 90-95%
- Minor performance issues

### Critical ❌
- Response time > 5 seconds
- CPU usage > 95%
- Memory usage > 95%
- Connection failures or major errors

## Monitoring Features

### Automatic Health Checks
- Runs every 30 seconds (configurable)
- Monitors database connectivity
- Tracks system resource usage
- Records all metrics to database

### Predefined Query Checks
- **Count Records**: `SELECT COUNT(*) FROM sample_data`
- **Recent Records**: `SELECT * FROM sample_data ORDER BY created_at DESC LIMIT 5`
- **Average Value**: `SELECT AVG(value) FROM sample_data`

### Custom Query Monitoring
- Execute any SQL query
- Measure execution time
- Track rows affected
- Monitor for errors

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   - Change the port in `app.py` (line 510)
   - Or kill the process using the port

2. **Database Connection Errors**
   - Check database file permissions
   - Verify database path exists
   - Ensure SQLite is properly installed

3. **Permission Errors**
   - Ensure write permissions for database directory
   - Check file system permissions

### Logs and Debugging
- Application logs are printed to console
- Health check errors are stored in the database
- Use browser developer tools for frontend debugging

## Security Considerations

- **Development Server**: This uses Flask's development server - not suitable for production
- **Database Access**: Ensure proper database file permissions
- **Network Access**: Configure firewall rules as needed
- **Input Validation**: Custom queries are executed directly - use with caution

## Extending the Application

### Adding New Database Types
1. Modify the `DatabaseHealthChecker` class
2. Add connection logic for your database type
3. Update health check queries as needed

### Custom Metrics
1. Add new fields to the `HealthCheckResult` dataclass
2. Update the database schema
3. Modify the health check logic

### Additional Visualizations
1. Add new Chart.js charts to the frontend
2. Create new API endpoints for data
3. Update the dashboard HTML/CSS

## License

This application is provided as-is for educational and development purposes.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review application logs
3. Verify configuration settings
4. Test API endpoints directly