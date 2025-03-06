import requests
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Admin SDK
cred = credentials.Certificate("nutro-chi-firebase-adminsdk-7ejyw-6911fcc0b0.json")  # Replace with your JSON key file
firebase_admin.initialize_app(cred)

db = firestore.client()

# USDA API Details
USDA_API_KEY = "API_KEY"
USDA_URL = "https://api.nal.usda.gov/fdc/v1/foods/list"

# Fetch data from USDA API
def fetch_usda_data():
    params = {
        "api_key": USDA_API_KEY,
    }
    response = requests.get(USDA_URL, params=params)

    if response.status_code == 200:
        return response.json()  # Returns a list of food items
    else:
        print("Error fetching USDA data:", response.status_code, response.text)
        return []

# Transform USDA API data into Firestore format
def transform_food_data(food):
    return {
        "fdcId": food.get("fdcId"),
        "description": food.get("description"),
        "availableDate": food.get("availableDate"),
        "brandOwner": food.get("brandOwner"),
        "brandedFoodCategory": food.get("brandedFoodCategory"),
        "dataSource": food.get("dataSource"),
        "dataType": food.get("dataType"),
        "foodClass": food.get("foodClass"),
        "foodNutrients": [
            {
                "amount": nutrient.get("amount"),
                "nutrient": {
                    "id": nutrient.get("nutrient", {}).get("id"),
                    "name": nutrient.get("nutrient", {}).get("name"),
                    "number": nutrient.get("nutrient", {}).get("number"),
                    "rank": nutrient.get("nutrient", {}).get("rank"),
                    "unitName": nutrient.get("nutrient", {}).get("unitName"),
                    "type": nutrient.get("nutrient", {}).get("type"),
                },
            }
            for nutrient in food.get("foodNutrients", [])
        ],
        "nutrientValues": {
            "carbohydrates": {"unit": "g", "value": food.get("carbohydrates", {}).get("value", 0)},
            "fat": {"unit": "g", "value": food.get("fat", {}).get("value", 0)},
            "fiber": {"unit": "g", "value": food.get("fiber", {}).get("value", 0)},
            "protein": {"unit": "g", "value": food.get("protein", {}).get("value", 0)},
            "sodium": {"unit": "mg", "value": food.get("sodium", {}).get("value", 0)},
            "sugar": {"unit": "g", "value": food.get("sugar", {}).get("value", 0)},
        },
        "servingSize": {"unit": "g", "value": food.get("servingSize", 0)},
        "marketCountry": food.get("marketCountry", "Unknown"),
    }

# Upload transformed food data to Firestore
def upload_to_firestore(food_data):
    try:
        doc_ref = db.collection("pura_data_pipeline").add(food_data)
        print("Document added with ID:", doc_ref[1].id)
    except Exception as e:
        print("Error adding document:", e)

# Main function to execute the pipeline
def main():
    food_list = fetch_usda_data()
    if not food_list:
        print("No data retrieved from USDA API.")
        return

    for food in food_list[:10]:  # Limiting to first 10 items for testing
        food_data = transform_food_data(food)
        upload_to_firestore(food_data)

# Run the script
if __name__ == "__main__":
    main()
