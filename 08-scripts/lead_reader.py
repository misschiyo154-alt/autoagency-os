import csv

with open("05-leads/leads.csv", newline="", encoding="utf-8") as file:
    reader = csv.DictReader(file)

    for lead in reader:
        print("\n-------------------------")
        print("Business :", lead["Business Name"])
        print("Type     :", lead["Business Type"])
        print("Location :", lead["Location"])
        print("Website  :", lead["Website"])
        print("Email    :", lead["Email"])