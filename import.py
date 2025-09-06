import pydantic
import fastapi
import uvicorn
import mysql.connector

print("=" * 50)
print("SUCCESS: All packages installed correctly!")
print("=" * 50)
print("Pydantic version:", pydantic.__version__)
print("FastAPI version:", fastapi.__version__)

# Test basic functionality
from pydantic import BaseModel

class TestModel(BaseModel):
    name: str
    value: int

test = TestModel(name="test", value=123)
print("Pydantic test passed:", test.dict())
print("=" * 50)