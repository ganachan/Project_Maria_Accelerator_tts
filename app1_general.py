import streamlit as st
import json
import logging
import os
import sys
import time
import uuid
import requests
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta, timezone
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Accessing environment variables
SPEECH_ENDPOINT = os.getenv("SPEECH_ENDPOINT")
SUBSCRIPTION_KEY = os.getenv("SUBSCRIPTION_KEY")
BLOB_CONNECTION_STRING = os.getenv("BLOB_CONNECTION_STRING")
BLOB_CONTAINER_NAME = os.getenv("BLOB_CONTAINER_NAME")
API_VERSION = os.getenv("API_VERSION")
BACKGROUND_IMAGE_URL = os.getenv("BACKGROUND_IMAGE_URL")

# Set up the page configuration
st.set_page_config(page_title="Azure AI Text-to-Speech Avatar", layout="wide")

# Custom CSS to apply background color and styles
st.markdown(
    """
    <style>
    .stApp {
        background-color: #E5F8FF;
        background-image: linear-gradient(to right, #B2FFEC, #D9F4FF);
    }
    .stTextInput>div>div>input {
        background-color: #FFFFFF;
        color: #000000;
    }
    h1 {
        font-size: 2em; /* Adjust font size for the headline */
        line-height: 1.2; /* Adjust line height for better spacing */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Adjust the headline
st.title("Elevate Your Sales Pitch: Create Personalized AI-Driven Videos with the Help of Maria, Your AI GBB Agent")
st.write("Create and download videos using your custom avatars and neural voices.")

# Input fields on the left side
with st.sidebar:
    st.header("User Information")
    username = st.text_input("Username", value="")
    industry_vertical = st.selectbox("Industry Vertical", ["education", "healthcare", "manufacturing", "telecom", "sdp", "finance", "other"])
    customer_name = st.text_input("Customer Name", value="")
    date = st.date_input("Date", value=datetime.now().date())

if username and industry_vertical and customer_name:
    default_input_text = (
        f"Welcome {customer_name}! I'm Maria, your AI partner from the Global Black Belt AI Team at Microsoft. "
        "We're thrilled that you've chosen to explore AI solutions with us. Our team is eager to collaborate with you to build cutting-edge AI solutions using Microsoft Azure AI services, along with our trusted partners. "
        "Let's embark on this journey together and transform your business with the power of AI. This personalized avatar is here to assist you and provide all the information you need."
    )
else:
    default_input_text = "Hi, I'm Maria, your AI partner from the Global Black Belt AI Team at Microsoft."

# Input field for Text to Speech
st.subheader("Input Text (Text to Speech)")
input_text = st.text_area("Input Text", value=default_input_text)

blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)

if 'video_history' not in st.session_state:
    st.session_state['video_history'] = []

def _create_job_id():
    return str(uuid.uuid4())

def _authenticate(subscription_key):
    return {'Ocp-Apim-Subscription-Key': subscription_key}

def check_existing_files(username, industry_vertical, customer_name, file_type):
    file_prefix = f"{username}_{industry_vertical}_{customer_name}_Maria_{file_type}"
    existing_files = container_client.list_blobs(name_starts_with=file_prefix)
    count = 1
    for blob in existing_files:
        blob_name = blob.name
        parts = blob_name.split("_")
        if len(parts) >= 4 and parts[-1].startswith(file_type):
            number_part = parts[-1].replace(file_type, "").replace(".mp4", "").replace(".webm", "").replace(".txt", "")
            try:
                number = int(number_part)
                if number >= count:
                    count = number + 1
            except ValueError:
                continue
    return count

def generate_sas_token(blob_name):
    sas_token = generate_blob_sas(
        account_name=blob_service_client.account_name,
        container_name=BLOB_CONTAINER_NAME,
        blob_name=blob_name,
        account_key=blob_service_client.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    return sas_token

def submit_synthesis(job_id: str, input_text: str):
    url = f'{SPEECH_ENDPOINT}/avatar/batchsyntheses/{job_id}?api-version={API_VERSION}'
    header = {'Content-Type': 'application/json'}
    header.update(_authenticate(SUBSCRIPTION_KEY))

    payload = {
        'synthesisConfig': {
            "voice": 'Marie_ProNeural',
            # Add word boundary data for timestamping
            "outputFormat": "riff-24khz-16bit-mono-pcm",
            "wordBoundary": True  # This adds word-level timestamping
        },
        'customVoices': {
            "Marie_ProNeural": ""
        },
        "inputKind": "plainText",
        "inputs": [
            {"content": input_text},
        ],
        "avatarConfig": {
            "customized": True,
            "talkingAvatarCharacter": '',
            "talkingAvatarStyle": '',
            "videoFormat": "mp4",
            "videoCodec": "h264",
            "subtitleType": "hard_embedded",
            "backgroundColor": "#FFFFFFFF",
            "backgroundImage": BACKGROUND_IMAGE_URL
        }
    }

    response = requests.put(url, json=payload, headers=header)
    if response.status_code < 400:
        return response.json()["id"]
    else:
        st.error(f'Failed to submit job: {response.text}')
        return None

def get_synthesis(job_id):
    """Check the status of the synthesis job and get the video URL once it's complete."""
    url = f'{SPEECH_ENDPOINT}/avatar/batchsyntheses/{job_id}?api-version={API_VERSION}'
    header = _authenticate(SUBSCRIPTION_KEY)

    try:
        response = requests.get(url, headers=header)
        response.raise_for_status()

        response_data = response.json()

        if response_data['status'] == 'Succeeded':
            return response_data['outputs']['result'], response_data  # Return both the video URL and the entire response data
        else:
            return None, None
    except Exception as e:
        st.error(f"Failed to get job status: {str(e)}")
        return None, None

def upload_to_blob(local_filename, blob_name):
    blob_client = container_client.get_blob_client(blob_name)
    with open(local_filename, "rb") as data:
        blob_client.upload_blob(data)
    return blob_client.url

def generate_filename(username, industry_vertical, customer_name, count, extension, file_type):
    return f"{username}_{industry_vertical}_{customer_name}_Maria_{file_type}{count}.{extension}"

def generate_srt(subtitle_data):
    """
    Generate SRT file content from the subtitle data.
    """
    srt_content = ""
    for idx, entry in enumerate(subtitle_data):
        start_time = format_srt_time(entry['start_time'])
        end_time = format_srt_time(entry['end_time'])
        srt_content += f"{idx+1}\n"
        srt_content += f"{start_time} --> {end_time}\n"
        srt_content += f"{entry['text']}\n\n"
    return srt_content

def save_srt_file(srt_content, srt_filename):
    with open(srt_filename, 'w', encoding='utf-8') as srt_file:
        srt_file.write(srt_content)
    return srt_filename

import subprocess

def format_srt_time(milliseconds):
    """
    Convert milliseconds to SRT time format (hh:mm:ss,ms).
    """
    seconds, ms = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{int(ms):03}"

def extract_word_timestamps(response_data):
    """Extract word-level timestamps from Azure Speech synthesis response data."""
    word_timestamps = []
    if 'wordBoundary' in response_data:
        for word_info in response_data['wordBoundary']:
            word_timestamps.append({
                'start_time': word_info['start'],
                'end_time': word_info['end'],
                'text': word_info['word']
            })
    return word_timestamps

# Streamlit button to submit the job
if st.button("Submit for Synthesis"):
    if not username or not input_text or not customer_name:
        st.warning("Please enter username, text, and customer name.")
    else:
        job_id = _create_job_id()
        recording_count = check_existing_files(username, industry_vertical, customer_name, "recordings")
        
        # Submit the synthesis job
        if submit_synthesis(job_id, input_text):
            st.write(f"Job ID: {job_id}")
            with st.spinner("Waiting for job to complete..."):
                while True:
                    # Call get_synthesis and capture both the download URL and response data
                    download_url, response_data = get_synthesis(job_id)
                    
                    if download_url and response_data:
                        st.success("Job completed successfully!")

                        video_name = generate_filename(username, industry_vertical, customer_name, recording_count, "mp4", "recordings")
                        local_video_path = video_name

                        with requests.get(download_url, stream=True) as r:
                            r.raise_for_status()
                            with open(local_video_path, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=8192):
                                    f.write(chunk)

                        # Generate and save the SRT file
                        subtitle_data = extract_word_timestamps(response_data)
                        srt_content = generate_srt(subtitle_data)
                        srt_filename = f"{video_name}.srt"
                        save_srt_file(srt_content, srt_filename)

                        blob_url = upload_to_blob(local_video_path, video_name)
                        st.session_state['video_history'].append({
                            "name": video_name,
                            "url": blob_url,
                            "sas_token": generate_sas_token(video_name)
                        })

                        st.download_button(
                            label="Download Video",
                            data=open(local_video_path, 'rb'),
                            file_name=video_name,
                            mime='video/mp4'
                        )

                        break
                    time.sleep(5)

# Feedback input
st.subheader("Feedback")
feedback = st.text_area("Please provide feedback if you have any suggestions for improvement.")

if feedback and st.button("Submit Feedback"):
    feedback_count = check_existing_files(username, industry_vertical, customer_name, "feedback")
    feedback_filename = generate_filename(username, industry_vertical, customer_name, feedback_count, "txt", "feedback")
    feedback_blob_client = container_client.get_blob_client(feedback_filename)
    feedback_blob_client.upload_blob(feedback)
    st.success(f"Thank you for your feedback! It has been saved as {feedback_filename}.")

# Display session video history
st.subheader("Session Video History")
for video in st.session_state['video_history']:
    video_sas_url = f"{video['url']}?{video['sas_token']}"
    st.write(f"{video['name']} - [Download]({video_sas_url})")

# Reset session button
if st.button("Reset Session"):
    st.session_state['video_history'] = []
    st.success("Session reset successfully. All session video history cleared.")

# Add a horizontal line for separation
st.markdown("---")
