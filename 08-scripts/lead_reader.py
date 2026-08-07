import csv

def get_leads():

    leads = []

    with open(
        "05-leads/leads.csv",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            leads.append({
                "business_name": row["Business Name"],
                "business_type": row["Business Type"],
                "location": row["Location"],
                "website": row["Website"],
                "email": row["Email"],
                "status": row["Status"]
            })

    return leads


if __name__ == "__main__":

    leads = get_leads()

    print(f"\n✅ Total Leads Found : {len(leads)}")

    for lead in leads:

        print("\n-----------------------------")

        print("Business :", lead["business_name"])

        print("Type     :", lead["business_type"])

        print("Location :", lead["location"])

        print("Website  :", lead["website"])

        print("Email    :", lead["email"])

        print("Status   :", lead["status"])