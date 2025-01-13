import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from pymongo import MongoClient
from datetime import datetime
import os
from motor.motor_asyncio import AsyncIOMotorClient

# Set up logging to console (optional)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("RequestLogger")

# MongoDB setup
client = AsyncIOMotorClient(os.getenv("MONGO_URI"))  # Adjust your MongoDB URI
db = client['reviewverseapp_logs']  # Database name
collection = db['logs']  # Collection name

class LoggingMiddleware(BaseHTTPMiddleware):
    async def log_message(self, message: str):
        logger.info(message)

    async def save_log_to_db(self, client_ip: str, path: str, status_code: int):
        log_entry = {
            "client_ip": client_ip,
            "path": path,
            "status_code": status_code,
            "timestamp": datetime.now()
        }
        collection.insert_one(log_entry)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        path = request.url.path
        
        # Log incoming request
        await self.log_message(f"Request from IP: {client_ip} to path: {path}")

        # Process the request
        response = await call_next(request)

        # Log outgoing response with status code
        await self.log_message(f"Response for {path} from IP: {client_ip} with status {response.status_code}")

        # Save log to MongoDB
        await self.save_log_to_db(client_ip, path, response.status_code)
        
        return response
