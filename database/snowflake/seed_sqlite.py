import sqlite3, uuid, datetime as dt

conn = sqlite3.connect("local.db")
cur = conn.cursor()

# Run schema
with open("sqlite/fallback.sql","r",encoding="utf-8") as f:
    cur.executescript(f.read())

def iso(days_ago=0, hours_ago=0):
    return (dt.datetime.utcnow() - dt.timedelta(days=days_ago, hours=hours_ago)).isoformat(timespec="seconds") + "Z"

user = "u_demo_min"

tx_rows = [
 ("t1", user, "ext-1001","Starbucks",        525,"USD","Coffee","want",0.95, iso(1,0)),
 ("t2", user, "ext-1002","Walmart",          389,"USD","Groceries","need",0.90, iso(2,0)),
 ("t3", user, "ext-1003","Chipotle",        1299,"USD","Dining Out","want",0.85, iso(3,0)),
 ("t4", user, "ext-1004","Metro",            250,"USD","Transport","need",0.80, iso(3,2)),
 ("t5", user, "ext-1005","Amazon",          5999,"USD","Electronics","want",0.70, iso(4,0)),
 ("t6", user, "ext-1006","Trader Joes",     4587,"USD","Groceries","need",0.88, iso(5,0)),
 ("t7", user, "ext-1007","Starbucks",        525,"USD","Coffee","want",0.95, iso(6,0)),
 ("t8", user, "ext-1008","Apartment Rent",120000,"USD","Rent","need",0.99, iso(10,0)),
 ("t9", user, "ext-1009","CVS Pharmacy",    1899,"USD","Healthcare","need",0.90, iso(9,0)),
 ("t10",user, "ext-1010","Uber Eats",       2299,"USD","Dining Out","want",0.80, iso(8,0)),
 ("t11",user, "ext-1011","Shell Gas",       4321,"USD","Transport","need",0.75, iso(12,0)),
 ("t12",user, "ext-1012","Kroger",          6789,"USD","Groceries","need",0.90, iso(13,0)),
]

cur.executemany("""
INSERT OR REPLACE INTO transactions
(id,user_id,transaction_id,merchant,amount_cents,currency,category,need_or_want,confidence,occurred_at)
VALUES (?,?,?,?,?,?,?,?,?,?)
""", tx_rows)

reply_rows = [
 ("r1","t1",user,"want", iso(1, -23.5)),  # 30 mins after t1
 ("r2","t3",user,"want", iso(3, -23.75)),
]
cur.executemany("""
INSERT OR REPLACE INTO user_replies
(id,transaction_id,user_id,user_label,received_at) VALUES (?,?,?,?,?)
""", reply_rows)

pred_rows = [
 ("p1",user,"Coffee", iso(0,2), iso(0,-10), 0.72, 180.0),
 ("p2",user,"Dining Out", iso(0,0), iso(-7,0), 0.41, 520.0),
]
cur.executemany("""
INSERT OR REPLACE INTO predictions
(id,user_id,category,window_start,window_end,probability,annual_savings_hint_usd)
VALUES (?,?,?,?,?,?,?)
""", pred_rows)

conn.commit()
conn.close()
print("Seeded local.db ✅")