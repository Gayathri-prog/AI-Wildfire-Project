import streamlit as st
import tensorflow as tf
import numpy as np
import json
import smtplib
import reverse_geocoder as rg
import folium
import random
import os
import math
import gtts
import base64
from googletrans import Translator
import pygame
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email import encoders
from tensorflow.keras.preprocessing import image
from geopy.distance import geodesic
from streamlit_folium import folium_static
import time

# Load the trained wildfire detection model
MODEL_PATH = "wildfire_model.h5"
USER_DB = "users.json"

if os.path.exists(MODEL_PATH):
    model = tf.keras.models.load_model(MODEL_PATH)
else:
    st.error("Wildfire detection model not found! Please check the file path.")

# Load users from database
def load_users():
    if os.path.exists(USER_DB):
        try:
            with open(USER_DB, "r") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}

def save_users(users):
    with open(USER_DB, "w") as f:
        json.dump(users, f, indent=4)

users = load_users()

# Translation dictionary for alert messages
ALERT_MESSAGES = {
    "en": {
        "subject": "🚨 Wildfire Alert!",
        "body": "A wildfire has been detected near your location. Please take necessary precautions.",
        "location": "Wildfire Location",
        "map_link": "View on Google Maps",
        "audio_text": "Warning! Wildfire detected in your area. Please evacuate to a safe location immediately."
    },
    "es": {
        "subject": "🚨 ¡Alerta de incendio forestal!",
        "body": "Se ha detectado un incendio forestal cerca de su ubicación. Por favor tome las precauciones necesarias.",
        "location": "Ubicación del incendio",
        "map_link": "Ver en Google Maps",
        "audio_text": "¡Advertencia! Incendio forestal detectado en su área. Por favor evacúe a un lugar seguro inmediatamente."
    },
    "fr": {
        "subject": "🚨 Alerte d'incendie de forêt !",
        "body": "Un incendie de forêt a été détecté près de votre emplacement. Veuillez prendre les précautions nécessaires.",
        "location": "Emplacement de l'incendie",
        "map_link": "Voir sur Google Maps",
        "audio_text": "Avertissement! Incendie de forêt détecté dans votre région. Veuillez évacuer vers un endroit sûr immédiatement."
    },
    "hi": {
        "subject": "🚨 जंगल की आग की चेतावनी!",
        "body": "आपके स्थान के निकट जंगल की आग का पता चला है। कृपया आवश्यक सावधानी बरतें।",
        "location": "जंगल की आग का स्थान",
        "map_link": "Google मानचित्र पर देखें",
        "audio_text": "चेतावनी! आपके क्षेत्र में जंगल की आग का पता चला है। कृपया तुरंत सुरक्षित स्थान पर निकल जाएं।"
    }
}

# Function to send email with audio attachment
def send_alert_email(user_email, wildfire_lat, wildfire_lon, language="en"):
    try:
        # Get user's location info
        user_location = rg.search((users[user_email]["lat"], users[user_email]["lon"]))[0]
        user_city = user_location.get("name", "your area")
        
        # Prepare email content
        msg = MIMEMultipart()
        msg["From"] = "dipenshuqriocity@gmail.com"  # Replace with your email
        msg["To"] = user_email
        msg["Subject"] = ALERT_MESSAGES[language]["subject"]
        
        # Create Google Maps link
        map_link = f"https://www.google.com/maps?q={wildfire_lat},{wildfire_lon}"
        
        # Email body
        body = f"""
        <html>
            <body>
                <h2>{ALERT_MESSAGES[language]["subject"]}</h2>
                <p>{ALERT_MESSAGES[language]["body"]}</p>
                <p><strong>{ALERT_MESSAGES[language]["location"]}:</strong> {wildfire_lat}, {wildfire_lon}</p>
                <p><a href="{map_link}">{ALERT_MESSAGES[language]["map_link"]}</a></p>
                <p>Please check the attached audio alert.</p>
            </body>
        </html>
        """
        msg.attach(MIMEText(body, "html"))
        
        # Create and attach audio alert
        tts = gtts.gTTS(ALERT_MESSAGES[language]["audio_text"], lang=language)
        audio_file = f"alert_{language}.mp3"
        tts.save(audio_file)
        
        with open(audio_file, "rb") as f:
            audio_part = MIMEAudio(f.read(), _subtype="mp3")
            audio_part.add_header("Content-Disposition", f"attachment; filename=alert_{language}.mp3")
            msg.attach(audio_part)
        
        # Send email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:  # Replace with your SMTP server
            server.starttls()
            server.login("dipenshuqriocity@gmail.com", "oqzg htxm nbbb pjuf")  # Replace with your credentials
            server.send_message(msg)
        
        os.remove(audio_file)
        return True
    except Exception as e:
        st.error(f"Error sending email: {str(e)}")
        return False

