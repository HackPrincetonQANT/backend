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
from db import execute, fetch_all

async def categorize_product(runner, product_name):
    """
    Categorize a single product using Dedalus AI with structured JSON output.
    AI is free to suggest any category without constraints.

    Expected input: Product name string
    Expected output: Dict with category, subcategory, confidence, reason fields
    """
    prompt = f"""You are a product taxonomy classifier. Categorize this product:

Product: {product_name}

Rules:
- Suggest the most appropriate category (e.g., Electronics, Groceries, Pet Supplies, etc.)
- Optionally provide a subcategory for more specificity
- If confidence < 0.6, set ask_user=true
- Keep category names concise and standard (no brand names)

Return ONLY valid JSON:
{{
  "category": "<main category>",
  "subcategory": "<optional subcategory or null>",
  "confidence": <float 0..1>,
  "reason": "<=12 words explaining why",
  "ask_user": <true|false>
}}"""

    response = await runner.run(
        input=prompt,
        model="openai/gpt-5-mini"
    )

    # Parse JSON response
    try:
        result = json.loads(response.final_output)
        # Ensure subcategory is present
        if 'subcategory' not in result:
            result['subcategory'] = None
        return result
    except json.JSONDecodeError:
        # Fallback if model doesn't return valid JSON
        return {
            "category": "Miscellaneous",
            "subcategory": None,
            "confidence": 0.0,
            "reason": "Failed to parse response",
            "ask_user": True
        }

def insert_to_snowflake(all_results, merchant_name):
    """
    Insert categorized products into Snowflake purchase_items table.

    Expected input: List of categorized product results
    Expected output: Number of successfully inserted records
    """
    # Use test user_id for now
    user_id = "test_user_001"

    inserted_count = 0

    for result in all_results:
        try:
            # Generate unique IDs
            item_id = str(uuid.uuid4())
            purchase_id = f"amzn_{result['transaction_id']}"

            # Prepare SQL for purchase_items table
            sql = """
            INSERT INTO purchase_items (
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

            params = {
                'item_id': item_id,
                'purchase_id': purchase_id,
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
            }

            execute(sql, params)
            inserted_count += 1

        except Exception as e:
            print(f"  ⚠️  Failed to insert {result['item']}: {str(e)}")

    return inserted_count

async def main():
    """
    Load Amazon mock data, categorize products with Dedalus AI, and insert to Snowflake.

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

    # Track results
    all_results = []
    total_products = sum(len(transaction['products']) for transaction in data['transactions'])

    print(f"🔄 Categorizing {total_products} products from {merchant_name}...")

    # Loop through all transactions and products
    processed = 0
    for transaction in data['transactions']:
        transaction_id = transaction['id']
        transaction_datetime = transaction['datetime']

        for product in transaction['products']:
            product_name = product['name']
            product_price = float(product['price']['total'])
            product_quantity = product['quantity']

            # Categorize product (quietly)
            result = await categorize_product(runner, product_name)

            # Store result with all fields needed for Snowflake
            all_results.append({
                "item": product_name,
                "category": result['category'],
                "subcategory": result.get('subcategory'),
                "price": product_price,
                "quantity": product_quantity,
                "purchased_at": transaction_datetime,
                "confidence": result['confidence'],
                "reason": result['reason'],
                "ask_user": result['ask_user'],
                "transaction_id": transaction_id
            })

            processed += 1
            print(f"  [{processed}/{total_products}] {product_name} → {result['category']}")


    # Print summary
    print("\n" + "=" * 80)
    print("CATEGORIZATION SUMMARY")
    print("=" * 80)

    # Aggregate by category
    category_data = {}
    for result in all_results:
        category = result['category']
        if category not in category_data:
            category_data[category] = {"total_spend": 0.0, "count": 0}
        category_data[category]["total_spend"] += result['price']
        category_data[category]["count"] += 1

    for category in sorted(category_data.keys()):
        data = category_data[category]
        print(f"  {category}: ${data['total_spend']:.2f} ({data['count']} items)")

    # Flag low confidence items
    low_confidence = [r for r in all_results if r['ask_user']]
    if low_confidence:
        print(f"\n⚠️  {len(low_confidence)} product(s) need manual review")

    # Insert to Snowflake
    print("\n" + "=" * 80)
    print("SNOWFLAKE DATABASE UPDATE")
    print("=" * 80)

    try:
        print("📤 Inserting categorized products to Snowflake...")
        inserted_count = insert_to_snowflake(all_results, merchant_name)
        print(f"✅ Successfully inserted {inserted_count}/{len(all_results)} products")

        # Verify insertion
        print("\n🔍 Verifying database update...")
        verification_sql = """
        SELECT category, COUNT(*) as count, SUM(price) as total_spend
        FROM purchase_items
        WHERE merchant = %(merchant)s
        GROUP BY category
        ORDER BY total_spend DESC
        """
        db_results = fetch_all(verification_sql, {'merchant': merchant_name})

        if db_results:
            print("✅ Database verification successful:")
            for row in db_results:
                print(f"  {row['CATEGORY']}: ${row['TOTAL_SPEND']:.2f} ({row['COUNT']} items)")
        else:
            print("⚠️  No results found in database (may need different query)")

    except Exception as e:
        print(f"❌ Database operation failed: {str(e)}")
        print("💾 Results saved to JSON as backup")

        # Save to JSON file as backup
        output_data = {"all_results": all_results, "category_aggregation": category_data}
        output_path = os.path.join(os.path.dirname(__file__), 'data', 'categorized_products.json')
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"   File: {output_path}")

    print("\n" + "=" * 80)
    return all_results

if __name__ == "__main__":
    asyncio.run(main())