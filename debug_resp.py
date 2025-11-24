from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
project_id = "68d3b6e481ea8e0ca2e086ee"
url = f"/api/sprint/plan/{project_id}"
body = {
    "members": [
        {"_id":"m1","name":"Alice Johnson","role":"backend","baseWeeklyHours":40,"unavailableDates":["2025-12-01"],"availabilityPct":0.9,"skillEfficiencyMultiplier":1.1,"reliabilityScore":0.95,"overloadRiskScore":0.0,"velocity":10},
        {"_id":"m2","name":"Sami Khan","role":"frontend","baseWeeklyHours":40,"unavailableDates":[],"availabilityPct":1.0,"skillEfficiencyMultiplier":1.0,"reliabilityScore":0.85,"overloadRiskScore":0.05,"velocity":8}
    ],
    "sprint_config": {"sprintLengthDays":14,"workHoursPerDay":6}
}
resp = client.post(url, json=body)
print('status', resp.status_code)
js = resp.json()
print('keys:', list(js.keys()))
print('assignmentStrategy:', js.get('assignmentStrategy'))
print('totalEffort:', js.get('totalEffort'))
print('memberWorkloadSummary:', js.get('memberWorkloadSummary'))
