import requests

def find_ticket(args):

    tickets = args[0][0]
    # [
    #     []
    # ]

    ticket_type = tickets.get("ticket_type")
    priority = tickets.get("priority")

    return {
            "ticket_type": ticket_type,
            "priority" : priority
    }


def get_sla_definition(args):
    ticket_type = args[0]
 
    api_url = "https://dev.assisto.tech/llm_api/execute_workflow"
 
    payload = {
        "workflow_name": "get_mongo_master_with_cond",
        "db_name":       "sla_engine",
        "master_name":   "sla_definitions",
        "filters": {
            "ticket_type": ticket_type
        },
    }
 
    response = requests.post(api_url, json=payload, timeout=30)
    response_json = response.json()
 
    data_array = response_json.get("functions_get_mongo_master_output_data", [])
 
    definition_id = []
    for sla_engine in data_array:
        definition_id.append({
            "sla_definition_id": sla_engine["sla_definition_id"],
        })
 
    return {"definition_id": definition_id}

def get_calendar_details(args):
    calendar_details = args[0][0]
    working_days = calendar_details.get('working_days')
    start_time=calendar_details.get('start_time')
    end_time=calendar_details.get('end_time')

    return {
        "working_days": working_days,
        "start_time": start_time,
        "end_time": end_time
    }

from datetime import datetime, timedelta

def get_working_day(args):

    holidays = args[0]

    current_date = datetime.strptime(
        args["current_date"],
        "%Y-%m-%d"
    ).date()

    holiday_dates = []

    for holiday in holidays:
        holiday_dates.append(holiday["date"])

    while True:

        working_date = current_date.strftime("%Y-%m-%d")

        # Skip Saturday and Sunday
        if current_date.weekday() in [5, 6]:
            current_date += timedelta(days=1)
            continue

        # Skip holidays
        if working_date in holiday_dates:
            current_date += timedelta(days=1)
            continue

        break

    return {
        "working_date": working_date
    }

def get_sla_level(args):

    sla_level = args

    resolution_minutes = sla_level.get("resolution_minutes")
    response_minutes = sla_level.get("response_minutes")

    return{
        "resolution_minutes" : resolution_minutes,
        "response_minutes" : response_minutes,
    }

# def calculate_deadline(args):

#     response_minutes = args[0]
#     resolution_minutes = args[1]
#     working_date = args[2]
#     created_at = args[3]

#     current_date = datetime.now().date()

#     response_deadline = None
#     resolution_deadline = None

#     if current_date == working_date:
#         current_time = datetime.now().strftime("%H:%M:%S")
#         response_deadline = current_time + response_minutes
#         resolution_deadline = current_time + resolution_minutes
#     else:
#         resolution_deadline = working_date + resolution_minutes
#         response_deadline = working_date + response_minutes

#     return{
#         "updated_data" : {"sla" :  
#           {
#               "resolution_due": "resolution_deadline", 
#               "response_due": "response_deadline"
#           }
#         }
#     }

# from datetime import datetime, timedelta

from datetime import datetime, timedelta

def calculate_deadline(args):

    response_minutes = int(args[0])
    resolution_minutes = int(args[1])
    created_at = args[3]

    created_at_dt = datetime.fromisoformat(created_at)

    response_deadline = created_at_dt + timedelta(minutes=response_minutes)
    resolution_deadline = created_at_dt + timedelta(minutes=resolution_minutes)

    return {
        "updated_data": {
            "sla": {
                "resolution_due": {
                    "$date": resolution_deadline.strftime("%Y-%m-%dT%H:%M:%SZ")
                },
                "response_due": {
                    "$date": response_deadline.strftime("%Y-%m-%dT%H:%M:%SZ")
                }
            }
        }
    }


from datetime import datetime

