import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

resp = client.get('/api/sprint/plan/test_project', headers={'Authorization': 'Bearer test-token'})
print('status', resp.status_code)
print(resp.json())
