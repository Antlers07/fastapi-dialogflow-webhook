from fastapi import FastAPI, Request
import mysql.connector
from mysql.connector import Error

app = FastAPI()

# MySQL connection function
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="ts111",
        database="kitchen_chatbot"
    )

# Webhook endpoint
@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    intent_name = data['queryResult']['intent']['displayName']

    if intent_name == "Receive Order":
        table_number = data['queryResult']['parameters']['table_number']
        items = data['queryResult']['parameters']['items']

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO orders (table_number, items) VALUES (%s, %s)",
                (table_number, items)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return {"fulfillmentText": "Order saved successfully!"}
        except Error as e:
            return {"fulfillmentText": f"Failed to save order: {e}"}
    return {"fulfillmentText": "Intent not handled."}
