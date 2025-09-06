const express = require('express');
const mysql = require('mysql2');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

// Create MySQL connection
const connection = mysql.createConnection({
    host: 'localhost',
    user: 'Antlers07',
    password: 'ts111',
    database: 'kitchen_chatbox'
});

// API endpoint to get orders with items
app.get('/api/orders', (req, res) => {
    const query = `
        SELECT o.*, GROUP_CONCAT(mi.Name SEPARATOR ', ') as items
        FROM orders o
        LEFT JOIN ordereditems oi ON o.OrderID = oi.OrderID
        LEFT JOIN menuitems mi ON oi.MenuItemID = mi.MenuItemID
        GROUP BY o.OrderID
        ORDER BY o.CreatedAt DESC
    `;
    
    connection.query(query, (error, results) => {
        if (error) {
            return res.status(500).json({ error: error.message });
        }
        res.json(results);
    });
});

// API endpoint to update order status
app.post('/api/orders/status', (req, res) => {
    const { orderId, status } = req.body;
    
    connection.query(
        'UPDATE orders SET OrderStatus = ? WHERE OrderID = ?',
        [status, orderId],
        (error, results) => {
            if (error) {
                return res.status(500).json({ error: error.message });
            }
            res.json({ success: true, message: 'Order status updated successfully' });
        }
    );
});

// API endpoint to get inventory
app.get('/api/inventory', (req, res) => {
    connection.query('SELECT * FROM inventory', (error, results) => {
        if (error) {
            return res.status(500).json({ error: error.message });
        }
        res.json(results);
    });
});

// API endpoint to create restock request
app.post('/api/restock', (req, res) => {
    const { itemId, quantity } = req.body;
    
    connection.query(
        'INSERT INTO restock_requests (InventoryID, QuantityRequested, Status) VALUES (?, ?, "pending")',
        [itemId, quantity],
        (error, results) => {
            if (error) {
                return res.status(500).json({ error: error.message });
            }
            res.json({ success: true, message: 'Restock request submitted' });
        }
    );
});

// Start server
app.listen(3000, () => {
    console.log('Server running on port 3000');
});