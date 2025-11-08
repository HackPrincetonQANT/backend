import asyncio
import json
import os
import sys
import uuid
from dedalus_labs import AsyncDedalus, DedalusRunner
from dotenv import load_dotenv

# Load environment variables from database API directory
env_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'api', '.env')
load_dotenv(env_path)

# Add parent directory to path for database imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database', 'api'))
from db import execute_many

async def categorize_products_batch(runner, products_data):
    """
    Categorize all products in a single batch call to Dedalus AI.
    This is much faster and more cost-effective than individual calls.

    Expected input: List of dicts with 'name' and 'price' keys
    Expected output: List of categorization results
    """
    # Build the batch prompt with all products
    product_list = "\n".join([
        f"{i+1}. {p['name']} (${p['price']:.2f})"
        for i, p in enumerate(products_data)
    ])

    prompt = f"""You are a product taxonomy classifier. Categorize ALL these products in one response.

Products to categorize:
{product_list}

Rules:
- Suggest the most appropriate category for each (e.g., Electronics, Groceries, Pet Supplies, etc.)
- Use CONSISTENT category names across similar products
- Optionally provide subcategories for specificity
- If confidence < 0.6, set ask_user=true
- Keep category names concise and standard (no brand names)

Return ONLY a valid JSON array with one object per product:
[
  {{
    "item_number": 1,
    "category": "<main category>",
    "subcategory": "<optional subcategory or null>",
    "confidence": <float 0..1>,
    "reason": "<=12 words explaining why",
    "ask_user": <true|false>
  }},
  ...
]"""

    response = await runner.run(
        input=prompt,
        model="openai/gpt-5-mini"
    )

    # Parse JSON array response
    try:
        results = json.loads(response.final_output)
        if not isinstance(results, list):
            raise ValueError("Expected JSON array")
        return results
    except (json.JSONDecodeError, ValueError) as e:
        # Fallback: create default categorizations
        return [
            {
                "item_number": i + 1,
                "category": "Miscellaneous",
                "subcategory": None,
                "confidence": 0.0,
                "reason": f"Failed to parse batch response: {str(e)}",
                "ask_user": True
            }
            for i in range(len(products_data))
        ]

def insert_to_snowflake_batch(all_results, merchant_name):
    """
    Insert all categorized products to Snowflake test table using batch insert.

    Expected input: List of categorized product results
    Expected output: Number of successfully inserted records
    """
    user_id = "test_user_001"

    # Prepare all parameter sets for batch insert
    params_list = []
    for result in all_results:
        params_list.append({
            'item_id': str(uuid.uuid4()),
            'purchase_id': f"amzn_{result['transaction_id']}",
            'user_id': user_id,
            'merchant': merchant_name,
            'ts': result['purchased_at'],
            'item_name': result['item'],
            'category': result['category'],
            'subcategory': result.get('subcategory'),
            'price': result['price'],
            'qty': result['quantity'],
            'reason': result['reason'],
            'confidence': result['confidence']
        })

    # Single batch insert for all records
    sql = """
    INSERT INTO purchase_items_test (
        item_id, purchase_id, user_id, merchant, ts,
        item_name, category, subcategory, price, qty,
        detected_needwant, reason, confidence, status
    ) VALUES (
        %(item_id)s, %(purchase_id)s, %(user_id)s, %(merchant)s,
        TO_TIMESTAMP_TZ(%(ts)s),
        %(item_name)s, %(category)s, %(subcategory)s, %(price)s, %(qty)s,
        NULL, %(reason)s, %(confidence)s, 'active'
    )
    """

    return execute_many(sql, params_list)

async def main():
    """
    Load Amazon mock data, categorize products with Dedalus AI batch call,
    and insert to Snowflake test table.

    Expected input: JSON file with Amazon transactions containing products
    Expected output: Category classification and database insertion confirmation
    """
    # Load JSON data
    json_path = os.path.join(os.path.dirname(__file__), 'data', 'simplify_mock_amazon.json')

    with open(json_path, 'r') as f:
        data = json.load(f)

    merchant_name = data['merchant']['name']

    # Initialize Dedalus client
    client = AsyncDedalus()
    runner = DedalusRunner(client)

    # Collect all products from all transactions
    products_to_categorize = []
    product_metadata = []

    for transaction in data['transactions']:
        for product in transaction['products']:
            products_to_categorize.append({
                'name': product['name'],
                'price': float(product['price']['total'])
            })
            product_metadata.append({
                'transaction_id': transaction['id'],
                'transaction_datetime': transaction['datetime'],
                'name': product['name'],
                'price': float(product['price']['total']),
                'quantity': product['quantity']
            })

    # Single batch categorization call
    categorization_results = await categorize_products_batch(runner, products_to_categorize)

    # Merge categorization results with product metadata
    all_results = []
    for i, cat_result in enumerate(categorization_results):
        metadata = product_metadata[i]
        all_results.append({
            "item": metadata['name'],
            "category": cat_result['category'],
            "subcategory": cat_result.get('subcategory'),
            "price": metadata['price'],
            "quantity": metadata['quantity'],
            "purchased_at": metadata['transaction_datetime'],
            "confidence": cat_result['confidence'],
            "reason": cat_result['reason'],
            "ask_user": cat_result['ask_user'],
            "transaction_id": metadata['transaction_id']
        })

    # Calculate summary statistics
    category_data = {}
    for result in all_results:
        category = result['category']
        if category not in category_data:
            category_data[category] = {"total_spend": 0.0, "count": 0}
        category_data[category]["total_spend"] += result['price']
        category_data[category]["count"] += 1

    # Insert to Snowflake test table
    try:
        inserted_count = insert_to_snowflake_batch(all_results, merchant_name)

        # Output final summary
        print(f"✅ Categorized {len(all_results)} products from {merchant_name}")
        print(f"✅ Inserted {inserted_count} records to purchase_items_test")
        print("\nCategory Summary:")
        for category in sorted(category_data.keys()):
            data_cat = category_data[category]
            print(f"  • {category}: ${data_cat['total_spend']:.2f} ({data_cat['count']} items)")

        # Flag low confidence items
        low_confidence = [r for r in all_results if r['ask_user']]
        if low_confidence:
            print(f"\n⚠️  {len(low_confidence)} product(s) flagged for manual review")

    except Exception as e:
        print(f"❌ Database operation failed: {str(e)}")

        # Save to JSON file as backup
        output_data = {"all_results": all_results, "category_aggregation": category_data}
        output_path = os.path.join(os.path.dirname(__file__), 'data', 'categorized_products.json')
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"💾 Results saved to: {output_path}")

    return all_results

if __name__ == "__main__":
    asyncio.run(main())
