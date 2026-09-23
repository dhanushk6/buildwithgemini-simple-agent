import subprocess
from google.cloud import firestore
from google.oauth2.credentials import Credentials

PROJECT_ID = "qwiklabs-gcp-03-90af3d54a148"


def get_firestore_client() -> firestore.Client:
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-access-token"], text=True
        ).strip()
        if token:
            creds = Credentials(token)
            return firestore.Client(project=PROJECT_ID, credentials=creds)
    except Exception:
        pass
    return firestore.Client(project=PROJECT_ID)


db = get_firestore_client()

seed_items = [
    {
        "id": "item-1",
        "item_name": "Organic Milk",
        "category": "dairy",
        "quantity": "1 gallon",
        "expiration_date": "2026-09-30",
        "allergens": ["dairy"],
    },
    {
        "id": "item-2",
        "item_name": "Rolled Oats",
        "category": "pantry",
        "quantity": "2 lbs",
        "expiration_date": "2026-12-15",
        "allergens": [],
    },
    {
        "id": "item-3",
        "item_name": "Fresh Spinach",
        "category": "produce",
        "quantity": "1 bag",
        "expiration_date": "2026-09-28",
        "allergens": [],
    },
    {
        "id": "item-4",
        "item_name": "Almond Butter",
        "category": "pantry",
        "quantity": "1 jar",
        "expiration_date": "2026-11-20",
        "allergens": ["tree_nuts"],
    },
    {
        "id": "item-5",
        "item_name": "Chicken Breast",
        "category": "protein",
        "quantity": "1.5 lbs",
        "expiration_date": "2026-09-26",
        "allergens": [],
    },
]


def seed():
    print(f"Seeding Firestore collection 'pantry_items' in project '{PROJECT_ID}'...")
    collection_ref = db.collection("pantry_items")
    for item in seed_items:
        doc_ref = collection_ref.document(item["id"])
        doc_ref.set(item)
        print(f"Seeded document: {item['id']} -> {item['item_name']}")
    print("Seeding completed successfully!")


if __name__ == "__main__":
    seed()
