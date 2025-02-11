import streamlit as st
import json
import logging
import os
import sys
import time
import uuid
import requests
import asyncio
import nest_asyncio

from datetime import datetime, timedelta, timezone
import base64

# Optional: load environment variables from a .env file if needed
# from dotenv import load_dotenv
# load_dotenv(override=True)

# Semantic Kernel imports
from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents import ChatHistory, ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole

nest_asyncio.apply()

###################################
# CONFIGURATION
###################################
# Replace the following placeholder values with your own configuration.
AZURE_AD_TENANT_ID = "YOUR_AZURE_AD_TENANT_ID"
REDIRECT_URI = "YOUR_REDIRECT_URI"
SPEECH_ENDPOINT = "YOUR_SPEECH_ENDPOINT"
SUBSCRIPTION_KEY = "YOUR_SUBSCRIPTION_KEY"
BLOB_CONNECTION_STRING = "YOUR_BLOB_CONNECTION_STRING"
BLOB_CONTAINER_NAME = "YOUR_BLOB_CONTAINER_NAME"
API_VERSION = "YOUR_API_VERSION"
TRANSLATOR_ENDPOINT = "YOUR_TRANSLATOR_ENDPOINT"
TRANSLATOR_SUBSCRIPTION_KEY = "YOUR_TRANSLATOR_SUBSCRIPTION_KEY"
BACKGROUND_IMAGE_URL = "YOUR_BACKGROUND_IMAGE_URL"

# Summarizer & Manager Agents configuration
AZURE_OPENAI_API_KEY = "YOUR_AZURE_OPENAI_API_KEY"
AZURE_OPENAI_ENDPOINT = "YOUR_AZURE_OPENAI_ENDPOINT"
AZURE_OPENAI_DEPLOYMENT_NAME = "YOUR_OPENAI_DEPLOYMENT_NAME"
AZURE_OPENAI_API_VERSION = "YOUR_AZURE_OPENAI_API_VERSION"

# Bing Search configuration
BING_SEARCH_ENDPOINT = "https://api.bing.microsoft.com/v7.0/search"
BING_SEARCH_API_KEY = "YOUR_BING_SEARCH_API_KEY"

###################################
# STREAMLIT PAGE CONFIG
###################################
st.set_page_config(page_title="Three-Agent Flow: Search, Summarize, Manager", layout="wide")

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
        font-size: 1.7em;
        line-height: 1.2;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("Multi-Agent Dynamo: Bing Search→ Summaries → TTS — Maria, your AI GBB Agent for dynamic customer engagements")

st.markdown(
    """
Agents:  
Step A) **SearchAgent** fetches Bing data.  
Step B) **SummarizerAgent** takes the Bing search results (assumed to be around 200 words) and produces a concise summary of 100–150 words that mentions only the customer and Microsoft.  
Step C) **ManagerAgent** checks the summary for unwanted brands and approves or requests changes.  
Step D) **Maria** generates a TTS Avatar video based on the approved summary.  

Feedback & Video History below.
""",
    unsafe_allow_html=True
)

###################################
# SIDEBAR
###################################
with st.sidebar:
    st.header("User Information")
    username = st.text_input("Username", value="")
    customer_name = st.text_input("Customer Name", value="")
    st.date_input("Date", value=datetime.now().date())

    st.header("Subtitle Language Options")
    target_language = st.selectbox(
        "Select Language for Captions",
        {"en": "English", "es": "Spanish", "fr": "French", "de": "German", "zh-Hans": "Simplified Chinese"},
        index=0
    )

###################################
# AGENT DEFINITIONS
###################################

