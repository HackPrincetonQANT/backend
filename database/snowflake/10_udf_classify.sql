USE ROLE BALANCEIQ_ROLE;
USE WAREHOUSE BALANCEIQ_WH;
USE DATABASE BALANCEIQ_DB;
USE SCHEMA CORE;

CREATE OR REPLACE FUNCTION CLASSIFY_NEEDWANT(
  USER_ID STRING,
  MERCHANT STRING,
  ITEM_NAME STRING,
  CATEGORY STRING,
  SUBCATEGORY STRING,
  PRICE FLOAT
)
RETURNS OBJECT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'classify'
AS
$$
from typing import Dict

def _norm(s):
    return (s or '').strip().lower()

NEED_KW = {'rent','utility','medication','insulin','diaper','grocery','transit','bus','metro','gas','mortgage'}
WANT_KW = {'latte','frappuccino','gaming','rgb','snack','candy','alcohol','cocktail','keyboard','headset','fast food','dessert'}

def classify(session, USER_ID, MERCHANT, ITEM_NAME, CATEGORY, SUBCATEGORY, PRICE) -> Dict:
    uid = _norm(USER_ID)
    cat = _norm(CATEGORY)
    sub = _norm(SUBCATEGORY)
    name = _norm(ITEM_NAME)
    merch = _norm(MERCHANT)

    # 1) user rules (subcategory → category)
    rule = None
    if sub:
        rows = session.sql("""
            SELECT rule, reason FROM user_category_rules
            WHERE user_id = %s AND category = %s AND subcategory = %s
        """, params=[uid, cat, sub]).collect()
        if rows:
            rule = rows[0]['RULE'], rows[0]['REASON']
    if rule is None and cat:
        rows = session.sql("""
            SELECT rule, reason FROM user_category_rules
            WHERE user_id = %s AND category = %s AND subcategory IS NULL
        """, params=[uid, cat]).collect()
        if rows:
            rule = rows[0]['RULE'], rows[0]['REASON']

    if rule is not None:
        r, why = rule
        if r == 'ban':
            return {"classification":"want","reason":"User ban → treat as discretionary","confidence":0.95}
        if r == 'always_need':
            return {"classification":"need","reason": f"User rule: {why or 'always_need'}","confidence":0.95}
        if r == 'always_want':
            return {"classification":"want","reason": f"User rule: {why or 'always_want'}","confidence":0.95}

    # 2) taxonomy default (subcategory → category)
    if sub:
        rows = session.sql("""
            SELECT default_needwant FROM category_taxonomy
            WHERE category = %s AND subcategory = %s
        """, params=[cat, sub]).collect()
        if rows:
            return {"classification": rows[0]['DEFAULT_NEEDWANT'], "reason":"Taxonomy (subcategory)", "confidence":0.80}
    if cat:
        rows = session.sql("""
            SELECT default_needwant FROM category_taxonomy
            WHERE category = %s AND subcategory IS NULL
        """, params=[cat]).collect()
        if rows:
            return {"classification": rows[0]['DEFAULT_NEEDWANT'], "reason":"Taxonomy (category)", "confidence":0.70}

    # 3) keyword/merchant heuristic
    text = f"{merch} {name}"
    if any(k in text for k in NEED_KW):
        return {"classification":"need","reason":"Keyword heuristic → essential","confidence":0.60}
    if any(k in text for k in WANT_KW):
        return {"classification":"want","reason":"Keyword heuristic → discretionary","confidence":0.60}

    # 4) fallback on price
    if PRICE is not None and PRICE >= 500:
        return {"classification":"want","reason":"High-ticket, no rule/taxonomy","confidence":0.55}

    return {"classification":"unknown","reason":"Insufficient signals","confidence":0.10}
$$;

-- Quick test
SELECT CLASSIFY_NEEDWANT('u_demo','Starbucks','Caffè Latte','Coffee','Latte',5.25) AS latte;
SELECT CLASSIFY_NEEDWANT('u_demo','Walmart','Whole Milk 1gal','Groceries','Dairy',3.89) AS milk;