# Function to notify nearby users
def notify_nearby_users(wildfire_lat, wildfire_lon, radius_km=50):
    wildfire_location = (wildfire_lat, wildfire_lon)
    notified_users = []
    
    for email, user_data in users.items():
        user_location = (user_data["lat"], user_data["lon"])
        distance = geodesic(wildfire_location, user_location).km
        
        if distance <= radius_km:
            if send_alert_email(email, wildfire_lat, wildfire_lon, user_data["language"]):
                notified_users.append(email)
    
    return notified_users

# UI Styling
st.set_page_config(page_title="Wildfire Detection & Alert System", layout="wide")
st.markdown(
    """
    <style>
    body {
        background-color: #f5f5f5;
        color: #333333;
        font-family: Arial, sans-serif;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        padding: 10px;
    }
    .stTextInput, .stNumberInput {
        border-radius: 5px;
        border: 1px solid #cccccc;
        padding: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

css = """
<style>
/* Global Styles */
body {
    background-color: #2f2f2f; /* Darker background for better contrast */
    color: #e0e0e0; /* Light gray text for better readability */
    font-family: 'Helvetica Neue', Arial, sans-serif; /* Modern font */
    margin: 0;
    padding: 0;
}

.stApp {
    background-color: #2f2f2f; /* Darker background for the app */
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background-color: #353535; /* Slightly lighter dark gray for sidebar */
    border-right: 1px solid #444444; /* Darker border to separate sidebar */
}

.stSidebar .stTitle {
    font-size: 1.5rem; /* Sidebar title */
    font-weight: 600;
    color: #ffffff; /* White text for the title */
    margin-bottom: 20px;
}

/* Sidebar elements */
.stSidebar input[type="text"], .stSidebar input[type="number"], .stSidebar select {
    background-color: #555555; /* Dark background for input fields */
    border: 1px solid #777777; /* Slightly lighter border */
    border-radius: 8px;
    padding: 10px;
    margin: 10px 0;
    width: 100%;
    font-size: 1rem;
    color: #e0e0e0; /* Light gray text for inputs */
}

.stSidebar button {
    background-color: #4CAF50; /* Green for action buttons */
    color: white;
    border-radius: 8px;
    padding: 12px 20px;
    border: none;
    width: 100%;
    font-size: 1rem;
    cursor: pointer;
}

.stSidebar button:hover {
    background-color: #45a049;
}

/* Main container */
.stMain {
    background-color: #3b3b3b; /* Dark gray for the main container */
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3); /* Subtle shadow around the main container */
    margin-top: 20px;
}

/* Heading and Text styling */
h1, h2, h3 {
    color: #ffffff; /* White text for headings */
}

h2 {
    font-weight: bold;
}

/* Buttons and links */
.stButton>button {
    background-color: #007BFF; /* Blue button for primary actions */
    color: white;
    border-radius: 8px;
    padding: 10px;
    border: none;
    cursor: pointer;
    font-size: 1rem;
}

.stButton>button:hover {
    background-color: #0056b3; /* Darker blue on hover */
}

/* Alerts and Success Messages */
.stSuccess, .stInfo, .stError {
    border-radius: 8px;
    padding: 10px;
    margin-top: 10px;
}

.stSuccess {
    background-color: #d4edda; /* Light green for success */
    color: #155724; /* Dark green text */
}

.stInfo {
    background-color: #cce5ff; /* Light blue for informational messages */
    color: #004085; /* Dark blue text */
}

.stError {
    background-color: #f8d7da; /* Light red for error messages */
    color: #721c24; /* Dark red text */
}

/* Input fields */
.stTextInput, .stNumberInput {
    background-color: #555555; /* Dark background for input fields */
    border: 1px solid #777777; /* Lighter border */
    border-radius: 8px;
    padding: 10px;
    font-size: 1rem;
    width: 100%;
    margin-bottom: 10px;
    color: #e0e0e0; /* Light gray text for input fields */
}