# Step A) SearchAgent: queries Bing
def bing_search(query: str) -> str:
    """Queries Bing for the given text and returns snippet data."""
    if not BING_SEARCH_API_KEY or "YOUR_BING_SEARCH_API_KEY" in BING_SEARCH_API_KEY:
        return "**ERROR**: Bing Search API key not found. Provide BING_SEARCH_API_KEY in your configuration."
    headers = {"Ocp-Apim-Subscription-Key": BING_SEARCH_API_KEY}
    params = {"q": query, "count": 2}
    try:
        response = requests.get(BING_SEARCH_ENDPOINT, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        results_text = ""
        if "webPages" in data and "value" in data["webPages"]:
            for item in data["webPages"]["value"]:
                snippet = item.get("snippet", "")
                results_text += snippet + "\n"
        else:
            results_text = "No Bing results found."
        return results_text.strip()
    except Exception as e:
        return f"Bing API call failed: {str(e)}"

def create_summarizer_agent():
    """
    Agent that takes the Bing search results (around 200 words) as input and summarizes them into a concise summary of 100–150 words.
    The summary must mention only the customer's name (from user input) and Microsoft.
    """
    kernel = Kernel()
    azure_chat = AzureChatCompletion(
        service_id="summarizer_service",
        api_key=AZURE_OPENAI_API_KEY,
        endpoint=AZURE_OPENAI_ENDPOINT,
        deployment_name=AZURE_OPENAI_DEPLOYMENT_NAME,
        api_version=AZURE_OPENAI_API_VERSION
    )
    kernel.add_service(azure_chat)
    instructions = (
        "You are SummarizerAgent. Given the Bing search results provided (approximately 200 words), summarize the information into a concise summary of 100 to 150 words. "
        "The summary must mention only the customer's name (from user input) and Microsoft, and exclude any other brands or competitors. "
        "Focus on the customer's history, vision, products, and services."
    )
    summarizer_agent = ChatCompletionAgent(
        service_id="summarizer_service",
        kernel=kernel,
        name="SummarizerAgent",
        instructions=instructions
    )
    return summarizer_agent

def create_manager_agent(customer_name: str):
    """Agent that checks the summary for unwanted brand names and approves or requests changes."""
    kernel = Kernel()
    azure_chat = AzureChatCompletion(
        service_id="manager_service",
        api_key=AZURE_OPENAI_API_KEY,
        endpoint=AZURE_OPENAI_ENDPOINT,
        deployment_name=AZURE_OPENAI_DEPLOYMENT_NAME,
        api_version=AZURE_OPENAI_API_VERSION
    )
    kernel.add_service(azure_chat)
    manager_instructions = (
        f"You are ManagerAgent. Check the summary provided by SummarizerAgent to ensure:\n"
        f"1) Only the customer's name '{customer_name}' and 'Microsoft' are mentioned.\n"
        "2) The summary is within 100 to 150 words.\n"
        "3) If the summary is acceptable, respond 'approved'. Otherwise, indicate what needs to be changed."
    )
    manager_agent = ChatCompletionAgent(
        service_id="manager_service",
        kernel=kernel,
        name="ManagerAgent",
        instructions=manager_instructions
    )
    return manager_agent

async def run_summarizer_manager_chain(customer_name: str, raw_text: str) -> (str, str, str):
    """
    1) SummarizerAgent processes the Bing search results.
    2) ManagerAgent checks the resulting summary.
    Returns (summarizer_output, manager_output, conversation).
    """
    conversation_log = []
    
    # Summarizer
    summarizer_agent = create_summarizer_agent()
    sum_history = ChatHistory()
    sum_history.add_message(ChatMessageContent(role=AuthorRole.SYSTEM, content=summarizer_agent.instructions))
    sum_history.add_user_message(raw_text)
    summarizer_output = ""
    async for msg in summarizer_agent.invoke(sum_history):
        summarizer_output = msg.content
        sum_history.add_message(msg)
        conversation_log.append(f"[Summarizer] {msg.content}")
    
    # Manager
    manager_agent = create_manager_agent(customer_name)
    manager_history = ChatHistory()
    manager_history.add_message(ChatMessageContent(role=AuthorRole.SYSTEM, content=manager_agent.instructions))
    manager_history.add_user_message(summarizer_output)
    manager_output = ""
    async for msg in manager_agent.invoke(manager_history):
        manager_output = msg.content
        manager_history.add_message(msg)
        conversation_log.append(f"[Manager] {msg.content}")
    
    full_convo = "\n".join(conversation_log)
    return summarizer_output, manager_output, full_convo

###########################
#  UI - BING + SUMMARIZE
###########################
st.markdown(
    "<h3 style='font-size:18px; margin-bottom:10px;'>1) Bing Search -> Summarize -> Manager Approval</h3>",
    unsafe_allow_html=True
)
bing_col, summary_col = st.columns(2)

with bing_col:
    st.write("**Step A: Bing Search**")
    if st.button("Fetch Bing Data"):
        if not customer_name:
            st.warning("Please enter a Customer Name in the sidebar.")
        else:
            query = f"{customer_name} history, recent recognition, products and services"
            st.info(f"Searching: {query}")
            data_found = bing_search(query)
            st.write("**Bing Data**:")
            st.write(data_found)
            st.session_state["bing_data"] = data_found

with summary_col:
    st.write("**Step B & C: Summarize & Manager Check**")
    if st.button("Summarize & Approve?"):
        if "bing_data" not in st.session_state or not st.session_state["bing_data"].strip():
            st.warning("No Bing data found. Fetch data first!")
        else:
            with st.spinner("Summarizing & Manager Checking..."):
                loop = asyncio.get_event_loop()
                sum_out, mgr_out, convo = loop.run_until_complete(
                    run_summarizer_manager_chain(customer_name, st.session_state["bing_data"])
                )
            st.success("**Summarizer Output**: " + sum_out)
            st.info("**Manager Decision**: " + mgr_out)
            if "approved" in mgr_out.lower():
                # Store only the summarizer's output as the final summary.
                st.session_state["final_summary"] = sum_out
                st.success("✅ Manager approved the summary! It has now been appended to the TTS input text below.")
            else:
                st.warning("Manager requests changes. Please revise or gather more data.")
            st.expander("Agent Conversation").write(convo)
            st.download_button(
                label="Download Agent Conversation",
                data=convo,
                file_name="agent_conversation.txt",
                mime="text/plain"
            )

st.markdown("---")

###########################
# 2) TTS AVATAR SECTION
###########################
st.subheader("2) Create Avatar Video with Summarized Context")

# Automatically use the final summary from session state (if available)
if 'final_summary' not in st.session_state:
    st.session_state['final_summary'] = ""
approved_summary = st.session_state.get('final_summary', st.session_state.get('summary_for_tts', ""))

# Build the TTS prompt automatically if username and customer_name are provided.
if username and customer_name:
    default_tts_text = (
        f"Hello {customer_name}, I'm Maria, your AI customer support agent at Microsoft.\n\n"
        "We appreciate your interest in exploring Azure AI solutions. "
        "Our team is eager to assist you and provide relevant info.\n\n"
        f"{approved_summary}\n\n"
        "Let us know how we can help with your projects or use cases!"
    )
else:
    default_tts_text = "Hi, I'm Maria, your AI partner from the Global Black Belt AI Team at Microsoft."

input_text = st.text_area("TTS Prompt:", value=default_tts_text, height=200)

# BLOB & TTS setup
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)

