import os
import requests
import json
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def extract_content_from_transcript(transcript):
    """ Extract meaningful content from transcript using API
    
    Args: 
        transcript (str): Transcript content from video 
        
    Returns: 
        str: Extracted and summarized content 
    """
    if not transcript or transcript.strip() == "":
        return "No content available"
    
    # Prepare transcript for sending
    cleaned_text = transcript.replace('\n', ' ').strip()
    
    # Get API key from environment variable
    api_key = os.getenv("CHATBOT_API_KEY", "app-cas1MEUkygU1lBucQpW8JTxN")
    
    # Configure API endpoint
    url = "http://chatbot.demo.mqsolutions.vn/v1/chat-messages"
    
    # Prepare payload
    payload = {
        "inputs": {},
        "query": "Đoạn văn dưới đây có điều vi phạm nào trong luật an ninh mạng hay không: " + cleaned_text,
        "response_mode": "streaming",  # Using streaming mode as requested
        "conversation_id": "",
        "user": "admin",
        "files": [
            {
                "type": "image",
                "transfer_method": "remote_url",
                "url": "https://cloud.Dify.ai/logo/logo-site.png"
            }
        ]
    }
    
    # Headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        # Send request
        logger.info("Sending transcript to API for content extraction")
        response = requests.post(url, headers=headers, json=payload, timeout=30, stream=True)
        
        # Check response
        response.raise_for_status()  # Raise exception if status code >= 400
        
        # Handle streaming response
        full_content = ""
        for line in response.iter_lines():
            if line:
                # The line might begin with "data: " for SSE format
                if line.startswith(b'data: '):
                    line = line[6:]  # Skip the "data: " prefix
                
                try:
                    data = json.loads(line)
                    if "answer" in data:
                        full_content += data["answer"]
                except json.JSONDecodeError:
                    # If it's not valid JSON, just append as string
                    full_content += line.decode('utf-8')
        
        if full_content:
            logger.info(f"Content extracted successfully from API, content length: {len(full_content)}")
            return full_content
        else:
            logger.warning("API response is empty, using simple extraction method")
            return simple_extract_content(cleaned_text)
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling API: {str(e)}")
        # Fallback to simple extraction
        return simple_extract_content(cleaned_text)
    except Exception as e:
        logger.error(f"Error processing response from API: {str(e)}")
        # Fallback to simple extraction
        return simple_extract_content(cleaned_text)

def simple_extract_content(text):
    """Simple extraction method when API is unavailable"""
    max_length = 1000
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text
