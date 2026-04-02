/**
 * Sends detected schema changes to the Coach Portal webhook endpoint.
 * Uses @future for async callout from scheduled context.
 */
public class SchemaChangeWebhook {

    // UPDATE THIS to your Coach Portal URL
    private static final String WEBHOOK_URL = 'http://localhost:8000/api/sf-connector/schema-webhook/';

    @future(callout=true)
    public static void sendAsync(List<Schema_Change__e> events) {
        // Serialize doesn't work on Platform Events directly, build JSON manually
        sendPayload(serializeEvents(events));
    }

    @future(callout=true)
    public static void sendPayload(String jsonBody) {
        try {
            HttpRequest req = new HttpRequest();
            req.setEndpoint(WEBHOOK_URL);
            req.setMethod('POST');
            req.setHeader('Content-Type', 'application/json');
            req.setBody(jsonBody);
            req.setTimeout(10000);

            Http http = new Http();
            HttpResponse res = http.send(req);

            if (res.getStatusCode() != 200) {
                System.debug('Schema webhook failed: ' + res.getStatusCode() + ' ' + res.getBody());
            }
        } catch (Exception e) {
            System.debug('Schema webhook error: ' + e.getMessage());
        }
    }

    private static String serializeEvents(List<Schema_Change__e> events) {
        List<Map<String, String>> payload = new List<Map<String, String>>();
        for (Schema_Change__e evt : events) {
            Map<String, String> item = new Map<String, String>();
            item.put('object_name', evt.Object_Name__c);
            item.put('field_name', evt.Field_Name__c);
            item.put('old_type', evt.Old_Type__c);
            item.put('new_type', evt.New_Type__c);
            item.put('changed_by', evt.Changed_By__c);
            item.put('description', evt.Change_Description__c);
            payload.add(item);
        }
        return JSON.serialize(new Map<String, Object>{
            'source' => 'salesforce_platform_event',
            'changes' => payload
        });
    }
}
