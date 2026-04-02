"""
Compares source (Salesforce) data with local (app) data.
Returns a list of change dicts without modifying any data.
"""


def detect_coach_changes(sf_coaches, local_coaches):
    """Compare coaches. Returns list of change dicts."""
    changes = []
    sf_map = {str(c.sf_id): c for c in sf_coaches}
    local_map = {str(c.sf_id): c for c in local_coaches}

    # Added
    for sf_id, sf_coach in sf_map.items():
        if sf_id not in local_map:
            changes.append({
                "change_type": "coach_added",
                "entity_type": "coach",
                "entity_sf_id": sf_coach.sf_id,
                "entity_name": sf_coach.name,
                "before_state": None,
                "after_state": {
                    "name": sf_coach.name,
                    "email": sf_coach.email,
                    "is_active": sf_coach.is_active,
                },
                "coach_name": sf_coach.name,
            })

    # Removed
    for sf_id, local_coach in local_map.items():
        if sf_id not in sf_map:
            changes.append({
                "change_type": "coach_removed",
                "entity_type": "coach",
                "entity_sf_id": local_coach.sf_id,
                "entity_name": local_coach.name,
                "before_state": {
                    "name": local_coach.name,
                    "email": local_coach.email,
                    "is_active": local_coach.is_active,
                },
                "after_state": None,
                "coach_name": local_coach.name,
            })

    # Updated
    for sf_id in sf_map:
        if sf_id in local_map:
            sf_c = sf_map[sf_id]
            local_c = local_map[sf_id]
            before = {}
            after = {}
            for field in ["name", "email", "active_clients", "is_active"]:
                sf_val = getattr(sf_c, field)
                local_val = getattr(local_c, field)
                if sf_val != local_val:
                    before[field] = local_val
                    after[field] = sf_val
            if before:
                changes.append({
                    "change_type": "coach_updated",
                    "entity_type": "coach",
                    "entity_sf_id": sf_c.sf_id,
                    "entity_name": sf_c.name,
                    "before_state": before,
                    "after_state": after,
                    "coach_name": sf_c.name,
                })

    return changes


def detect_account_changes(sf_accounts, local_accounts, sf_coaches_map, local_coaches_map):
    """Compare accounts. Detects add/remove/reassign/update."""
    changes = []
    sf_map = {str(a.sf_id): a for a in sf_accounts}
    local_map = {str(a.sf_id): a for a in local_accounts}

    for sf_id, sf_acc in sf_map.items():
        if sf_id not in local_map:
            coach_name = sf_coaches_map.get(str(sf_acc.coach_id), "Unknown") if sf_acc.coach_id else "Unassigned"
            changes.append({
                "change_type": "account_added",
                "entity_type": "account",
                "entity_sf_id": sf_acc.sf_id,
                "entity_name": sf_acc.name,
                "before_state": None,
                "after_state": {
                    "name": sf_acc.name,
                    "industry": sf_acc.industry,
                    "coach": coach_name,
                },
                "coach_name": coach_name,
                "account_name": sf_acc.name,
            })
        else:
            local_acc = local_map[sf_id]

            # Check reassignment
            sf_coach_sfid = _get_coach_sf_id(sf_acc, sf_coaches_map)
            local_coach_sfid = _get_coach_sf_id_local(local_acc, local_coaches_map)

            if sf_coach_sfid != local_coach_sfid:
                old_coach = local_coaches_map.get(local_coach_sfid, "Unassigned")
                new_coach = sf_coaches_map.get(sf_coach_sfid, "Unassigned")
                changes.append({
                    "change_type": "account_reassigned",
                    "entity_type": "account",
                    "entity_sf_id": sf_acc.sf_id,
                    "entity_name": sf_acc.name,
                    "before_state": {"coach": old_coach},
                    "after_state": {"coach": new_coach},
                    "coach_name": new_coach,
                    "account_name": sf_acc.name,
                })

            # Check other field updates
            before = {}
            after = {}
            for field in ["name", "industry", "website"]:
                sf_val = getattr(sf_acc, field)
                local_val = getattr(local_acc, field)
                if sf_val != local_val:
                    before[field] = local_val
                    after[field] = sf_val
            if before:
                changes.append({
                    "change_type": "account_updated",
                    "entity_type": "account",
                    "entity_sf_id": sf_acc.sf_id,
                    "entity_name": sf_acc.name,
                    "before_state": before,
                    "after_state": after,
                    "account_name": sf_acc.name,
                })

    for sf_id, local_acc in local_map.items():
        if sf_id not in sf_map:
            old_coach = local_coaches_map.get(
                _get_coach_sf_id_local(local_acc, local_coaches_map), "Unknown"
            )
            changes.append({
                "change_type": "account_removed",
                "entity_type": "account",
                "entity_sf_id": local_acc.sf_id,
                "entity_name": local_acc.name,
                "before_state": {
                    "name": local_acc.name,
                    "coach": old_coach,
                },
                "after_state": None,
                "coach_name": old_coach,
                "account_name": local_acc.name,
            })

    return changes