if 'video_history' not in st.session_state:
    st.session_state['video_history'] = []

def _create_job_id():
    return str(uuid.uuid4())

def _authenticate(subscription_key):
    return {'Ocp-Apim-Subscription-Key': subscription_key}

def check_existing_files(username, customer_name, file_type):
    file_prefix = f"{username}_{customer_name}_Maria_{file_type}"
    existing_files = container_client.list_blobs(name_starts_with=file_prefix)
    count = 1
    for blob in existing_files:
        blob_name = blob.name
        parts = blob_name.split("_")
        if len(parts) >= 3 and parts[-1].startswith(file_type):
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

def submit_synthesis(job_id: str, tts_text: str):
    url = f'{SPEECH_ENDPOINT}/avatar/batchsyntheses/{job_id}?api-version={API_VERSION}'
    header = {'Content-Type': 'application/json'}
    header.update(_authenticate(SUBSCRIPTION_KEY))
    payload = {
        'synthesisConfig': {
            "voice": "YOUR_TTS_VOICE",
            "outputFormat": "riff-24khz-16bit-mono-pcm",
            "wordBoundary": True
        },
        'customVoices': {
            "YOUR_TTS_VOICE": "YOUR_CUSTOM_VOICE_ID"
        },
        "inputKind": "plainText",
        "inputs": [
            {"content": tts_text}
        ],
        "avatarConfig": {
            "customized": True,
            "talkingAvatarCharacter": "YOUR_AVATAR_CHARACTER",
            "talkingAvatarStyle": "YOUR_AVATAR_STYLE",
            "videoFormat": "mp4",
            "videoCodec": "h264",
            "subtitleType": "hard_embedded",
            "backgroundColor": "#FFFFFFFF",
            "backgroundImage": BACKGROUND_IMAGE_URL
        }
    }
    resp = requests.put(url, json=payload, headers=header)
    if resp.status_code < 400:
        return resp.json().get("id")
    else:
        st.error(f"Avatar TTS error: {resp.text}")
        return None

