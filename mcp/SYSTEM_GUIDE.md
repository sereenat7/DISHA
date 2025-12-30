# 🚀 Agentic Disaster Response System - Complete Guide

This guide shows you how to run and test the complete MCP server system.

## 📋 System Overview

The system consists of:

1. **FastAPI Backend** - Evacuation system with disaster response integration
2. **Disaster Response Agent** - Autonomous agent for processing disasters
3. **MCP Tools** - Model Context Protocol tools for alert dispatch
4. **Context Builder** - Enriches disaster data with geographical context
5. **Alert Prioritizer** - Analyzes and prioritizes disaster alerts

## 🚀 Quick Start

### 1. Start the FastAPI Server

The FastAPI server is already running on `http://127.0.0.1:8000`

You can verify it's running by visiting:

- **API Documentation**: http://127.0.0.1:8000/docs
- **System Health**: http://127.0.0.1:8000/system/health

### 2. Test the System

Run the comprehensive test:

```bash
python test_system.py
```

Or use the startup script:

```bash
python run_system.py
```

## 🔧 Available Endpoints

### Core Endpoints

1. **Trigger Disaster Event**

   ```bash
   curl -X POST "http://127.0.0.1:8000/disaster/trigger" \
     -H "Content-Type: application/json" \
     -d '{
       "disaster_type": "fire",
       "location_lat": 52.5200,
       "location_lon": 13.4050,
       "severity": "high",
       "affected_radius_km": 5.0,
       "description": "Test fire disaster",
       "estimated_affected_population": 2000
     }'
   ```

2. **Get Disaster Status**

   ```bash
   curl -X GET "http://127.0.0.1:8000/disaster/{disaster_id}/status"
   ```

3. **System Health Check**

   ```bash
   curl -X GET "http://127.0.0.1:8000/system/health"
   ```

4. **System Status**

   ```bash
   curl -X GET "http://127.0.0.1:8000/system/status"
   ```

5. **Evacuation Routes** (Original functionality)
   ```bash
   curl -X POST "http://127.0.0.1:8000/evacuation-routes" \
     -H "Content-Type: application/json" \
     -d '{
       "user_lat": 52.5200,
       "user_lon": 13.4050,
       "radius_km": 10.0,
       "max_per_category": 3
     }'
   ```

## 🧪 Testing Scenarios

### Scenario 1: Basic Disaster Processing

```bash
# Trigger a fire disaster
curl -X POST "http://127.0.0.1:8000/disaster/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "disaster_type": "fire",
    "location_lat": 52.5200,
    "location_lon": 13.4050,
    "severity": "high",
    "affected_radius_km": 5.0,
    "description": "Building fire in Berlin",
    "estimated_affected_population": 1500
  }'
```

### Scenario 2: Multiple Disaster Types

```bash
# Flood disaster
curl -X POST "http://127.0.0.1:8000/disaster/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "disaster_type": "flood",
    "location_lat": 48.8566,
    "location_lon": 2.3522,
    "severity": "critical",
    "affected_radius_km": 10.0,
    "description": "Severe flooding in Paris",
    "estimated_affected_population": 5000
  }'

# Earthquake disaster
curl -X POST "http://127.0.0.1:8000/disaster/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "disaster_type": "earthquake",
    "location_lat": 35.6762,
    "location_lon": 139.6503,
    "severity": "critical",
    "affected_radius_km": 20.0,
    "description": "Major earthquake in Tokyo",
    "estimated_affected_population": 10000
  }'
```

### Scenario 3: System Monitoring

```bash
# Check system health
curl -X GET "http://127.0.0.1:8000/system/health" | python -m json.tool

# Get detailed system status
curl -X GET "http://127.0.0.1:8000/system/status" | python -m json.tool
```

## 🔍 Understanding the Response

### Disaster Trigger Response

```json
{
  "disaster_id": "disaster_20251230_164815_abc123",
  "status": "processing",
  "message": "Disaster event triggered successfully",
  "processing_started_at": "2025-12-30T16:48:15.123456",
  "estimated_completion_time": "2025-12-30T16:48:45.123456"
}
```

### System Health Response

```json
{
  "timestamp": "2025-12-30T16:48:15.623692",
  "evacuation_system": "healthy",
  "disaster_response_agent": "healthy"
}
```

## 🛠️ MCP Tools Integration

The system includes these MCP tools:

1. **Alert Tool** (`alert_tool.py`)

   - Handles emergency notifications
   - Dispatches alerts to multiple channels
   - Supports fallback mechanisms

2. **Routing Tool** (`routing_tool.py`)

   - Manages evacuation route information
   - Integrates with OSRM routing service
   - Provides real-time route updates

3. **Context Tool** (`context_tool.py`)

   - Provides situational awareness data
   - Enriches disaster context
   - Supports geographical analysis

4. **Backup Tools** (`backup_tools.py`)
   - Fallback mechanisms for reliability
   - Alternative alert channels
   - Redundant routing services

## 📊 System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI       │    │  Disaster        │    │   MCP Tools     │
│   Backend       │◄──►│  Response Agent  │◄──►│   Registry      │
│   (Port 8000)   │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       │
         │              ┌──────────────────┐             │
         │              │  Context Builder │             │
         │              └──────────────────┘             │
         │                       │                       │
         │                       ▼                       │
         │              ┌──────────────────┐             │
         │              │ Alert Prioritizer│             │
         │              └──────────────────┘             │
         │                       │                       │
         │                       ▼                       │
         └──────────────►┌──────────────────┐◄───────────┘
                         │ Alert Dispatcher │
                         └──────────────────┘
```

## 🚨 Troubleshooting

### Common Issues

1. **"Disaster Response Agent is not available"**

   - The agent failed to initialize properly
   - Check the server logs for import errors
   - Ensure all dependencies are installed

2. **"No disaster data found for ID"**

   - The disaster ID doesn't exist in the system
   - Use the correct disaster ID from the trigger response

3. **Connection errors**
   - Ensure the FastAPI server is running on port 8000
   - Check firewall settings
   - Verify network connectivity

### Debug Commands

```bash
# Check server logs
curl -X GET "http://127.0.0.1:8000/system/status"

# Test basic connectivity
curl -X GET "http://127.0.0.1:8000/"

# Validate API schema
curl -X GET "http://127.0.0.1:8000/openapi.json"
```

## 🎯 Next Steps

1. **Production Deployment**

   - Configure proper database storage
   - Set up monitoring and alerting
   - Implement authentication and authorization

2. **MCP Integration**

   - Connect to real alert systems
   - Integrate with emergency services
   - Add more MCP tool providers

3. **Scaling**
   - Add load balancing
   - Implement message queues
   - Set up distributed processing

## 📝 Logs and Monitoring

The system provides comprehensive logging:

- **Workflow logs**: Track disaster processing steps
- **Error logs**: Capture and handle failures
- **Performance logs**: Monitor system performance
- **Alert logs**: Track alert dispatch status

Check the console output when running the system to see real-time logs.

---

🎉 **Congratulations!** You now have a fully functional Agentic Disaster Response system with MCP tools integration.

For more details, check the API documentation at http://127.0.0.1:8000/docs
