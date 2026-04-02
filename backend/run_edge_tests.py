"""
Edge Case Test Suite — Coach-Client Reassignment System
Runs all ~15 real-world scenarios from the PRD and documents results.
"""
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

import django
django.setup()

from salesforce_sim.models import SFCoach, SFAccount, SFContact, SFAssignment
from coaching.models import Coach, Account, Contact
from sync.engine import run_sync
from sync.models import AuditRecord

# Get coaches
alice = SFCoach.objects.using('salesforce').get(name='Alice Johnson')
bob = SFCoach.objects.using('salesforce').get(name='Bob Smith')
carol = SFCoach.objects.using('salesforce').get(name='Carol Williams')
dave = SFCoach.objects.using('salesforce').get(name='Dave Brown')
eve = SFCoach.objects.using('salesforce').get(name='Eve Davis')

results = []


def test(num, name, setup_fn, verify_fn=None):
    print(f"TEST {num}: {name}")
    setup_fn()
    r = run_sync()
    audits = list(AuditRecord.objects.filter(sync=r))
    passed = r.status == "completed"
    if verify_fn:
        passed = passed and verify_fn(r, audits)
    for a in audits[:3]:
        print(f"  Audit: {a.change_type} - {a.entity_name}")
    if len(audits) > 3:
        print(f"  ... and {len(audits) - 3} more")
    print(f"  Changes: {r.changes_detected} | RESULT: {'PASS' if passed else 'FAIL'}")
    results.append((num, name, "PASS" if passed else "FAIL", r.changes_detected))
    print()


# TEST 1: Account reassigned to different coach
def t1():
    tc = SFAccount.objects.using('salesforce').get(name='TechCorp')
    tc.coach = bob
    tc.save(using='salesforce')
    SFContact.objects.using('salesforce').filter(account=tc).update(coach=bob)

def v1(r, a):
    return any(x.change_type == 'account_reassigned' and x.entity_name == 'TechCorp' for x in a)

test(1, "Account reassigned from Alice to Bob", t1, v1)


# TEST 2: Coach leaves org, clients redistributed
def t2():
    dave.is_active = False
    dave.save(using='salesforce')
    for acc in SFAccount.objects.using('salesforce').filter(coach=dave):
        acc.coach = eve
        acc.save(using='salesforce')
        SFContact.objects.using('salesforce').filter(account=acc).update(coach=eve)

test(2, "Coach (Dave) leaves org, clients go to Eve", t2)


# TEST 3: Multiple coaches swap simultaneously
def t3():
    bob_accts = list(SFAccount.objects.using('salesforce').filter(coach=bob))
    carol_accts = list(SFAccount.objects.using('salesforce').filter(coach=carol))
    for a in bob_accts:
        a.coach = carol
        a.save(using='salesforce')
        SFContact.objects.using('salesforce').filter(account=a).update(coach=carol)
    for a in carol_accts:
        a.coach = bob
        a.save(using='salesforce')
        SFContact.objects.using('salesforce').filter(account=a).update(coach=bob)

test(3, "Multi-coach swap: Bob <-> Carol accounts", t3)


# TEST 4: New account added
def t4():
    SFAccount.objects.using('salesforce').create(
        name='NewStartup Inc', industry='Technology',
        website='https://newstartup.com',
        coaching_start_date='2026-03-25', coach=alice
    )

def v4(r, a):
    return any(x.change_type == 'account_added' and x.entity_name == 'NewStartup Inc' for x in a)

test(4, "New account added (NewStartup Inc)", t4, v4)


# TEST 5: Account removed
def t5():
    SFAccount.objects.using('salesforce').filter(name='NewStartup Inc').delete()

def v5(r, a):
    return any(x.change_type == 'account_removed' and x.entity_name == 'NewStartup Inc' for x in a)

test(5, "Account removed (NewStartup Inc)", t5, v5)


# TEST 6: New contact added
def t6():
    acct = SFAccount.objects.using('salesforce').get(name='TechCorp')
    SFContact.objects.using('salesforce').create(
        name='Rajesh Kumar', title='CTO',
        phone='555-0000', email='rajesh@techcorp.com',
        account=acct, coach=acct.coach
    )

def v6(r, a):
    return any(x.change_type == 'contact_added' and 'Rajesh' in x.entity_name for x in a)

test(6, "New contact added (Rajesh Kumar)", t6, v6)


# TEST 7: Contact removed
def t7():
    SFContact.objects.using('salesforce').filter(name='Rajesh Kumar').delete()

def v7(r, a):
    return any(x.change_type == 'contact_removed' and 'Rajesh' in x.entity_name for x in a)

