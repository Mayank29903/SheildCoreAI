# SportShield AI - Google Solution Challenge 2026 🛡️

**SportShield AI** is a real-time sports media rights intelligence platform targeting the Google Solution Challenge 2026. It protects intellectual property for sports organizations and athletes through cryptographic digital watermarking, real-time web scraping, generative AI forensics, and immutable blockchain-like ledger storage securely utilizing Google Firebase.

This guide is written specifically to teach you **step-by-step** how the application gets built, configured, and deployed. Learn each part so you can maintain it yourself!

---

## 📚 Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Step 1: Setting up Firebase & Google Cloud](#step-1-setting-up-firebase--google-cloud)
3. [Step 2: Connecting the Backend](#step-2-connecting-the-backend)
4. [Step 3: Connecting the Frontend](#step-3-connecting-the-frontend)
5. [Step 4: Running the Demo locally](#step-4-running-the-demo-locally)
6. [Pre-Flight and Demo Scripts](#pre-flight-and-demo-scripts)

---

## 🏗️ Architecture Overview

The platform uses a decoupled frontend/backend architecture ensuring high scalability:

- **Frontend:** React 18, Vite, Tailwind v4 (CSS Native Variables), and Framer Motion for animations. It communicates with Firebase directly for auth and live database feeds to get under 100ms lag.
- **Backend:** FastAPI (Python), orchestrated alongside deep learning models (HuggingFace Deepfake detector, Gemini 2.0 Flash vision, pHash perception, Steganography).
- **Core Strategy:** The backend performs heavy AI manipulation and data checks, while Firebase Realtime DB triggers instantaneous UI flashes on the frontend without needing polling calls.

---

## 🚀 Step 1: Setting up Firebase & Google Cloud
*Why? You need a database to store ownership certificates, images, and user authentication!*

### Firebase Setup
1. Go to the [Firebase Console](https://console.firebase.google.com/) and create a new project.
2. Select **Start in Production Mode** for Firestore, and locate your region (e.g. `us-central1`).
3. Set up **Realtime Database** in Test Mode.
4. Set up **Storage** in Production Mode.
5. In **Authentication**, enable the "Google" Provider.

### Getting the "Secret Keys"
To connect your backend securely to Firebase, you need a Service Account Key.
1. Go to **Project Settings** > **Service Accounts**.
2. Click **Generate New Private Key**. This downloads a `.json` file.
3. Keep this safe! Place it in your backend folder and rename it to `serviceAccountKey.json`.
4. Run `base64 -w 0 serviceAccountKey.json > base64.txt` (Linux/WSL) or `certutil -encode serviceAccountKey.json tmp.b64` (Windows) to encode it if you decide to deploy to Cloud Run!

### Google Cloud APIs
1. Go to the GCP Console and search for **Gemini API**. Get a free Gemini 2.0 Flash API key.
2. Search for the **Programmable Search Engine** (CSE) to allow web crawling.
3. Save these keys for your `.env` configuration!

---

## 🛠️ Step 2: Connecting the Backend
*Why? The backend is where all the forensic AI checks happen.*

1. Open your terminal and navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Create your local environment setup:
   Copy `.env.example` into a new file called `.env`.
   Fill out the `GEMINI_API_KEY`, `FIREBASE_PROJECT_ID`, and path to your `FIREBASE_CREDENTIALS_JSON`.
3. Install dependencies using Python:
   ```bash
   pip install -r requirements.txt
   ```
4. Run your development server:
   ```bash
   python main.py
   ```
   *Your server is now active on `http://localhost:8000`*

---

## 💻 Step 3: Connecting the Frontend
*Why? The frontend is what the judges will see!*

1. Open a new terminal and navigate to the frontend folder:
   ```bash
   cd frontend
   ```
2. Create your frontend `.env`:
   Copy `.env.example` to `.env`.
   Go back to Firebase Settings -> General -> Add Web App. Copy the `firebaseConfig` keys they give you into your `.env` file!
3. Install UI packages and modules:
   ```bash
   npm install
   ```
4. Start your local React application:
   ```bash
   npm run dev
   ```

---

## 🎭 Step 4: Running the Demo locally

Once both are running, open your browser to `http://localhost:5173`.
Start the flow:
1. Click **Authenticate Operator**. This connects you with Google Firebase.
2. You will be redirected to the **Dashboard** which serves as Mission Control.
3. Go to **Register Asset** to upload a legitimate sports image (Must be a PNG!). This writes the LSB watermark into the deepest layers of the pixels!
4. Go to **Scan Content** and upload a cropped version of that image. Watch the radar tick as it pulls the watermark and verifies EXIF manipulations.

---

## 📋 Pre-Flight and Demo Scripts
Before stepping on stage, test the forensic pipeline locally.
Open the command line to verify your Python environment holds the Steganography weights:

**Watermark Survival Test:**
```python
from stegano import lsb; from PIL import Image; import json
img = Image.new('RGB',(200,200),'navy'); img.save('test.png')
secret = lsb.hide('test.png', json.dumps({'cert_id':'TEST1234'}))
secret.save('test_wm.png')
print('WATERMARK:', json.loads(lsb.reveal('test_wm.png')))
```

### ✨ Good luck building and presenting! 
If you encounter errors like `React.Suspense` crashing, ensure your React version is strictly `^18.3.0` and that all your Firebase config variables are properly filled out!
