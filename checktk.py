from dotenv import load_dotenv
import requests
import os
from datetime import datetime, timedelta


#Add this to your .env file
load_dotenv()
TAEKUS_API_KEY = os.getenv("TAEKUS_API_KEY")
USERNAME = os.getenv("TAEKUS_USERNAME")

class Device:
    def __init__(self, name, device_type, uuid, state):
        self.name = name
        self.device_type = device_type
        self.uuid = uuid
        self.state = state
    
    def __str__(self):
        return f"Device(name={self.name}, type={self.device_type}, uuid={self.uuid}, state={self.state})"

class Account:
    def __init__(self, uuid, nickname, lastFour, status, devices):
        self.uuid = uuid
        self.name = nickname
        self.lastFour = lastFour
        self.status = status
        self.devices = devices

    def __str__(self):
        return f"Account(uuid={self.uuid}, name={self.name})"


def main():
    if not TAEKUS_API_KEY or not USERNAME:
        raise ValueError("TAEKUS_API_KEY and USERNAME must be set in the environment variables.")
    
    BusinessUUID = getBusinessUUID()

    if not BusinessUUID:
        raise ValueError("Business UUID could not be retrieved. Please check your API key and username.")
    
    accountsList = fetchListPaymentCards(BusinessUUID)
    printAccounts(accountsList)

    for account in accountsList:
        fetchListPaymentCardTransactions(BusinessUUID, account.uuid)

    #fetchAllTransactions(BusinessUUID)
    



def getBusinessUUID():
    url = "https://app.taekus.com/api/banking/internal-accounts/"
    headers = {
        "Authorization" : "Api-Key " + TAEKUS_API_KEY,
        "Username" : USERNAME
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print(response.json())
        for account in response.json().get("internal_accounts", []):
            if account.get("display_name") == "Business Debit":
                print("Business Debit Account with UUID:", account.get("uuid"))
                print("Available Balance:", account.get("available_balance"))
                return account.get("uuid")
    else:
        print(f"Failed to fetch transactions: {response.status_code} - {response.text}")

def fetchListPaymentCards(BusinessUUID):
    returnAccounts = []
    url = "https://app.taekus.com/api/banking/payment-cards/virtual/"
    headers = {
        "Authorization" : "Api-Key " + TAEKUS_API_KEY,
        "Username" : USERNAME
    }
    params = {"cardAccountUuid": BusinessUUID}
    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        for account in response.json():
            devices = []
            for device in account.get("digital_wallet_cards"):
                device_obj = Device(
                    name=device.get("device_name"),
                    device_type=device.get("device_type"),
                    uuid=device.get("uuid"),
                    state=device.get("state")
                )
                devices.append(device_obj)
            # Create Account with all devinces and info
            returnAccounts.append(Account(
                uuid=account.get("uuid"),
                nickname=account.get("nickname"),
                lastFour=account.get("last_four"),
                status=account.get("status"),
                devices=devices
            ))
        return returnAccounts

    else:
        print(f"Failed to fetch payment cards: {response.status_code} - {response.text}")

def fetchListPaymentCardTransactions(BusinessUUID, accountUUID):
    url = "https://app.taekus.com/api/banking/payment-cards/transactions/"
    headers = {
        "Authorization" : "Api-Key " + TAEKUS_API_KEY,
        "Username" : USERNAME
    }

    # Get the current time
    now = datetime.now()

    # Calculate the previous day's start and end
    start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = (now - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)

    #print("Start Date:", start_date)
    #print("End Date:", end_date)

    print("Fetching under business UUID:", BusinessUUID)
    print("Fetching transactions for account UUID:", accountUUID)

    params = {
        "cardAccountUuid": BusinessUUID,
        "virtualCardUUID": accountUUID,
        "filterType": "PURCHASE",
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat()
        }
    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        print(response.json())
    else:
        print(f"Failed to fetch transactions: {response.status_code} - {response.text}")


def fetchAllTransactions(BusinessUUID):
    url = "https://app.taekus.com/api/banking/payment-cards/transactions/"
    headers = {
        "Authorization" : "Api-Key " + TAEKUS_API_KEY,
        "Username" : USERNAME
    }

    # Get the current time
    now = datetime.now()

    # Calculate the previous day's start and end
    start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = (now - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)

    params = {
        "cardAccountUuid": BusinessUUID,
        "filterType": "PURCHASE",
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat()
        }
    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        print(response.json())
    else:
        print(f"Failed to fetch transactions: {response.status_code} - {response.text}")



def printAccounts(accounts):
    for account in accounts:
        print(f"Account UUID: {account.uuid}, Name: {account.name}, Last Four: {account.lastFour}, Status: {account.status}")
        for device in account.devices:
            print(f"  Device Name: {device.name}, Type: {device.device_type}, UUID: {device.uuid}, State: {device.state}")

if __name__ == "__main__":
    main()
