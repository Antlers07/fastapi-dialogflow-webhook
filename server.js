// ================================
// Dialogflow Webhook: Kitchen Bot
// ================================

const express = require("express");
const bodyParser = require("body-parser");

const app = express();
app.use(bodyParser.json());

// In-memory storage (for demo purposes)
let orders = [];
let stock = {
  rice: 50,
  chicken: 30,
  salmon: 20,
  prawns: 15,
  noodles: 40
};
let orderCounter = 1000;

// Webhook endpoint for Dialogflow
app.post("/webhook", (req, res) => {
  const intent = req.body.queryResult.intent.displayName;
  console.log("👉 Intent received:", intent);

  // --- Receive Order ---
  if (intent === "Receive Order") {
    const orderType = req.body.queryResult.parameters.order_type;
    const tableNum = req.body.queryResult.parameters.table_number || "N/A";
    const items = req.body.queryResult.parameters.food_items;

    const orderId = ++orderCounter;
    const order = {
      order_id: orderId,
      order_type: orderType,
      table_number: tableNum,
      items: items,
      status: "new"
    };

    orders.push(order);

    return res.json({
      fulfillmentText: `✅ Order #${orderId} received: ${orderType}, items: ${items}, table: ${tableNum}. Added to kitchen queue.`,
      payload: order
    });
  }

  // --- Update Preparation Status ---
  if (intent === "Update Preparation Status") {
    const orderId = parseInt(req.body.queryResult.parameters.order_id);
    const status = req.body.queryResult.parameters.status;

    const order = orders.find(o => o.order_id === orderId);
    if (order) {
      order.status = status;
      return res.json({
        fulfillmentText: `🍳 Order #${orderId} status updated to ${status}.`,
        payload: order
      });
    } else {
      return res.json({
        fulfillmentText: `⚠️ Order #${orderId} not found.`
      });
    }
  }

  // --- Notify Waitstaff ---
  if (intent === "Notify Waitstaff") {
    const tableNum = req.body.queryResult.parameters.table_number || "N/A";
    const orderId = req.body.queryResult.parameters.order_id || "Unknown";

    return res.json({
      fulfillmentText: `📢 Waitstaff notified: Order #${orderId} (Table ${tableNum}) is ready to serve.`,
      payload: {
        order_id: orderId,
        table_number: tableNum,
        notify: true
      }
    });
  }

  // --- Stock Low Alert ---
  if (intent === "Stock Low Alert") {
    const ingredient = req.body.queryResult.parameters.ingredient_name;

    return res.json({
      fulfillmentText: `⚠️ Stock Alert: ${ingredient} is running low. Admin notified.`,
      payload: {
        ingredient_name: ingredient,
        stock_status: "low"
      }
    });
  }

  // --- Show Current Orders ---
  if (intent === "Show Current Orders") {
    if (orders.length === 0) {
      return res.json({
        fulfillmentText: "📭 No current orders in the queue."
      });
    }
    const list = orders
      .map(o => `#${o.order_id} (Table ${o.table_number}): ${o.items} [${o.status}]`)
      .join("\n");
    return res.json({
      fulfillmentText: `📋 Current Orders:\n${list}`
    });
  }

  // --- Complete Order ---
  if (intent === "Complete Order") {
    const orderId = parseInt(req.body.queryResult.parameters.order_id);
    const index = orders.findIndex(o => o.order_id === orderId);

    if (index !== -1) {
      orders.splice(index, 1);
      return res.json({
        fulfillmentText: `✅ Order #${orderId} has been completed and removed from the kitchen queue.`
      });
    } else {
      return res.json({
        fulfillmentText: `⚠️ Order #${orderId} not found.`
      });
    }
  }

  // --- Update Stock Level ---
  if (intent === "Update Stock Level") {
    const ingredient = req.body.queryResult.parameters.ingredient_name;
    const amount = req.body.queryResult.parameters.amount;

    stock[ingredient] = amount;
    return res.json({
      fulfillmentText: `🔄 Stock for ${ingredient} updated to ${amount} units.`,
      payload: {
        ingredient_name: ingredient,
        stock_level: amount
      }
    });
  }

  // --- Check Stock Level ---
  if (intent === "Check Stock Level") {
    const ingredient = req.body.queryResult.parameters.ingredient_name;
    const amount = stock[ingredient] || 0;

    return res.json({
      fulfillmentText: `📦 Current stock of ${ingredient}: ${amount} units.`
    });
  }

  // --- Daily Summary ---
  if (intent === "Daily Summary") {
    const total = orders.length;
    const completed = 1000 + orderCounter - total; // rough count
    const pending = total;

    return res.json({
      fulfillmentText: `📊 Daily Summary:\nTotal Orders: ${completed + pending}\nCompleted: ${completed}\nPending: ${pending}`
    });
  }

  // --- Clear Queue ---
  if (intent === "Clear Queue") {
    orders = [];
    return res.json({
      fulfillmentText: "🗑️ All kitchen orders cleared."
    });
  }

  // --- Default Fallback ---
  return res.json({
    fulfillmentText: "❓ Sorry, I didn’t understand that request."
  });
});

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 Kitchen Webhook server running on port ${PORT}`);
});
