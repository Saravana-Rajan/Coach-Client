/**
 * Scheduled Apex — runs SchemaChangeDetector every 5 minutes.
 *
 * To schedule:
 *   System.schedule('Schema Change Detector', '0 0/5 * * * ?', new SchemaChangeScheduler());
 *
 * To unschedule:
 *   List<CronTrigger> jobs = [SELECT Id FROM CronTrigger WHERE CronJobDetail.Name = 'Schema Change Detector'];
 *   for (CronTrigger job : jobs) System.abortJob(job.Id);
 */
public class SchemaChangeScheduler implements Schedulable {

    public void execute(SchedulableContext ctx) {
        SchemaChangeDetector.detectChanges();
    }
}
