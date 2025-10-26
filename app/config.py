import os
from dotenv import load_dotenv

load_dotenv()

NODE_BASE_URL = os.getenv("NODE_BASE_URL", "https://nexa-au2s.onrender.com/api")
SPRINT_DURATION_DAYS = int(os.getenv("SPRINT_DURATION_DAYS", 14))
HOURS_PER_DAY = float(os.getenv("HOURS_PER_DAY", 6))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Optional: If your Node backend requires an API key or bearer token, set the
# NODE_API_KEY environment variable. By default it's sent as an Authorization
# header with the 'Bearer ' prefix. You can override the header name or prefix
# using NODE_API_KEY_HEADER and NODE_API_KEY_PREFIX.
NODE_API_KEY = os.getenv("NODE_API_KEY")
NODE_API_KEY_HEADER = os.getenv("NODE_API_KEY_HEADER", "Authorization")
NODE_API_KEY_PREFIX = os.getenv("NODE_API_KEY_PREFIX", "Bearer ")
# Optional: If your Postman session used a cookie-based session, you can paste
# the Cookie header value here (e.g. "connect.sid=...; other=..."). This is
# less secure but useful for quick local testing when an API token is not
# available. Prefer NODE_API_KEY when possible.
NODE_COOKIE = os.getenv("NODE_COOKIE")
