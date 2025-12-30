# 🚨 How to Test Real Notifications - DISHA System

## 🎯 **Quick Test Options**

### **Option 1: Full End-to-End Test (Recommended)**

```bash
# 1. Start the system
python run_system.py

# 2. In another terminal, trigger a disaster
curl -X POST "http://127.0.0.1:8000/disaster/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "disaster_type": "flood",
    "location_lat": 19.0760,
    "location_lon": 72.8777,
    "severity": "high",
    "affected_radius_km": 5.0,
    "description": "TEST: Severe flooding in Mumbai - Real notification test",
    "estimated_affected_population": 2000
  }'

# 3. Check if people received SMS/emails
python view_alerts.py
```

### **Option 2: Direct SMS Test (Fastest)**

```bash
# Send immediate SMS to all registered numbers
python test_live_sms.py
```

### **Option 3: Service Integration Test**

```bash
# Test all services (SMS, Email, Push, News)
python test_real_notifications.py
```

---

## 📱 **What Will Happen When You Test**

### **Real People Will Receive:**

1. **📱 SMS Messages** to:

   - **+918850755760** (Joel Pawar)
   - **+919529685725** (Sereena Thomas)
   - **+919322945843** (Seane Dcosta)

2. **📧 Email Alerts** from: `alerts@disha.gov.in`

3. **🔔 Push Notifications** via Firebase

4. **📰 AI-Generated News** using Groq AI

---

## 🚀 **Step-by-Step Testing Guide**

### **Step 1: Start the System**

```bash
python run_system.py
```

_This starts the FastAPI server and disaster response agent_

### **Step 2: Trigger a Test Disaster**

**Option A: Using curl (Terminal)**

```bash
curl -X POST "http://127.0.0.1:8000/disaster/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "disaster_type": "earthquake",
    "location_lat": 28.6139,
    "location_lon": 77.2090,
    "severity": "critical",
    "affected_radius_km": 10.0,
    "description": "CRITICAL TEST: Major earthquake in Delhi - Testing emergency response",
    "estimated_affected_population": 5000
  }'
```

**Option B: Using Browser**

1. Go to: `http://127.0.0.1:8000/docs`
2. Find `/disaster/trigger` endpoint
3. Click "Try it out"
4. Use this JSON:

```json
{
  "disaster_type": "fire",
  "location_lat": 12.9716,
  "location_lon": 77.5946,
  "severity": "high",
  "affected_radius_km": 3.0,
  "description": "TEST: Building fire in Bangalore - Emergency notification test",
  "estimated_affected_population": 1000
}
```

### **Step 3: Monitor the Results**

**Check System Status:**

```bash
python view_alerts.py
```

**Detailed Monitoring:**

```bash
python monitor_alerts.py
# Choose option 1 for comprehensive monitoring
```

**Check Server Logs:**

```bash
# Look for real-time processing logs in the terminal running run_system.py
```

---

## 📊 **Expected Test Results**

### **✅ Success Indicators:**

1. **API Response:**

```json
{
  "disaster_id": "disaster_xxxxx_xxxxx",
  "status": "processing_started",
  "message": "Disaster event queued for autonomous processing"
}
```

2. **SMS Delivery:**

   - Joel, Sereena, and Seane receive SMS on their phones
   - SMS contains disaster details and safety instructions

3. **System Logs Show:**

   - "REAL SMS sent to +918850755760: SMxxxxxxx"
   - "REAL email sent to alerts@disha.gov.in"
   - "Firebase push notifications sent"
   - "Groq AI generated emergency bulletin"

4. **Monitor Shows:**
   - System health: HEALTHY
   - Processing status: alert_dispatch → completed
   - Successful deliveries: 3/3 SMS, emails sent

---

## 🧪 **Different Test Scenarios**

### **Test 1: Critical Emergency**

```bash
curl -X POST "http://127.0.0.1:8000/disaster/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "disaster_type": "explosion",
    "location_lat": 19.0760,
    "location_lon": 72.8777,
    "severity": "critical",
    "affected_radius_km": 2.0,
    "description": "CRITICAL: Industrial explosion in Mumbai - Immediate evacuation required",
    "estimated_affected_population": 800
  }'
```

_Expected: All channels activated (SMS, Email, Push, Emergency Broadcast)_

### **Test 2: Medium Priority**

```bash
curl -X POST "http://127.0.0.1:8000/disaster/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "disaster_type": "flood",
    "location_lat": 22.5726,
    "location_lon": 88.3639,
    "severity": "medium",
    "affected_radius_km": 8.0,
    "description": "MEDIUM: Flooding in Kolkata - Monitor situation",
    "estimated_affected_population": 3000
  }'
```

_Expected: SMS, Email, Push notifications (no emergency broadcast)_

### **Test 3: Low Priority**

```bash
curl -X POST "http://127.0.0.1:8000/disaster/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "disaster_type": "electrical",
    "location_lat": 13.0827,
    "location_lon": 80.2707,
    "severity": "low",
    "affected_radius_km": 1.0,
    "description": "LOW: Power outage in Chennai - Routine maintenance",
    "estimated_affected_population": 500
  }'
```

_Expected: Email and web notifications only_

---

## 🔍 **Troubleshooting**

### **If SMS Not Received:**

1. Check Twilio credentials in `.env`
2. Verify phone numbers are correct
3. Check Twilio account balance
4. Look for error messages in logs

### **If System Not Starting:**

```bash
# Check if ports are available
lsof -i :8000

# Kill existing processes
pkill -f "python run_system.py"

# Restart
python run_system.py
```

### **If No Response:**

```bash
# Test API directly
curl http://127.0.0.1:8000/health

# Check system status
python test_system.py
```

---

## 📞 **Contact Information**

**Test Phone Numbers (Will receive real SMS):**

- **Joel Pawar**: +918850755760
- **Sereena Thomas**: +919529685725
- **Seane Dcosta**: +919322945843

**Email**: alerts@disha.gov.in

---

## ⚠️ **Important Notes**

1. **Real SMS Cost**: Each test sends 3 real SMS messages (costs money)
2. **Rate Limits**: Don't spam - wait 30 seconds between tests
3. **Phone Notifications**: People will receive actual emergency alerts
4. **Production Ready**: This is a fully functional emergency system

---

## 🎉 **Quick Start Command**

**For immediate testing, just run:**

```bash
python test_live_sms.py
```

**This will send real SMS to all 3 phone numbers immediately!**

---

_Your DISHA disaster response system is now fully operational with real notifications! 🚨📱✅_