def get_synthesis(job_id):
    url = f'{SPEECH_ENDPOINT}/avatar/batchsyntheses/{job_id}?api-version={API_VERSION}'
    header = _authenticate(SUBSCRIPTION_KEY)
    try:
        r = requests.get(url, headers=header)
        r.raise_for_status()
        data = r.json()
        return data.get('outputs', {}).get('result'), data
    except Exception as e:
        st.error(f"Failed TTS job status: {str(e)}")
        return None, None

def upload_to_blob(local_file, blob_name):
    bc = container_client.get_blob_client(blob_name)
    with open(local_file, "rb") as d:
        bc.upload_blob(d, overwrite=True)
    return bc.url

if st.button("Generate Video"):
    if not username or not input_text or not customer_name:
        st.warning("Enter username, text, and customer name first.")
    else:
        recording_count = check_existing_files(username, customer_name, "recordings")
        job_id = _create_job_id()
        if submit_synthesis(job_id, input_text):
            st.write(f"TTS Job ID: {job_id}")
            with st.spinner("Building your avatar video..."):
                max_attempts = 60  # 60 attempts * 5 seconds = 5 minutes timeout
                attempt = 0
                while attempt < max_attempts:
                    url_dl, data = get_synthesis(job_id)
                    if url_dl and data:
                        if data.get('status') == 'Succeeded':
                            st.success("Video creation succeeded!")
                            video_name = f"{username}_{customer_name}_Maria_recordings{recording_count}.mp4"
                            with requests.get(url_dl, stream=True) as r:
                                r.raise_for_status()
                                with open(video_name, 'wb') as f:
                                    for chunk in r.iter_content(chunk_size=8192):
                                        f.write(chunk)
                            blob_url = upload_to_blob(video_name, video_name)
                            st.session_state['video_history'].append({
                                "name": video_name,
                                "url": blob_url,
                                "sas_token": generate_sas_token(video_name)
                            })
                            st.download_button(
                                label="Download Video",
                                data=open(video_name, 'rb'),
                                file_name=video_name,
                                mime='video/mp4'
                            )
                            break
                    attempt += 1
                    time.sleep(5)
                else:
                    st.error("TTS job did not complete within the expected time.")

#############################################
# FEEDBACK / VIDEO HISTORY
#############################################
st.subheader("Feedback")
feedback = st.text_area("Any suggestions?")

if feedback and st.button("Submit Feedback"):
    feedback_count = check_existing_files(username, customer_name, "feedback")
    fname = f"{username}_{customer_name}_Maria_feedback{feedback_count}.txt"
    bc = container_client.get_blob_client(fname)
    bc.upload_blob(feedback)
    st.success(f"Feedback saved: {fname}")

st.subheader("Session Video History")
if "video_history" not in st.session_state:
    st.session_state["video_history"] = []

for vid in st.session_state["video_history"]:
    link = f"{vid['url']}?{vid['sas_token']}"
    st.write(f"{vid['name']} - [Download]({link})")

if st.button("Reset Session"):
    st.session_state["video_history"] = []
    st.success("Session cleared.")

st.markdown("---")

# Logout button if needed
from urllib.parse import urlencode
if AZURE_AD_TENANT_ID:
    logout_url = f"https://login.microsoftonline.com/{AZURE_AD_TENANT_ID}/oauth2/v2.0/logout"
    post_logout_redirect = {"post_logout_redirect_uri": REDIRECT_URI}
    logout_url_with_redirect = f"{logout_url}?{urlencode(post_logout_redirect)}"
    st.markdown(
        f"""
        <div style="margin-top: 10px; text-align: left;">
            <a href="{logout_url_with_redirect}" target="_self" style="text-decoration: none;">
                <button style="background-color: #0078D4; color: white; padding: 10px 20px; border: none; border-radius: 5px; font-size: 16px; cursor: pointer;">
                    Logout
                </button>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )
