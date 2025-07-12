#pip install gspread google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

import gspread
from google.oauth2.service_account import Credentials
import datetime

# Define the scope and load credentials
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
CREDS_FILE = "credentials.json"
SHEET_ID = "1UjPoBYo40jJEtRU8wkZxeawonxccuXjypuR0-Iayr4o"  # Found in the Google Sheet URL: https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit
SHEET_NAME = "Transactions"  # Name of the worksheet in your Google Sheet

def log_transaction(transaction_data):
    try:
        # Authenticate with Google Sheets API
        creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
        client = gspread.authorize(creds)

        # Open the Google Sheet
        spreadsheet = client.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet(SHEET_NAME)

        # Prepare transaction data (example format)
        # Assuming transaction_data is a dict like: {"amount": 100.50, "recipient": "John Doe", "status": "Success"}
        row = [
            datetime.datetime.now().isoformat(),  # Timestamp
            transaction_data.get("amount", ""),
            transaction_data.get("recipient", ""),
            transaction_data.get("status", ""),
            transaction_data.get("transaction_id", "")  # Optional: add more fields as needed
        ]

        # Append the row to the Google Sheet
        worksheet.append_row(row)
        print("Transaction logged successfully!")

    except Exception as e:
        print(f"Error logging transaction: {e}")

# Example usage: Simulate a payment transaction
if __name__ == "__main__":
    # Example transaction data from your payment program
    sample_transaction = {
        "amount": 100.50,
        "recipient": "John Doe",
        "status": "Success",
        "transaction_id": "TXN123456"
    }

    log_transaction(sample_transaction)