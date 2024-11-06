# coze_api_client.py

import os
import requests
import json

class CozeAPIClient:
    def __init__(self, access_token: str):
        """
        Initialize the Coze API client with the required access token.
        """
        self.base_url = "https://api.coze.com/v1/workflow/run"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    def run_workflow(self, workflow_id: str, parameters: dict = None, bot_id: str = None, ext: dict = None):
        """
        Run a workflow with the specified workflow ID and optional parameters.
        :param workflow_id: The ID of the workflow to run.
        :param parameters: Input parameters for the workflow's starting node (optional).
        :param bot_id: The associated Bot ID (optional).
        :param ext: Additional fields (optional).
        :return: A well-formatted and indented response.
        """
        # Prepare the payload (body) for the request
        payload = {
            "workflow_id": workflow_id,
        }
        
        # Add optional parameters to the payload if provided
        if parameters:
            payload["parameters"] = parameters
        if bot_id:
            payload["bot_id"] = bot_id
        if ext:
            payload["ext"] = ext

        # Make the POST request to run the workflow
        response = requests.post(self.base_url, headers=self.headers, data=json.dumps(payload))

        # Process the response based on status code
        if response.status_code == 200:
            # Parse the response
            response_data = response.json()
            if "data" in response_data:
                # Unpack and format nested JSON within the 'data' field
                response_data["data"] = self.parse_nested_json(response_data["data"])
            return response_data
        else:
            # Return the error response with details if the call fails
            error_data = {
                "code": response.status_code,
                "msg": response.text
            }
            return error_data

    def parse_nested_json(self, data):
        """
        Recursively parses nested JSON strings in the 'data' field.
        :param data: The raw data string that might contain JSON.
        :return: Parsed JSON object if possible, or the original string if not.
        """
        if isinstance(data, str):
            try:
                # Attempt to parse the 'data' field into a Python dictionary
                parsed_data = json.loads(data)
                # Recursively check if the parsed data contains more JSON strings
                return self.parse_nested_json(parsed_data)
            except (json.JSONDecodeError, TypeError):
                # If the data is not valid JSON, return it as-is
                return data
        elif isinstance(data, dict):
            # Recursively parse each value in the dictionary
            return {key: self.parse_nested_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            # Recursively parse each item in the list
            return [self.parse_nested_json(item) for item in data]
        else:
            # Return the data as-is if it's not a string or dict
            return data

    def format_response(self, response_data: dict) -> str:
        """
        Formats the response data to be well indented and structured for readability.
        :param response_data: The raw response data as a dictionary.
        :return: A formatted string of the response.
        """
        return json.dumps(response_data, indent=4, sort_keys=True)

# Instantiate the CozeAPIClient
coze_client = CozeAPIClient(access_token=os.getenv("COZE_API_TOKEN", ""))
workflow_id = "7429188020409270277"

def fetch_data(stock_symbol: str):
    """
    Fetches data for the specified stock symbol using CozeAPIClient.
    :param stock_symbol: The stock symbol for which to retrieve data.
    :return: The API response.
    """
    parameters = {
        "BOT_USER_INPUT": "Predict the next month",  # Placeholder input
        "Stock_Name": stock_symbol.upper()  # Use the user-provided stock symbol
    }
    # Run the workflow with the provided parameters
    return coze_client.run_workflow(workflow_id=workflow_id, parameters=parameters)