def dashboard_metrics(args):
    """
    Calculate dashboard metrics for ticket and SLA monitoring.

    Input:
    - args[0]: List of ticket documents

    Metrics:
    - total_tickets: Total number of tickets in the system
    - active_slas: Tickets whose response and resolution SLAs are still within due time
    - breached_slas: Tickets where either response SLA or resolution SLA has been breached
    - response_sla_breached: Tickets that missed the response SLA
    - resolution_sla_breached: Tickets that missed the resolution SLA
    """

    # Ticket collection passed by workflow
    tickets = args[0][0]

    # Total number of tickets returned from the collection
    total_tickets = len(tickets)

    # Count of tickets operating within SLA timelines
    active_slas = 0

    # Count of tickets where either SLA has been breached
    breached_slas = 0

    # Count of tickets that breached response SLA
    response_sla_breached = 0

    # Count of tickets that breached resolution SLA
    resolution_sla_breached = 0

    # Current UTC timestamp used for SLA comparison
    now = datetime.utcnow()

    # Process each ticket individually
    for ticket in tickets:

        # Ignore inactive tickets as they are no longer part of SLA tracking
        if not ticket.get("is_active"):
            continue

        # Retrieve SLA details from the ticket
        sla = ticket.get("sla", {})

        # Response SLA deadline
        response_due = sla.get("response_due")

        # Resolution SLA deadline
        resolution_due = sla.get("resolution_due")

        # Flags used to determine whether SLAs are breached
        response_breached = False
        resolution_breached = False

        # Check response SLA breach
        if response_due:
            response_due_time = datetime.fromisoformat(
                response_due.replace("Z", "")
            )

            if response_due_time <= now:
                response_breached = True
                response_sla_breached += 1

        # Check resolution SLA breach
        if resolution_due:
            resolution_due_time = datetime.fromisoformat(
                resolution_due.replace("Z", "")
            )

            if resolution_due_time <= now:
                resolution_breached = True
                resolution_sla_breached += 1

        # A ticket is considered breached if either
        # response SLA or resolution SLA has been missed
        if response_breached or resolution_breached:
            breached_slas += 1
        else:
            active_slas += 1

    # Return dashboard summary metrics
    return {
        "total_tickets": total_tickets,
        "active_slas": active_slas,
        "breached_slas": breached_slas,
        "response_sla_breached": response_sla_breached,
        "resolution_sla_breached": resolution_sla_breached
    }

from datetime import datetime

def process_sla_breaches(args):
    """
    Process all active tickets and identify SLA breaches.

    Input:
    - args[0]: List of ticket documents

    Output:
    - List of ticket updates that need to be applied to the database
    """

    # Ticket collection passed by workflow
    tickets = args[0][0]

    # Store only tickets that require updates
    updated_data = []

    # Current UTC timestamp used for SLA comparison
    now = datetime.utcnow()

    # Process each ticket individually
    for ticket in tickets:

        # Ignore inactive tickets
        if not ticket.get("is_active"):
            continue

        sla = ticket.get("sla", {})

        response_due = sla.get("response_due")
        resolution_due = sla.get("resolution_due")

        latest_status = ticket.get("latest_status")

        response_breached = False
        resolution_breached = False

        new_status = None
        remarks = None

        if response_due:
            response_due_time = datetime.fromisoformat(
                response_due.replace("Z", "")
            )

            if response_due_time <= now & latest_status == "open":
                response_breached = True

        if resolution_due:
            resolution_due_time = datetime.fromisoformat(
                resolution_due.replace("Z", "")
            )

            if resolution_due_time <= now and (latest_status != "closed" or latest_status != "resolved"):
                resolution_breached = True

        if resolution_breached:
            new_status = "resolution_sla_breached"
            remarks = "Resolution SLA breached by scheduled SLA monitor"

        elif response_breached:
            new_status = "response_sla_breached"
            remarks = "Response SLA breached by scheduled SLA monitor"

        if not new_status:
            continue

        if latest_status == new_status:
            continue

        updated_data.append({
            "ticket_id": ticket["id"],
            "updated_data": {
                "latest_status": new_status,
                "updated_by": "sla_cron_job",
                "updated_at": now.strftime("%Y-%m-%dT%H:%M:%S"),
                "status_history": ticket.get("status_history", []) + [{
                    "status": new_status,
                    "remarks": remarks
                }]
            }
        })

    # Return all updates to be applied
    return {
        "updated_data": updated_data
    }