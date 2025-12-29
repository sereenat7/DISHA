from fastapi import FastAPI, HTTPException
import uvicorn
from Asycn_Alerts.alerts import send_parallel_alerts, logger
import os
from datetime import datetime

app = FastAPI(
    title="DISHA Alert System API",
    description="Emergency Alert System using Twilio for parallel calls and SMS",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {
        "service": "DISHA Alert System",
        "status": "active",
        "version": "1.0.0",
        "endpoints": {
            "trigger_alerts": "/api/alerts/trigger",
            "health": "/health"
        }
    }

@app.get("/health")
def health_check():
    twilio_configured = all([
        os.environ.get('TWILIO_ACCOUNT_SID'),
        os.environ.get('TWILIO_AUTH_TOKEN'),
        os.environ.get('TWILIO_PHONE_NUMBER')
    ])
    
    return {
        "status": "healthy" if twilio_configured else "configuration_incomplete",
        "twilio_configured": twilio_configured,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/alerts/trigger")
def trigger_alerts():
    try:
        twilio_configured = all([
            os.environ.get('TWILIO_ACCOUNT_SID'),
            os.environ.get('TWILIO_AUTH_TOKEN'),
            os.environ.get('TWILIO_PHONE_NUMBER')
        ])
        
        if not twilio_configured:
            raise HTTPException(
                status_code=500,
                detail="Twilio credentials not configured. Please set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER environment variables."
            )
        
        contacts = [
            {
                'phone': '+918850755760',
                'twiml_url': 'http://demo.twilio.com/docs/voice.xml',
                'sms_message': 'URGENT: This is an emergency alert! from Government of India by DISHA, Make sure you are safe'
            },
            {
                'phone': '+919529685725',
                'twiml_url': 'http://demo.twilio.com/docs/voice.xml',
                'sms_message': 'URGENT: This is an emergency alert! from Government of India by DISHA, Make sure you are safe'
            },
            {
                'phone': '+919322945843',
                'twiml_url': 'http://demo.twilio.com/docs/voice.xml',
                'sms_message': 'URGENT: This is an emergency alert! from Government of India by DISHA, Make sure you are safe'
            }
        ]
        
        logger.info("Alert trigger received via API")
        
        results = send_parallel_alerts(
            contacts,
            max_workers=5,
            num_call_attempts=5,
            wait_time_between_rounds=40
        )
        
        formatted_results = []
        for result in results:
            total_calls = len(result.get('calls', []))
            successful_calls = sum(1 for c in result.get('calls', []) if c.get('success'))
            
            formatted_results.append({
                "phone": result.get('phone'),
                "total_calls": total_calls,
                "successful_calls": successful_calls,
                "sms_sent": result.get('sms', {}).get('success', False),
                "call_details": result.get('calls', [])
            })
        
        return {
            "status": "completed",
            "message": "Alerts sent successfully",
            "total_contacts": len(results),
            "timestamp": datetime.now().isoformat(),
            "results": formatted_results
        }
        
    except Exception as e:
        logger.error(f"Error triggering alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)