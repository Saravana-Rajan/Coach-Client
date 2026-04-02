/**
 * Detects field schema changes by querying SetupAuditTrail.
 * Publishes Schema_Change__e Platform Events for each change found.
 * Called by SchemaChangeScheduler every 5 minutes.
 */
public class SchemaChangeDetector {

    // How far back to check (in minutes)
    private static final Integer CHECK_WINDOW_MINUTES = 6;

    public static List<Schema_Change__e> detectChanges() {
        List<Schema_Change__e> events = new List<Schema_Change__e>();

        // Query SetupAuditTrail for recent field changes
        DateTime cutoff = DateTime.now().addMinutes(-CHECK_WINDOW_MINUTES);

        List<SetupAuditTrail> trails = [
            SELECT Action, Section, Display, CreatedDate, CreatedBy.Name
            FROM SetupAuditTrail
            WHERE CreatedDate > :cutoff
            AND (
                Section = 'Custom Fields'
                OR Section = 'Fields'
                OR Display LIKE '%field%'
                OR Display LIKE '%Field%'
                OR Action LIKE '%FieldDefinition%'
            )
            ORDER BY CreatedDate DESC
            LIMIT 50
        ];

        for (SetupAuditTrail trail : trails) {
            Schema_Change__e evt = new Schema_Change__e();
            evt.Object_Name__c = parseObjectName(trail.Display);
            evt.Field_Name__c = parseFieldName(trail.Display);
            evt.Change_Description__c = trail.Display;
            evt.Changed_By__c = trail.CreatedBy.Name;
            evt.Old_Type__c = '';
            evt.New_Type__c = trail.Action;
            events.add(evt);
        }

        // Publish Platform Events
        if (!events.isEmpty()) {
            EventBus.publish(events);

            // Also send webhook to Coach Portal
            SchemaChangeWebhook.sendAsync(events);
        }

        return events;
    }

    private static String parseObjectName(String display) {
        if (display == null) return 'Unknown';
        // Try to extract object name from display string
        // Examples: "Changed field Coach__c on Account", "Created custom field on Contact"
        if (display.containsIgnoreCase('Account')) return 'Account';
        if (display.containsIgnoreCase('Contact')) return 'Contact';
        if (display.containsIgnoreCase('Coach')) return 'Coach';
        return 'Unknown';
    }

    private static String parseFieldName(String display) {
        if (display == null) return 'Unknown';
        // Try to extract field name
        if (display.contains('Coach__c')) return 'Coach__c';
        // Generic: look for __c pattern
        Pattern p = Pattern.compile('(\\w+__c)');
        Matcher m = p.matcher(display);
        if (m.find()) return m.group(1);
        return display.left(100);
    }
}
