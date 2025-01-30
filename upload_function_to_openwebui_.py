import os
import json
import requests
from dotenv import load_dotenv

OPENWEBUI_URL = "https://llm.oculair.ca"

def get_jwt_token():
    load_dotenv()
    token = os.getenv("OPENWEBUI_JWT_TOKEN")
    if not token:
        raise ValueError("OPENWEBUI_JWT_TOKEN not found in .env file")
    return token

def upload_function(name, content, description=""):
    """Upload or update a function in OpenWebUI"""
    
    OPENWEBUI_JWT_TOKEN = get_jwt_token()
    function_id = f"custom_{name.lower().replace(' ', '_')}"
    
    headers = {
        "Authorization": f"Bearer {OPENWEBUI_JWT_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "OpenWebUI-Function-Uploader/1.0"
    }
    
    # First try to delete the function if it exists
    delete_url = f"{OPENWEBUI_URL}/api/v1/functions/id/{function_id}/delete"
    try:
        requests.delete(delete_url, headers=headers)
        print("Deleted existing function...")
    except requests.exceptions.RequestException:
        pass
    
    # Create new function
    url = f"{OPENWEBUI_URL}/api/v1/functions/create"
    payload = {
        "id": function_id,
        "name": name,
        "content": content,
        "meta": {
            "description": description,
            "manifest": {}
        }
    }
    
    try:
        print("Creating new function...")
        print(f"URL: {url}")
        print(f"Headers: {headers}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        response = requests.post(url, headers=headers, json=payload)
        print(f"Response Status: {response.status_code}")
        print(f"Response Text: {response.text}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error uploading function: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
            print(f"Request URL: {e.response.url}")
            print(f"Request Headers: {e.response.request.headers}")
            print(f"Request Body: {e.response.request.body}")
        return None

if __name__ == "__main__":
    # Example usage
    function_name = input("Enter function name: ")
    function_content = input("Enter function content: ")
    function_description = input("Enter function description (optional): ")
    
    result = upload_function(function_name, function_content, function_description)
    
    if result:
        print("Function uploaded successfully!")
        print("Function ID:", result.get("id"))
    else:
        print("Failed to upload function")