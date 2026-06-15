import requests

def find_ticket(args):

    tickets = args[0]

    ticket_type = tickets.get("ticket_type")
    priority = tickets.get("priority")

    return {
            "ticket_type": ticket_type,
            "priority" : priority
    }


def get_sla_definition(args):
    ticket_type = args
 
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
    calendar_details = args
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
        "response_minutes" : response_minutes
    }

def calculate_deadline(args):

    response_minutes = args[0]
    resolution_minutes = args[1]
    working_date = args[2]

    current_date = datetime.now().date()

    response_deadline = None
    resolution_deadline = None

    if current_date == working_date:
        current_time = datetime.now().strftime("%H:%M:%S")
        response_deadline = current_time + response_minutes
        resolution_deadline = current_time + resolution_minutes
    else:
        resolution_deadline = "09:00" + resolution_minutes
        response_deadline = "09:00" + response_minutes

    return{
        "response_deadline" : response_deadline,
        "resolution_deadline" : resolution_deadline
    }

