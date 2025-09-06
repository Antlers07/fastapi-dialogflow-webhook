from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import mysql.connector
from mysql.connector import Error
from fastapi.responses import HTMLResponse
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Kitchen Chatbot API", version="1.0.0")

# Add CORS middleware for Dialogflow
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define Pydantic models for request validation (THIS IS KEY!)
class FoodItem(BaseModel):
    id: str
    name: Optional[str] = None
    quantity: int
    price: float

class Parameters(BaseModel):
    table_number: str
    food_items: List[FoodItem]

class QueryResult(BaseModel):
    parameters: Parameters

class DialogflowWebhookRequest(BaseModel):
    queryResult: QueryResult

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="ts111",
            database="kitchen_chatbot",
            autocommit=False
        )
        logger.info("Database connection established successfully")
        return connection
    except Error as e:
        logger.error(f"Error connecting to MySQL database: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

@app.post("/webhook")
async def webhook(request: DialogflowWebhookRequest):
    """
    Handle Dialogflow webhook requests for order processing
    """
    try:
        data = request.dict()
        print("Received data:", data)

        # Extract data from the validated request
        table_number = request.queryResult.parameters.table_number
        food_items = request.queryResult.parameters.food_items
        
        logger.info(f"Received order for table: {table_number}")
        
        # Validate required fields
        if not table_number or table_number == "Unknown":
            return {
                "fulfillmentText": "I need to know your table number to place the order. Which table are you at?"
            }
        
        if not food_items:
            return {
                "fulfillmentText": "Please specify what you'd like to order. What food items would you like?"
            }
        
        # Process the order in database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert into Orders table
        cursor.execute(
            "INSERT INTO Orders (TableNumber, OrderStatus) VALUES (%s, %s)",
            (table_number, "Pending")
        )
        order_id = cursor.lastrowid
        logger.info(f"Created order ID: {order_id} for table: {table_number}")

        # Insert into OrderedItems table - FIXED: Convert id to integer
        for item in food_items:
            cursor.execute(
                "INSERT INTO OrderedItems (OrderID, ItemID, Quantity, Price) VALUES (%s, %s, %s, %s)",
                (order_id, int(item.id), item.quantity, item.price)  # ← int() conversion here
            )

        # Commit the transaction
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "fulfillmentText": f"✅ Order received for table {table_number}! Your order has been placed and will be ready soon. Order ID: {order_id}",
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [f"✅ Order received for table {table_number}! Your order has been placed and will be ready soon. Order ID: {order_id}"]
                    }
                }
            ]
        }

    except ValueError:
        logger.error("ItemID must be a number")
        return {
            "fulfillmentText": "Sorry, there was an error with the item format. Please make sure item IDs are numbers."
        }
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return {
            "fulfillmentText": "Sorry, I encountered an error while processing your order. Please try again."
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
        result = cursor.fetchone()
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
        
        cursor.execute("SELECT * FROM Orders ORDER BY OrderTimestamp DESC LIMIT 10")
        orders = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {"orders": orders, "count": len(orders)}
        
    except Error as e:
        return {"error": "Failed to fetch orders", "details": str(e)}

@app.get("/chat", response_class=HTMLResponse)
async def chat_interface():
    """Serve the chat interface HTML page"""
    html_content = """
    <!DOCTYPE html>
<html>
<head>
    <title>🍳 Kitchen Chatbot</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Arial', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .chat-container {
            width: 100%;
            max-width: 400px;
            height: 600px;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .chat-header {
            background: #4CAF50;
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 18px;
            font-weight: bold;
        }
        
        .chat-messages {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background: #f8f9fa;
        }
        
        .message {
            margin: 10px 0;
            padding: 12px 15px;
            border-radius: 15px;
            max-width: 80%;
            word-wrap: break-word;
            line-height: 1.4;
        }
        
        .user-message {
            background: #007bff;
            color: white;
            margin-left: auto;
            text-align: right;
        }
        
        .bot-message {
            background: white;
            color: #333;
            border: 1px solid #ddd;
            margin-right: auto;
        }
        
        .chat-input {
            display: flex;
            padding: 15px;
            background: white;
            border-top: 1px solid #eee;
        }
        
        #user-input {
            flex: 1;
            padding: 12px 15px;
            border: 1px solid #ddd;
            border-radius: 25px;
            outline: none;
            font-size: 14px;
        }
        
        #user-input:focus {
            border-color: #4CAF50;
        }
        
        #send-button {
            padding: 12px 20px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            margin-left: 10px;
            font-weight: bold;
            transition: background 0.3s;
        }
        
        #send-button:hover {
            background: #45a049;
        }
        
        .typing-indicator {
            color: #666;
            font-style: italic;
            text-align: center;
            padding: 10px;
            font-size: 14px;
        }
        
        /* Scrollbar styling */
        .chat-messages::-webkit-scrollbar {
            width: 6px;
        }
        
        .chat-messages::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        
        .chat-messages::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 10px;
        }
        
        .chat-messages::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            🍳 Kitchen Chatbot
        </div>
        
        <div class="chat-messages" id="chat-messages">
            <div class="message bot-message">
                👋 Hello! I'm your kitchen assistant.<br><br>
                You can say things like:<br>
                • "I want to order pizza for table 5"<br>
                • "Order burger and fries for table 3"<br>
                • "I'd like to place an order"<br><br>
                What would you like to order today?
            </div>
        </div>
        
        <div class="chat-input">
            <input type="text" id="user-input" placeholder="Type your message here..." autocomplete="off">
            <button id="send-button">Send</button>
        </div>
    </div>

    <script>
        const chatMessages = document.getElementById('chat-messages');
        const userInput = document.getElementById('user-input');
        const sendButton = document.getElementById('send-button');

        // Function to add message to chat
        function addMessage(text, isUser) {
            const messageDiv = document.createElement('div');
            messageDiv.className = isUser ? 'message user-message' : 'message bot-message';
            messageDiv.innerHTML = text;
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        // Function to show typing indicator
        function showTypingIndicator() {
            const typingDiv = document.createElement('div');
            typingDiv.className = 'typing-indicator';
            typingDiv.id = 'typing-indicator';
            typingDiv.textContent = 'Bot is typing...';
            chatMessages.appendChild(typingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        // Function to hide typing indicator
        function hideTypingIndicator() {
            const typingIndicator = document.getElementById('typing-indicator');
            if (typingIndicator) {
                chatMessages.removeChild(typingIndicator);
            }
        }

        // Simulate Dialogflow response
        async function simulateDialogflowResponse(userMessage) {
            return new Promise(resolve => {
                setTimeout(() => {
                    const lowerMessage = userMessage.toLowerCase();
                    
                    if (lowerMessage.includes('hello') || lowerMessage.includes('hi') || lowerMessage.includes('hey')) {
                        resolve("Hello! How can I help you with your order today? 🍕");
                    }
                    else if (lowerMessage.includes('pizza')) {
                        resolve("Great choice! 🍕 How many pizzas would you like and for which table?");
                    }
                    else if (lowerMessage.includes('burger')) {
                        resolve("Burgers are awesome! 🍔 How many would you like and for which table?");
                    }
                    else if (lowerMessage.includes('fries')) {
                        resolve("Crispy fries! 🍟 How many portions would you like?");
                    }
                    else if (lowerMessage.includes('menu')) {
                        resolve("📋 Our menu:<br>• Pizza - $12.99<br>• Burger - $8.99<br>• Fries - $4.99<br>• Salad - $7.99<br>• Coffee - $2.99<br>What would you like to order?");
                    }
                    else if (lowerMessage.includes('table') && lowerMessage.match(/table\s+\d/)) {
                        const tableNumber = userMessage.match(/table\s+(\d+)/i)[1];
                        resolve("Perfect! Table " + tableNumber + " noted. What would you like to order?");
                    }
                    else if (lowerMessage.includes('thank')) {
                        resolve("You're welcome! Your order will be ready soon. Enjoy your meal! 😊");
                    }
                    else if (lowerMessage.includes('order') || lowerMessage.includes('want') || lowerMessage.includes('get')) {
                        resolve("I'd be happy to take your order! What would you like to eat and for which table?");
                    }
                    else {
                        resolve("Thank you! I've received your message. How can I help with your order today?");
                    }
                }, 1000 + Math.random() * 1000);
            });
        }

        // Main function to handle message sending
        async function sendMessage() {
            const message = userInput.value.trim();
            if (!message) return;

            // Add user message
            addMessage(message, true);
            userInput.value = '';
            
            // Show typing indicator
            showTypingIndicator();
            
            try {
                // Get bot response
                const botResponse = await simulateDialogflowResponse(message);
                
                // Remove typing indicator and add bot response
                hideTypingIndicator();
                addMessage(botResponse, false);
                
            } catch (error) {
                hideTypingIndicator();
                addMessage("Sorry, I'm having trouble connecting. Please try again.", false);
                console.error("Error:", error);
            }
        }

        // Event listeners
        sendButton.addEventListener('click', sendMessage);
        
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });

        // Focus input on load and allow Enter key
        userInput.focus();
        userInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault(); // Prevent form submission
                sendMessage();
            }
        });

        // Make chat scroll to bottom on load
        window.addEventListener('load', function() {
            chatMessages.scrollTop = chatMessages.scrollHeight;
            userInput.focus();
        });
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)
