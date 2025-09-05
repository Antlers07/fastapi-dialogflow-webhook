const express = require('express');
const bodyParser = require('body-parser');
const mysql = require('mysql');

const app = express();
app.use(bodyParser.json());

// MySQL connection
const db = mysql.createConnection({
  host: 'localhost',
  user: 'root',
  password: 'ts111',
  database: 'kitchen_chatbot'
});

db.connect((err) => {
  if (err) throw err;
  console.log('Connected to MySQL');
});

// Dialogflow webhook endpoint
app.post('/webhook', (req, res) => {
  const intentName = req.body.queryResult.intent.displayName;

  if (intentName === 'Receive Order') {
    const tableNumber = req.body.queryResult.parameters.table_number;
    const items = req.body.queryResult.parameters.items;

    const sql = `INSERT INTO orders (table_number, items) VALUES (?, ?)`;
    db.query(sql, [tableNumber, items], (err, result) => {
      if (err) {
        return res.json({ fulfillmentText: 'Failed to save order.' });
      }
      res.json({ fulfillmentText: 'Order saved successfully!' });
    });
  }
});

app.listen(3000, () => console.log('Server is running on port 3000'));
