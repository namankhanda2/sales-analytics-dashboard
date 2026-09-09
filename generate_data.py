"""
Generates a realistic sales dataset (CSV) for the Sales Analytics Dashboard.

Run: python generate_data.py
Writes: data/sales.csv
"""

import csv
import random
from datetime import date, timedelta

random.seed(42)

REGIONS = ["North", "South", "East", "West"]

CATEGORIES = {
    "Electronics": ["Laptop", "Smartphone", "Headphones", "Monitor", "Tablet"],
    "Clothing": ["T-Shirt", "Jeans", "Jacket", "Sneakers", "Dress"],
    "Home & Kitchen": ["Mixer", "Coffee Maker", "Toaster", "Vacuum", "Lamp"],
    "Sports": ["Dumbbells", "Yoga Mat", "Treadmill", "Water Bottle", "Resistance Band"],
}

CUSTOMER_SEGMENTS = ["Retail", "Wholesale", "Corporate"]

PRODUCT_PRICES = {
    "Laptop": 899.0, "Smartphone": 699.0, "Headphones": 149.0, "Monitor": 279.0, "Tablet": 329.0,
    "T-Shirt": 19.99, "Jeans": 49.99, "Jacket": 89.99, "Sneakers": 79.99, "Dress": 59.99,
    "Mixer": 39.99, "Coffee Maker": 59.99, "Toaster": 29.99, "Vacuum": 129.99, "Lamp": 24.99,
    "Dumbbells": 34.99, "Yoga Mat": 24.99, "Treadmill": 499.0, "Water Bottle": 12.99, "Resistance Band": 15.99,
}


def random_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))


def generate_sales(n_rows=3000):
    start = date(2022, 1, 1)
    end = date(2025, 12, 31)
    rows = []

    for idx in range(1, n_rows + 1):
        order_date = random_date(start, end)
        region = random.choice(REGIONS)
        category = random.choice(list(CATEGORIES.keys()))
        product = random.choice(CATEGORIES[category])
        unit_price = PRODUCT_PRICES[product]
        quantity = random.randint(1, 5)

        if region == "West":
            quantity = max(1, int(quantity * random.uniform(0.9, 1.6)))
        if category == "Electronics":
            quantity = max(1, int(quantity * random.uniform(0.8, 1.4)))

        discount = random.choice([0.0, 0.0, 0.0, 0.05, 0.10, 0.20])
        unit_cost = unit_price * random.uniform(0.45, 0.6)
        segment = random.choice(CUSTOMER_SEGMENTS)
        if segment == "Wholesale":
            discount = max(discount, 0.10)

        revenue = round(unit_price * quantity * (1 - discount), 2)
        cost = round(unit_cost * quantity, 2)
        profit = round(revenue - cost, 2)

        rows.append({
            "order_id": f"ORD-{idx:05d}",
            "order_date": order_date.isoformat(),
            "region": region,
            "category": category,
            "product": product,
            "customer_segment": segment,
            "quantity": quantity,
            "unit_price": round(unit_price, 2),
            "discount": discount,
            "revenue": revenue,
            "cost": cost,
            "profit": profit,
        })

    return rows


def main():
    rows = generate_sales()
    with open("data/sales.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated {len(rows)} rows -> data/sales.csv")


if __name__ == "__main__":
    main()