def detect_contact_changes(sf_contacts, local_contacts, sf_coaches_map, local_coaches_map):
    """Compare contacts. Detects add/remove/reassign/update."""
    changes = []
    sf_map = {str(c.sf_id): c for c in sf_contacts}
    local_map = {str(c.sf_id): c for c in local_contacts}

    for sf_id, sf_con in sf_map.items():
        if sf_id not in local_map:
            coach_name = sf_coaches_map.get(str(sf_con.coach_id), "Unknown") if sf_con.coach_id else "Unassigned"
            changes.append({
                "change_type": "contact_added",
                "entity_type": "contact",
                "entity_sf_id": sf_con.sf_id,
                "entity_name": sf_con.name,
                "before_state": None,
                "after_state": {
                    "name": sf_con.name,
                    "title": sf_con.title,
                    "coach": coach_name,
                },
                "coach_name": coach_name,
            })
        else:
            local_con = local_map[sf_id]

            sf_coach_sfid = _get_coach_sf_id(sf_con, sf_coaches_map)
            local_coach_sfid = _get_coach_sf_id_local(local_con, local_coaches_map)

            if sf_coach_sfid != local_coach_sfid:
                old_coach = local_coaches_map.get(local_coach_sfid, "Unassigned")
                new_coach = sf_coaches_map.get(sf_coach_sfid, "Unassigned")
                changes.append({
                    "change_type": "contact_reassigned",
                    "entity_type": "contact",
                    "entity_sf_id": sf_con.sf_id,
                    "entity_name": sf_con.name,
                    "before_state": {"coach": old_coach},
                    "after_state": {"coach": new_coach},
                    "coach_name": new_coach,
                })

            before = {}
            after = {}
            for field in ["name", "title", "phone", "email"]:
                sf_val = getattr(sf_con, field)
                local_val = getattr(local_con, field)
                if sf_val != local_val:
                    before[field] = local_val
                    after[field] = sf_val
            if before:
                changes.append({
                    "change_type": "contact_updated",
                    "entity_type": "contact",
                    "entity_sf_id": sf_con.sf_id,
                    "entity_name": sf_con.name,
                    "before_state": before,
                    "after_state": after,
                })

    for sf_id, local_con in local_map.items():
        if sf_id not in sf_map:
            old_coach = local_coaches_map.get(
                _get_coach_sf_id_local(local_con, local_coaches_map), "Unknown"
            )
            changes.append({
                "change_type": "contact_removed",
                "entity_type": "contact",
                "entity_sf_id": local_con.sf_id,
                "entity_name": local_con.name,
                "before_state": {
                    "name": local_con.name,
                    "title": local_con.title,
                    "coach": old_coach,
                },
                "after_state": None,
                "coach_name": old_coach,
            })

    return changes


def detect_assignment_changes(sf_assignments, local_assignments, sf_coaches_map, local_coaches_map):
    """Compare assignments."""
    changes = []
    sf_map = {str(a.sf_id): a for a in sf_assignments}
    local_map = {str(a.sf_id): a for a in local_assignments}

    for sf_id, sf_asgn in sf_map.items():
        if sf_id not in local_map:
            coach_name = sf_coaches_map.get(str(sf_asgn.coach_id), "Unknown")
            changes.append({
                "change_type": "assignment_added",
                "entity_type": "assignment",
                "entity_sf_id": sf_asgn.sf_id,
                "entity_name": f"{coach_name} -> Contact#{sf_asgn.contact_id}",
                "before_state": None,
                "after_state": {"status": sf_asgn.status, "coach": coach_name},
                "coach_name": coach_name,
            })
        else:
            local_asgn = local_map[sf_id]
            if sf_asgn.status != local_asgn.status:
                changes.append({
                    "change_type": "assignment_updated",
                    "entity_type": "assignment",
                    "entity_sf_id": sf_asgn.sf_id,
                    "entity_name": f"Assignment {sf_asgn.sf_id}",
                    "before_state": {"status": local_asgn.status},
                    "after_state": {"status": sf_asgn.status},
                })

    for sf_id, local_asgn in local_map.items():
        if sf_id not in sf_map:
            changes.append({
                "change_type": "assignment_removed",
                "entity_type": "assignment",
                "entity_sf_id": local_asgn.sf_id,
                "entity_name": f"Assignment {local_asgn.sf_id}",
                "before_state": {"status": local_asgn.status},
                "after_state": None,
            })

    return changes


# --- Helpers ---

def _get_coach_sf_id(sf_obj, sf_coaches_map):
    """Get the sf_id of the coach linked to a source object (via FK id)."""
    if sf_obj.coach_id is None:
        return None
    return str(sf_obj.coach_id)


def _get_coach_sf_id_local(local_obj, local_coaches_map):
    """Get the sf_id string of the coach linked to a local object."""
    if local_obj.coach_id is None:
        return None
    return str(local_obj.coach_id)
