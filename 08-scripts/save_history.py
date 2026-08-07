import csv
from datetime import datetime

business_name = input("Business Name: ")
business_type = input("Business Type: ")
location = input("Location: ")

with open("09-history/history.csv", "a", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)

    writer.writerow([
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        business_name,
        business_type,
        location,
        "SUCCESS"
    ])

print("✅ History Saved")