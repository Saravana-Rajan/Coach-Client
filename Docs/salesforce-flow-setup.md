# Salesforce Flow Webhook Setup

## Prerequisites
- ngrok installed and authenticated (https://ngrok.com/download)
- Backend server running on port 8001

## Start ngrok
```bash
ngrok http 8001
```
This will give a public URL like `https://abc123.ngrok.io`

## Your webhook URL
Replace YOUR_NGROK_URL with the actual ngrok URL.

Webhook endpoint: `YOUR_NGROK_URL/api/sf-connector/notify/`

## Steps to create the Flow in Salesforce:

### 1. Go to Setup -> Flows -> New Flow
- Select "Record-Triggered Flow"
- Click "Create"

### 2. Configure the trigger:
- Object: Account
- Trigger: "A record is created or updated"
- Condition: None (trigger on any change)

### 3. Add an Action:
- Type: "HTTP Callout" (or "Apex Action" if HTTP Callout isn't available)
- URL: YOUR_NGROK_URL/api/sf-connector/notify/
- Method: POST
- Body: `{"source": "salesforce", "object": "Account"}`

### 4. Save and Activate the Flow

### 5. Repeat for Contact object (create a second Flow)

## Testing:
1. Edit any Account in Salesforce (e.g., change a coach name)
2. The Flow will call your webhook
3. The Coach Portal will show "Out of sync" notification
4. Click "Sync Now" to pull and sync

## Notes on ngrok
- The free tier generates a new URL each time ngrok is restarted, so you will need to update the Salesforce Flow URL accordingly.
- For a stable URL, consider upgrading to a paid ngrok plan or using a persistent tunnel solution.
- ngrok must remain running for the webhook to be reachable.
