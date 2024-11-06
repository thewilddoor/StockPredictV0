# coze_chat.py

import requests
import uuid
import logging
import sys
import json

class Coze:
    def __init__(self,
                 bot_id=None,
                 api_token=None,
                 user_id="default_user",
                 conversation_id=None,
                 stream=False):
        self.bot_id = bot_id
        self.api_token = api_token
        self.user_id = user_id
        self.conversation_id = conversation_id or self.generate_conversation_id()
        self.stream = stream
        self.url = 'https://api.coze.com/open_api/v2/chat'
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        }
        logging.basicConfig(stream=sys.stderr, level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def generate_conversation_id():
        return str(uuid.uuid4())

    @staticmethod
    def build_messages(history=None):
        """
        Builds the message list to send to the Coze API.
        :param history: A list of (content, is_user) tuples.
        :return: A list of dictionaries formatted for the Coze API.
        """
        messages = []
        if history:
            for content, is_user in history:
                role = 'user' if is_user else 'assistant'
                messages.append({
                    "role": role,
                    "content": content
                })
        return messages

    def chat(self, query, history=None):
        """
        Sends a message to the Coze API and returns the assistant's response.
        :param query: The user's message.
        :param history: A list of (content, is_user) tuples representing the chat history.
        :return: The assistant's response as a string.
        """
        payload = {
            "bot_id": self.bot_id,
            "user": self.user_id,
            "query": query,
            "stream": self.stream
        }

        # Include conversation_id if provided
        if self.conversation_id:
            payload["conversation_id"] = self.conversation_id

        # Include chat_history if provided
        if history:
            payload["chat_history"] = self.build_messages(history)

        try:
            response = requests.post(self.url, headers=self.headers, json=payload)
            response.raise_for_status()
        except requests.RequestException as e:
            self.logger.error(f"Request error: {e}")
            return "An error occurred while processing your request."

        try:
            data = response.json()
            return self.get_response(data)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            return "Invalid response format received."

    def get_response(self, data):
        """
        Processes the API response to extract the assistant's response.
        :param data: The API response data.
        :return: The response content from the assistant.
        """
        if 'messages' in data:
            messages = data['messages']
            response_content = ''
            for msg in messages:
                if msg['role'] == 'assistant' and msg['type'] == 'answer':
                    response_content += msg['content']
            return response_content
        else:
            self.logger.error(f"No messages in response: {data}")
            return "No messages received from the server."

    def reset_conversation(self):
        """
        Resets the conversation by generating a new conversation_id.
        """
        self.conversation_id = self.generate_conversation_id()
        self.logger.info("Conversation has been reset with new conversation_id.")
