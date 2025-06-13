import sqlite3

# Connect to the database
conn = sqlite3.connect('database2.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()



# Fetch orders along with the payment status
cursor.execute("""
    SELECT id, user_id, total_amount, status, date, payment_status
    FROM "order"
""")
orders = cursor.fetchall()

# Fetch order details
cursor.execute("""
    SELECT od.order_id, od.product_id, od.quantity, od.price, p.name 
    FROM order_details od
    JOIN product p ON od.product_id = p.id
""")
order_details = cursor.fetchall()

# Combine order details with orders
orders_with_details = []
for order in orders:
    order_id = order['id']
    # Get the corresponding order details for this order
    details = [od for od in order_details if od['order_id'] == order_id]
    orders_with_details.append({
        'order': order,
        'details': details
    })

# Display orders along with their details and payment status
for order_with_details in orders_with_details:
    print(f"Order ID: {order_with_details['order']['id']}")
    print(f"Total Amount: {order_with_details['order']['total_amount']}")
    print(f"Payment Status: {order_with_details['order']['payment_status']}")
    print("Order Details:")
    for detail in order_with_details['details']:
        print(f"  Product: {detail['name']}, Quantity: {detail['quantity']}, Price: {detail['price']}")
    print("-" * 40)

# Close the connection
conn.close()