/* Maps */
.stMap {
    margin-top: 20px;
    margin-bottom: 20px;
}

/* Footer */
footer {
    background-color: #353535; /* Dark gray footer */
    text-align: center;
    padding: 10px;
    font-size: 0.85rem;
    color: #999999; /* Light gray text for footer */
}

footer a {
    color: #007bff;
    text-decoration: none;
}

footer a:hover {
    text-decoration: underline;
}
</style>
"""
st.markdown(css, unsafe_allow_html = True)
st.title("🔥 Wildfire Detection & Alert System")
st.markdown("Detect and receive alerts about wildfires with AI-powered image analysis.")

# Sidebar for user input
st.sidebar.header("User Input")
lat = st.sidebar.number_input("Enter Latitude", value=20.0, min_value=-90.0, max_value=90.0, format="%.6f")
lon = st.sidebar.number_input("Enter Longitude", value=80.0, min_value=-180.0, max_value=180.0, format="%.6f")
uploaded_file = st.sidebar.file_uploader("Upload Satellite Image", type=["jpg", "png"])
language = st.sidebar.selectbox("Preferred Language", ["English", "Spanish", "French", "Hindi"], key='user')
languages = {"English":"en", "Spanish":"es", "French":"fr", "Hindi":"hi"}
language = languages.get(language)
if st.sidebar.button("Detect Wildfire"):
    if uploaded_file:
        img_path = "temp.jpg"
        with open(img_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Prediction
        img = image.load_img(img_path, target_size=(150, 150))
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0) / 255.0
        prediction = model.predict(img_array)
        result = "Wildfire Detected" if prediction[0][0] > 0.5 else "No Wildfire"

        st.subheader(f"🚨 Detection Result: {result}")

        if result == "Wildfire Detected":
            # Generate a safe location
            random_angle = random.uniform(0, 360)
            distance_km = 5
            angle_rad = math.radians(random_angle)
            delta_lat = distance_km / 111
            delta_lon = distance_km / (111 * math.cos(math.radians(lat)))
            safe_lat = lat + delta_lat * math.sin(angle_rad)
            safe_lon = lon + delta_lon * math.cos(angle_rad)

            st.success(f"Safe Location: {safe_lat}, {safe_lon}")
            google_maps_url = f"https://www.google.com/maps?q={safe_lat},{safe_lon}"
            st.markdown(f"[🔗 View Safe Location on Google Maps]({google_maps_url})")

            # Display map
            map = folium.Map(location=[lat, lon], zoom_start=10)
            folium.Marker([lat, lon], tooltip="Wildfire Location", icon=folium.Icon(color="red")).add_to(map)
            folium.Marker([safe_lat, safe_lon], tooltip="Safe Location", icon=folium.Icon(color="green")).add_to(map)
            st.subheader("📍 Safe Route")
            folium_static(map)
            
            tts = gtts.gTTS(ALERT_MESSAGES[language]["audio_text"], lang=language)
            audio_file = f"alert_{language}.mp3"
            tts.save(audio_file)
            pygame.mixer.init()
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            os.remove(audio_file)
            notified_users = notify_nearby_users(lat, lon)
            if notified_users:
                st.success(f"Alerts sent to {len(notified_users)} users in the affected area.")
            else:
                st.info("No registered users in the affected area.")
        else:
            st.success("No wildfire detected.")
    else:
        st.error("Please upload an image for wildfire detection.")

# Admin Panel for User Registration
st.sidebar.header("🔹 Register for Alerts")
email = st.sidebar.text_input("Email")
user_lat = st.sidebar.number_input("User Latitude", value=0.0, format="%.6f")
user_lon = st.sidebar.number_input("User Longitude", value=0.0, format="%.6f")
language = st.sidebar.selectbox("Preferred Language", ["English", "Spanish", "French", "Hindi"], key='Register')
languages = {"English":"en", "Spanish":"es", "French":"fr", "Hindi":"hi"}
language = languages.get(language)

if st.sidebar.button("Register User"):
    if email:
        users[email] = {"email": email, "lat": user_lat, "lon": user_lon, "language": language}
        save_users(users)
        st.sidebar.success("User registered successfully!")
    else:
        st.sidebar.error("Please enter a valid email.")