# USDA Data Ingestion Pipeline with Google Cloud Functions & Firestore

## Overview
This project automates the ingestion of food data from USDA into Google Firestore using Google Cloud Functions and Cloud Scheduler.

## Features
- **Fetch USDA food data** in batches and store in Firestore.
- **Track last fetched page** in Firestore to avoid duplicate data.
- **Automatically update database** every 5 minutes using Google Cloud Scheduler.
- **Standardize food data** and ensure completeness.
- **Handles 400K+ items** efficiently with batch operations.

---

## **1️⃣ Setup Google Cloud Project**
### **Create a New Google Cloud Project**
```sh
gcloud projects create my-usda-project
```

### **Set the Active Project**
```sh
gcloud config set project my-usda-project
```

### **Enable Required Services**
```sh
gcloud services enable \
    cloudfunctions.googleapis.com \
    firestore.googleapis.com \
    cloudscheduler.googleapis.com \
    secretmanager.googleapis.com \
    pubsub.googleapis.com \
    run.googleapis.com
```

---

## **2️⃣ Setup Firestore Database**
1. **Go to Firebase Console:** [Firebase Firestore](https://console.firebase.google.com/)
2. **Create Firestore Database:** Select "Native Mode"
3. **Create a collection:** `usda_data` (for food items)
4. **Create another collection:** `usda_metadata` (for tracking last fetched page)

---

## **3️⃣ Store Firebase Credentials Securely**
### **Create a Secret in Google Secret Manager**
```sh
gcloud secrets create firebase-admin-sdk --replication-policy="automatic"
```

### **Upload Firebase Credentials**
```sh
gcloud secrets versions add firebase-admin-sdk --data-file=firebase-admin-sdk.json
```

---

## **4️⃣ Deploy Cloud Function**
### **Clone This Repository**

### **Deploy the Cloud Function**
```sh
gcloud functions deploy usda_data_ingestion \
    --runtime python310 \
    --gen2 \
    --trigger-http \
    --allow-unauthenticated \
    --service-account=my-usda-project@appspot.gserviceaccount.com \
    --entry-point=cloud_function_handler \
    --region us-central1 \
    --source . \
    --timeout=540
```

---

## **5️⃣ Schedule Data Sync Every 5 Minutes**
### **Create Cloud Scheduler Job**
```sh
gcloud scheduler jobs create http usda-scheduler \
    --schedule "every 5 minutes" \
    --time-zone "America/Chicago" \
    --uri "https://us-central1-my-usda-project.cloudfunctions.net/usda_data_ingestion" \
    --http-method POST \
    --location us-central1 \
    --oidc-service-account-email=my-usda-project@appspot.gserviceaccount.com
```

---

## **6️⃣ Testing & Debugging**
### **Run Locally**
```sh
python main.py
```

### **Manually Trigger Cloud Function**
```sh
curl -X POST https://us-central1-my-usda-project.cloudfunctions.net/usda_data_ingestion
```

### **Check Firestore Count**
```sh
gcloud firestore indexes composite list
```

---

## **7️⃣ Monitoring & Logs**
### **View Logs in Google Cloud Console**
[Cloud Logs](https://console.cloud.google.com/logs/query)

### **Check Firestore Data**
[Firestore Console](https://console.firebase.google.com/)

---

## **🚀 Why This Works**
✅ **Tracks last fetched page** & resumes from there  
✅ **Prevents duplicate ingestion**  
✅ **Handles pagination efficiently**  
✅ **Scales to process 400K+ items**  
✅ **Automates data sync every 5 minutes**  

Would you like to add **error handling & retries** for failed requests? 🚀🔥

