# Salesforce Deployment — Schema Change Detection

Deploy these to your Salesforce org to enable real-time schema change detection.

## What This Does
- Creates a Platform Event `Schema_Change__e` that fires when field metadata changes
- Creates a Scheduled Apex class that checks for metadata changes every 5 minutes
- Sends a webhook to your Coach Portal app when changes are detected

## Deploy Steps

### 1. Create the Platform Event
Go to **Setup → Platform Events → New Platform Event**:
- Label: `Schema Change`
- API Name: `Schema_Change__e`
- Add these custom fields:
  - `Object_Name__c` (Text, 100)
  - `Field_Name__c` (Text, 100)
  - `Old_Type__c` (Text, 100)
  - `New_Type__c` (Text, 100)
  - `Changed_By__c` (Text, 200)
  - `Change_Description__c` (Long Text Area, 1000)

### 2. Deploy the Apex Classes
Go to **Setup → Apex Classes → New** and paste each class:
- `SchemaChangeDetector.cls` — Queries SetupAuditTrail for field changes
- `SchemaChangeScheduler.cls` — Runs the detector every 5 minutes
- `SchemaChangeWebhook.cls` — Sends webhook to your Coach Portal

### 3. Schedule the Job
Open **Developer Console → Execute Anonymous** and run:
```apex
System.schedule('Schema Change Detector', '0 0/5 * * * ?', new SchemaChangeScheduler());
```

### 4. Configure the Webhook URL
Go to **Setup → Custom Metadata Types** or **Custom Settings** and set:
- `Coach_Portal_URL__c` = `http://your-app-url/api/sf-connector/schema-webhook/`

Or update the URL directly in `SchemaChangeWebhook.cls`.

### 5. Add Remote Site Setting
Go to **Setup → Remote Site Settings → New**:
- Name: `CoachPortal`
- URL: `http://your-app-url` (or `http://localhost:8000` for dev)
