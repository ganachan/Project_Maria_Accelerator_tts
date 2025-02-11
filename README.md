# **Maria: AI-Driven Custom Avatar GBB Agent**
### Bringing AI to Life with Azure AI Text-to-Speech & Avatars  

Welcome to the **Maria AI Avatar Repository**—your go-to guide for creating and deploying **custom AI-driven avatars with natural-sounding voices** using **Azure AI**. This repository walks you through the **end-to-end process** of setting up **your own AI-powered digital assistant**—from **building an avatar, training a neural voice, and inputting data**, to **generating lifelike video outputs**.

---

## 🚀 **What This Repository Offers**
- **AI-Powered Avatar Creation** – Customize an avatar for your brand, powered by Azure AI.
- **Neural Voice Integration** – Use pre-built or custom-trained voices for enhanced realism.
- **Personalized Text-to-Speech** – Generate speech with **text-based inputs**, tailored to your business.
- **Seamless Video Generation** – Automatically synthesize AI-driven videos with real-time lip-syncing.
- **Azure AI Integration** – Leverage **Azure Speech Services**, **Blob Storage**, and **Custom Neural Voices (CNV)**.
- **Multi-Agent AI Collaboration** – Integrate with other AI assistants for **RAG (Retrieval-Augmented Generation)** workflows.

---

## 🔧 **Getting Started**

### **1️⃣ Setup Your Environment**
First, clone this repository:
```bash
git clone https://github.com/ganachan/Project_Maria_Accelerator_tts.git
cd Maria-AI-Avatar

Install the required dependencies:
pip install -r requirements.txt


2️⃣ Configure Environment Variables
Before running the application, you must set up your .env file with the following environment variables:

SPEECH_ENDPOINT=<YOUR_AZURE_SPEECH_SERVICE_ENDPOINT>
SUBSCRIPTION_KEY=<YOUR_AZURE_SUBSCRIPTION_KEY>
BLOB_CONNECTION_STRING=<YOUR_AZURE_BLOB_STORAGE_CONNECTION_STRING>
BLOB_CONTAINER_NAME=<YOUR_BLOB_CONTAINER_NAME>
API_VERSION=<YOUR_API_VERSION>
BACKGROUND_IMAGE_URL=<URL_TO_BACKGROUND_IMAGE>

3️⃣ How to Use the Repository

Step 1: Create Your Custom Avatar & Neural Voice
To personalize Maria for your brand, you need to:

✅ Create a custom avatar model in the Azure AI Avatar Studio.
✅ Train your custom neural voice (CNV) using Azure AI Speech Studio.
✅ Ensure your avatar model ID and voice ID are accessible via Azure.

Step 2: Modify app.py to Input Your Data
Once your avatar and voice are created, update app.py with your data and configurations.

🔹 Open app.py and customize:

The avatar selection (talkingAvatarCharacter).
The custom neural voice (CNV).
The input text for speech synthesis.
The background image.

Example modification in app.py:

payload = {
    "avatarConfig": {
        "customized": True,
        "talkingAvatarCharacter": "Your_Custom_Avatar_ID",
        "talkingAvatarStyle": "Your_Avatar_Style",
    },
    "synthesisConfig": {
        "voice": "Your_Custom_Neural_Voice_ID",
    },
    "inputKind": "plainText",
    "inputs": [{"content": input_text}]
}

Step 3: Run the Application

Launch the Streamlit UI to start generating AI-driven avatar videos.

streamlit run app.py

Step 4: Store & Share AI-Generated Videos

All videos are stored in Azure Blob Storage. The repository includes functions to:

✅ Generate secure SAS links for easy sharing.
✅ Retrieve and manage AI-generated content via Azure Storage SDK.
✅ Monitor usage and insights via the Azure portal.


🎯 How This Can Be Reused

💡 For Businesses:

Build AI-powered sales & marketing avatars to personalize customer engagement.
Develop AI-driven virtual assistants for healthcare, education, finance, or retail.
Automate internal training & onboarding videos with lifelike avatars.

💡 For Developers:

Extend the repository to support multi-modal AI workflows.
Connect to Microsoft Copilot and Azure OpenAI APIs for dynamic AI interactions.
Deploy AI avatars in Microsoft Teams, ServiceNow, or Dynamics 365.

🚀 Next Steps & Customization

🔹 Enhance personalization: Add customer-specific branding & styles.
🔹 Multi-Agent Collaboration: Integrate Maria with Semantic Kernel Agents.
🔹 Advanced Analytics: Track user engagement & AI-generated interactions.
🔹 Cloud Deployment: Host the application on Azure App Services.


