import os
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify
import json
import time

# Initialize Flask App
app = Flask(__name__)

# Load Firebase credentials securely from Google Secret Manager
from google.cloud import secretmanager

client = secretmanager.SecretManagerServiceClient()
secret_name = "projects/pura-452821/secrets/firebase-admin-sdk/versions/latest"
response = client.access_secret_version(request={"name": secret_name})
firebase_creds = json.loads(response.payload.data.decode("UTF-8"))

# Initialize Firebase Admin SDK
cred = credentials.Certificate(firebase_creds)
firebase_admin.initialize_app(cred)
db = firestore.client()

# USDA & Open Food Facts API Details
USDA_API_KEY = "API_KEY"
USDA_LIST_URL = "https://api.nal.usda.gov/fdc/v1/foods/list"
USDA_BULK_URL = "https://api.nal.usda.gov/fdc/v1/foods"
OFF_API_URL = "https://world.openfoodfacts.org/api/v2/product/"

### 🔥 Function: Check Firestore Before Adding
def is_fdcid_in_firestore(fdc_id):
    doc_ref = db.collection("pura_data_pipeline").document(str(fdc_id)).get()
    return doc_ref.exists

### 🔥 Function: Query Firestore for Barcode
def query_firestore_barcode(barcode):
    docs = db.collection("pura_data_pipeline").where("barcode", "==", barcode).stream()
    for doc in docs:
        return doc.to_dict()
    return None

### 🔥 Function: Fetch USDA Food Data (Bulk)
def fetch_usda_data(page_size=100, page_number=1):
    params = {
        "api_key": USDA_API_KEY,
        "pageSize": page_size,
        "pageNumber": page_number,
        "dataType": ["Branded"]
    }
    response = requests.get(USDA_LIST_URL, params=params)
    return response.json() if response.status_code == 200 else []

### 🔥 Function: Fetch USDA Bulk Details
def fetch_usda_details_bulk(fdc_ids):
    params = {"api_key": USDA_API_KEY}
    payload = {"fdcIds": fdc_ids}
    response = requests.post(USDA_BULK_URL, params=params, json=payload)
    return response.json() if response.status_code == 200 else []

### 🔥 Function: Fetch Open Food Facts (OFF) Data
def fetch_off_data(barcode):
    response = requests.get(f"{OFF_API_URL}{barcode}.json")
    if response.status_code == 200:
        product = response.json().get("product")
        if product:
            return {
                "fdcId": f"OFF_{product['code']}",
                "description": product.get("product_name", ""),
                "brandOwner": product.get("brands", ""),
                "barcode": product["code"],
                "source": "OFF",
                "ingredients": product.get("ingredients_text", ""),
                "foodNutrients": product.get("nutriments", {})
            }
    return None

### 🔥 Function: Transform Food Data for Firestore
def transform_food_data(food, source="USDA"):
    if source == "USDA":
        return {
            "fdcId": food.get("fdcId"),
            "description": food.get("description"),
            "brandOwner": food.get("brandOwner"),
            "barcode": food.get("gtinUpc", ""),
            "source": "USDA",
            "ingredients": food.get("ingredients", ""),
            "foodNutrients": food.get("foodNutrients", [])
        }
    else:  # OFF
        nutriments = food.get("nutriments", {})
        return {
            "fdcId": f"OFF_{food.get('code')}",
            "description": food.get("product_name"),
            "brandOwner": food.get("brands"),
            "barcode": food.get("code"),
            "source": "OFF",
            "ingredients": food.get("ingredients_text", ""),
            "foodNutrients": [{ "name": key, "amount": value } for key, value in nutriments.items() if isinstance(value, (int, float))]
        }

### 🔥 Function: Batch Upload to Firestore
def upload_batch_to_firestore(food_items):
    batch = db.batch()
    for food_data in food_items:
        doc_id = str(food_data["fdcId"])
        doc_ref = db.collection("pura_data_pipeline").document(doc_id)
        batch.set(doc_ref, food_data)
    batch.commit()
    print(f"✅ Batch upload completed - {len(food_items)} items added.")

### 🔥 Cloud Function: USDA + OFF Ingestion
@app.route("/", methods=["POST"])
def usda_off_ingestion():
    total_ingested = 0
    max_pages = 10  # Adjust as needed for testing (e.g., 4000 for all)

    for page in range(1, max_pages + 1):
        usda_food_list = fetch_usda_data(page_size=100, page_number=page)
        if not usda_food_list:
            break

        usda_fdc_ids = [food.get("fdcId") for food in usda_food_list if food.get("fdcId")]
        if usda_fdc_ids:
            usda_detailed_foods = fetch_usda_details_bulk(usda_fdc_ids)
            new_foods = [food for food in usda_detailed_foods if not is_fdcid_in_firestore(food.get("fdcId"))]
            valid_foods = [transform_food_data(food, "USDA") for food in new_foods]
            if valid_foods:
                upload_batch_to_firestore(valid_foods)
                total_ingested += len(valid_foods)

    return jsonify({"status": "success", "message": f"USDA ingestion completed. {total_ingested} items added."})

### 🔥 Cloud Function: Barcode Lookup
@app.route("/lookup", methods=["POST"])
def lookup_food():
    data = request.get_json()
    barcode = data.get("barcode")
    
    if not barcode:
        return jsonify({"error": "Missing barcode"}), 400

    # 1️⃣ Check Firestore
    food_item = query_firestore_barcode(barcode)
    if food_item:
        return jsonify(food_item)

    # 2️⃣ Query USDA API
    food_item = fetch_usda_data(barcode)
    if food_item:
        db.collection("pura_data_pipeline").document(str(food_item["fdcId"])).set(food_item)
        return jsonify(food_item)

    # 3️⃣ Query Open Food Facts (OFF)
    food_item = fetch_off_data(barcode)
    if food_item:
        db.collection("pura_data_pipeline").document(str(food_item["fdcId"])).set(food_item)
        return jsonify(food_item)

    return jsonify({"error": "Food item not found"}), 404

# Start Flask App (For local testing)
def cloud_function_handler(request):
    return usda_off_ingestion()