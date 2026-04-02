from datetime import date
from django.core.management.base import BaseCommand
from salesforce_sim.models import SFCoach, SFAccount, SFContact, SFAssignment


class Command(BaseCommand):
    help = "Seed the simulated Salesforce database with test data"

    def handle(self, *args, **options):
        # Clear existing data
        SFAssignment.objects.using("salesforce").all().delete()
        SFContact.objects.using("salesforce").all().delete()
        SFAccount.objects.using("salesforce").all().delete()
        SFCoach.objects.using("salesforce").all().delete()

        # 5 Coaches
        arjun = SFCoach.objects.using("salesforce").create(
            name="Arjun Mehta", email="arjun@coaching.com",
            active_clients=8, is_active=True
        )
        deepa = SFCoach.objects.using("salesforce").create(
            name="Deepa Nair", email="deepa@coaching.com",
            active_clients=6, is_active=True
        )
        karthik = SFCoach.objects.using("salesforce").create(
            name="Karthik Rajan", email="karthik@coaching.com",
            active_clients=4, is_active=True
        )
        sneha = SFCoach.objects.using("salesforce").create(
            name="Sneha Iyer", email="sneha@coaching.com",
            active_clients=2, is_active=True
        )
        vikram = SFCoach.objects.using("salesforce").create(
            name="Vikram Desai", email="vikram@coaching.com",
            active_clients=0, is_active=True
        )

        # 10 Accounts — distributed: Arjun=4, Deepa=3, Karthik=2, Sneha=1
        accounts_data = [
            ("TechCorp", "Technology", "https://techcorp.com", "2024-01-15", arjun),
            ("HealthPlus", "Healthcare", "https://healthplus.com", "2024-03-01", arjun),
            ("FinanceHub", "Finance", "https://financehub.com", "2024-06-15", arjun),
            ("ManuPro", "Manufacturing", "https://manupro.com", "2024-02-20", arjun),
            ("CloudNine", "Technology", "https://cloudnine.io", "2024-04-10", deepa),
            ("DataWorks", "Technology", "https://dataworks.com", "2024-05-01", deepa),
            ("GreenEnergy", "Energy", "https://greenenergy.com", "2024-07-12", deepa),
            ("RetailMax", "Retail", "https://retailmax.com", "2024-08-05", karthik),
            ("BuildRight", "Construction", "https://buildright.com", "2024-09-18", karthik),
            ("AutoDrive", "Automotive", "https://autodrive.com", "2024-10-01", sneha),
        ]

        accounts = {}
        for name, industry, website, start, coach in accounts_data:
            acc = SFAccount.objects.using("salesforce").create(
                name=name, industry=industry, website=website,
                coaching_start_date=date.fromisoformat(start),
                assigned_coach=coach.name, coach=coach
            )
            accounts[name] = acc

        # 20 Contacts — 2 per account
        contacts_data = [
            ("Rajesh Kumar", "CEO", "rajesh@techcorp.com", "555-0101", "TechCorp", arjun),
            ("Ananya Sharma", "VP Engineering", "ananya@techcorp.com", "555-0102", "TechCorp", arjun),
            ("Suresh Pillai", "Director HR", "suresh@healthplus.com", "555-0201", "HealthPlus", arjun),
            ("Kavitha Menon", "CTO", "kavitha@healthplus.com", "555-0202", "HealthPlus", arjun),
            ("Arun Prasad", "CFO", "arun@financehub.com", "555-0301", "FinanceHub", arjun),
            ("Meena Krishnan", "COO", "meena@financehub.com", "555-0302", "FinanceHub", arjun),
            ("Ganesh Venkat", "VP Operations", "ganesh@manupro.com", "555-0401", "ManuPro", arjun),
            ("Priya Reddy", "Lead Engineer", "priya@manupro.com", "555-0402", "ManuPro", arjun),
            ("Siddharth Joshi", "CEO", "siddharth@cloudnine.io", "555-0501", "CloudNine", deepa),
            ("Lakshmi Bhat", "CTO", "lakshmi@cloudnine.io", "555-0502", "CloudNine", deepa),
            ("Rohit Saxena", "VP Engineering", "rohit@dataworks.com", "555-0601", "DataWorks", deepa),
            ("Divya Gupta", "Product Manager", "divya@dataworks.com", "555-0602", "DataWorks", deepa),
            ("Manish Tiwari", "Director of Ops", "manish@greenenergy.com", "555-0701", "GreenEnergy", deepa),
            ("Pooja Agarwal", "Team Lead", "pooja@greenenergy.com", "555-0702", "GreenEnergy", deepa),
            ("Nandini Rao", "CEO", "nandini@retailmax.com", "555-0801", "RetailMax", karthik),
            ("Harish Srinivasan", "CFO", "harish@retailmax.com", "555-0802", "RetailMax", karthik),
            ("Revathi Subramanian", "VP Sales", "revathi@buildright.com", "555-0901", "BuildRight", karthik),
            ("Vivek Choudhary", "Director of Projects", "vivek@buildright.com", "555-0902", "BuildRight", karthik),
            ("Amit Patel", "CEO", "amit@autodrive.com", "555-1001", "AutoDrive", sneha),
            ("Neha Banerjee", "CTO", "neha@autodrive.com", "555-1002", "AutoDrive", sneha),
        ]

        contacts = {}
        for name, title, email, phone, acc_name, coach in contacts_data:
            contact = SFContact.objects.using("salesforce").create(
                name=name, title=title, email=email, phone=phone,
                assigned_coach=coach.name, account=accounts[acc_name], coach=coach
            )
            contacts[name] = contact

        # Create assignments for all active coach-contact pairs
        for name, contact in contacts.items():
            SFAssignment.objects.using("salesforce").create(
                coach=contact.coach,
                contact=contact,
                account=contact.account,
                status="active"
            )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded: {SFCoach.objects.using('salesforce').count()} coaches, "
            f"{SFAccount.objects.using('salesforce').count()} accounts, "
            f"{SFContact.objects.using('salesforce').count()} contacts, "
            f"{SFAssignment.objects.using('salesforce').count()} assignments"
        ))