test(7, "Contact removed (Rajesh Kumar)", t7, v7)


# TEST 8: Contact reassigned to different coach
def t8():
    con = SFContact.objects.using('salesforce').filter(coach=carol).first()
    if con:
        con.coach = eve
        con.save(using='salesforce')

def v8(r, a):
    return any(x.change_type == 'contact_reassigned' for x in a)

test(8, "Contact reassigned from Carol to Eve", t8, v8)


# TEST 9: Contact moved to different account
def t9():
    con = SFContact.objects.using('salesforce').filter(coach=eve).first()
    hp = SFAccount.objects.using('salesforce').get(name='HealthPlus')
    if con:
        old_name = con.name
        con.account = hp
        con.save(using='salesforce')
        print(f"  Moved {old_name} to HealthPlus")

test(9, "Contact moved to different account", t9)


# TEST 10: Coach details updated
def t10():
    eve.email = 'eve.updated@coaching.com'
    eve.save(using='salesforce')

def v10(r, a):
    return any(x.change_type == 'coach_updated' for x in a)

test(10, "Coach details updated (Eve email changed)", t10, v10)


# TEST 11: Account details updated
def t11():
    tc = SFAccount.objects.using('salesforce').get(name='TechCorp')
    tc.industry = 'AI & Machine Learning'
    tc.save(using='salesforce')

def v11(r, a):
    return any(x.change_type == 'account_updated' for x in a)

test(11, "Account updated (TechCorp industry changed)", t11, v11)


# TEST 12: No changes - zero audit records
def t12():
    pass

def v12(r, a):
    return r.changes_detected == 0 and len(a) == 0

test(12, "No changes - zero audit records expected", t12, v12)


# TEST 13: New coach added
def t13():
    SFCoach.objects.using('salesforce').create(
        name='Priya Sharma', email='priya@coaching.com',
        is_active=True, active_clients=0
    )

def v13(r, a):
    return any(x.change_type == 'coach_added' and 'Priya' in x.entity_name for x in a)

test(13, "New coach added (Priya Sharma)", t13, v13)


# TEST 14: Coach removed entirely
def t14():
    SFCoach.objects.using('salesforce').filter(name='Priya Sharma').delete()

def v14(r, a):
    return any(x.change_type == 'coach_removed' and 'Priya' in x.entity_name for x in a)

test(14, "Coach removed (Priya Sharma)", t14, v14)


# TEST 15: Bulk reassignment
def t15():
    SFAccount.objects.using('salesforce').filter(coach=alice).update(coach=eve)
    SFContact.objects.using('salesforce').filter(coach=alice).update(coach=eve)

def v15(r, a):
    return any(x.change_type in ('account_reassigned', 'contact_reassigned') for x in a)

test(15, "Bulk reassignment: all Alice accounts to Eve", t15, v15)


# TEST 16: Access control - coach can only see own data
print("TEST 16: Access control enforcement")
local_eve = Coach.objects.filter(name='Eve Davis').first()
local_alice = Coach.objects.filter(name='Alice Johnson').first()
if local_eve and local_alice:
    eve_accounts = Account.objects.filter(coach=local_eve).count()
    alice_accounts = Account.objects.filter(coach=local_alice).count()
    print(f"  Eve sees {eve_accounts} accounts, Alice sees {alice_accounts} accounts")
    # After test 15, Alice should have 0 accounts (all moved to Eve)
    passed = alice_accounts == 0
    print(f"  Alice lost access after reassignment: {'PASS' if passed else 'FAIL'}")
    results.append((16, "Access control: Alice loses access after reassignment", "PASS" if passed else "FAIL", 0))
else:
    print("  Could not find coaches")
    results.append((16, "Access control", "FAIL", 0))
print()


# TEST 17: Sync with no changes produces zero records (second run)
print("TEST 17: Second no-change sync")
r = run_sync()
audits = AuditRecord.objects.filter(sync=r)
passed = r.changes_detected == 0 and audits.count() == 0
print(f"  Changes: {r.changes_detected}, Audits: {audits.count()}")
print(f"  RESULT: {'PASS' if passed else 'FAIL'}")
results.append((17, "Second no-change sync produces zero records", "PASS" if passed else "FAIL", 0))
print()


# SUMMARY
print("=" * 65)
print("EDGE CASE TEST SUMMARY")
print("=" * 65)
for num, name, status, changes in results:
    icon = "PASS" if status == "PASS" else "FAIL"
    print(f"  [{icon}] Test {num}: {name} ({changes} changes)")

passed_count = sum(1 for r in results if r[2] == "PASS")
total = len(results)
print()
print(f"  {passed_count}/{total} tests passed")
