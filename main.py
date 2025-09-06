from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import mysql.connector
from mysql.connector import Error
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Kitchen Chatbot API", version="1.0.0")

# Add CORS middleware for Dialogflow
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the expected request structure
class FoodItem(BaseModel):
    id: str
    name: Optional[str] = None
    quantity: int
    price: float

class DialogflowParameters(BaseModel):
    table_number: Optional[str] = "Unknown"
    food_items: List[FoodItem] = []

class QueryResult(BaseModel):
    parameters: DialogflowParameters

class DialogflowWebhookRequest(BaseModel):
    queryResult: QueryResult

def get_db_connection():
    """Create and return a database connection"""
    try:
        # Use environment variables for production
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "ts111"),
            database=os.getenv("DB_NAME", "kitchen_chatbot"),
            autocommit=False
        )
        logger.info("Database connection established successfully")
        return connection
    except Error as e:
        logger.error(f"Error connecting to MySQL database: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

@app.post("/webhook")
async def webhook(request: DialogflowWebhookRequest):
    """Handle Dialogflow webhook requests for order processing"""
    try:
        # Extract parameters from the validated request
        table_number = request.queryResult.parameters.table_number
        items = request.queryResult.parameters.food_items
        
        logger.info(f"Received order for table: {table_number} with {len(items)} items")
        
        # Validate required parameters
        if not table_number or table_number == "Unknown":
            logger.warning("Table number not provided")
            return {
                "fulfillmentText": "I need to know your table number to place the order. Which table are you at?"
            }
        
        if not items:
            logger.warning("No food items provided")
            return {
                "fulfillmentText": "Please specify what you'd like to order. What food items would you like?"
            }

        # Process the order in database
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Insert into Orders table
            cursor.execute(
                "INSERT INTO Orders (TableNumber, OrderStatus) VALUES (%s, %s)",
                (table_number, "Pending")
            )
            order_id = cursor.lastrowid
            logger.info(f"Created order ID: {order_id} for table: {table_number}")

            # Insert into OrderedItems table
            for item in items:
                cursor.execute(
                    """INSERT INTO OrderedItems (OrderID, ItemID, Quantity, Price) 
                    VALUES (%s, %s, %s, %s)""",
                    (order_id, item.id, item.quantity, item.price)
                )
                logger.info(f"Added item: {item.id} x {item.quantity} to order {order_id}")

            # Commit the transaction
            conn.commit()
            logger.info(f"Order {order_id} committed successfully")

            # Prepare success response
            response = {
                "fulfillmentText": f"✅ Order received for table {table_number}! Your order has been placed and will be ready soon. Order ID: {order_id}",
                "fulfillmentMessages": [
                    {
                        "text": {
                            "text": [f"✅ Order received for table {table_number}! Your order has been placed and will be ready soon. Order ID: {order_id}"]
                        }
                    }
                ],
                "source": "kitchen-chatbot-api"
            }
            
            return response

        except Error as db_error:
            # Rollback in case of database error
            if conn:
                conn.rollback()
            logger.error(f"Database error: {db_error}")
            raise HTTPException(status_code=500, detail="Database operation failed")
            
        finally:
            # Always close connections
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    except Exception as e:
        logger.error(f"Unexpected error in webhook: {e}")
        return {
            "fulfillmentText": "Sorry, I encountered an unexpected error while processing your order. Please try again in a moment."
        }

@app.get("/")
async def root():
    return {
        "message": "Kitchen Chatbot API is running",
        "status": "active",
        "endpoints": {
            "webhook": "POST /webhook",
            "health": "GET /health",
            "orders": "GET /orders",
            "docs": "GET /docs"
        }
    }

@app.get("/health")
async def health_check():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Error as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

@app.get("/orders")
async def get_orders():
    """Get all orders for testing"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT o.OrderID, o.TableNumber, o.OrderStatus, o.OrderTimestamp,
                   oi.ItemID, oi.Quantity, oi.Price
            FROM Orders o
            LEFT JOIN OrderedItems oi ON o.OrderID = oi.OrderID
            ORDER BY o.OrderTimestamp DESC
            LIMIT 10
        """)
        
        orders = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return {"orders": orders, "count": len(orders)}
        
    except Error as e:
        logger.error(f"Error fetching orders: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch orders")

# Add this for Render deployment
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)