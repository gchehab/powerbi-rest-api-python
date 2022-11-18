import requests
import datetime
import logging
import re
import zipfile
import io
import json

token = { "bearer": None, "expiration": None }
credentials = { "client_id": None, "username": None, "password": None, "tenant_id": None, "client_secret": None }

log = logging.getLogger()
console = logging.StreamHandler()
console.setFormatter(logging.Formatter("%(asctime)s\t%(levelname)s -- %(message)s"))
log.addHandler(console)
log.setLevel(20)

HTTP_OK = 200
HTTP_ACCEPTED = 202

def connect(client_id: str, username: str, password: str, tenant_id: str = "common", client_secret: str = None) -> None:
    global token
    global credentials

    if client_secret:
        body = {
            "grant_type": "client_credentials",
            "resource": "https://analysis.windows.net/powerbi/api",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username,
            "password": password
        }
    else:
        body = {
            "grant_type": "password",
            "resource": "https://analysis.windows.net/powerbi/api",
            "client_id": client_id,
            "username": username,
            "password": password
        }

    headers = { "Content-Type": "application/x-www-form-urlencoded" }
    response = requests.post("https://login.microsoftonline.com/{}/oauth2/token".format(tenant_id), headers = headers, data = body)

    if response.status_code == HTTP_OK:
        set_credentials(client_id, username, password, tenant_id, client_secret)
        set_token(response.json()["access_token"])
        log.info("Connected to the Power BI REST API with {}".format(username))
    else:
        set_credentials(None, None, None, None, None)
        set_token(None)
        log.error("Error {} -- Something went wrong when trying to retrieve the token from the REST API".format(response.status_code))

def verify_token() -> bool:
    global token
    if token["bearer"] == None:
        log.error("Error 401 -- Please connect to the Power BI REST API with the connect() function before")
        return False
    else:
        if token["expiration"] < datetime.datetime.now():
            connect(credentials["client_id"], credentials["username"], credentials["password"], credentials["tenant_id"], credentials["client_secret"])
            return True
        else:
            return True

def get_token() -> dict:
    global token
    return token

def set_token(bearer: str) -> None:
    global token
    token["bearer"] = "Bearer {}".format(bearer)
    token["expiration"] = datetime.datetime.now() + datetime.timedelta(hours = 1)

def set_credentials(client_id: str, username: str, password: str, tenant_id: str, client_secret: str) -> None:
    global credentials
    credentials["client_id"] = client_id
    credentials["username"] = username
    credentials["password"] = password
    credentials["tenant_id"] = tenant_id
    credentials["client_secret"] = client_secret

# Workspace
def get_workspaces() -> list:
    global token
    if(not verify_token()): return None

    headers = { "Authorization": token["bearer"] }
    response = requests.get("https://api.powerbi.com/v1.0/myorg/groups", headers = headers)

    if response.status_code == HTTP_OK:
        return response.json()["value"]
    else:
        log.error("Error {} -- Something went wrong when trying to retrieve the list of workspaces you have access".format(response.status_code))
        return None

def get_workspace(workspace_id: str) -> list:
    global token
    if(not verify_token()): return None

    headers = { "Authorization": token["bearer"] }
    response = requests.get("https://api.powerbi.com/v1.0/myorg/groups", headers = headers)

    if response.status_code == HTTP_OK:
        ws = [result for result in response.json()["value"] if result["id"] == workspace_id]
        if(len(ws) > 0): return ws[0]
        else: return None
    else:
        log.error("Error {} -- Something went wrong when trying to retrieve the workspace {}".format(response.status_code, workspace_id))
        return None

def create_workspace(workspace_name: str, new: bool = False) -> dict:
    global token
    if(not verify_token()): return None

    headers = { "Authorization": token["bearer"] }
    body = { "name": workspace_name }

    if new:
        response = requests.post("https://api.powerbi.com/v1.0/myorg/groups?workspaceV2=True", headers = headers, data = body)

        if response.status_code == HTTP_OK:
            result = response.json()
            return { "id": result["id"], "isOnDedicatedCapacity": result["isOnDedicatedCapacity"], "name": result["name"] }
        else:
            log.error("Error {} -- Something went wrong when trying to create a new workspace V2 called {}".format(response.status_code, workspace_name))
            return None
    else:
        response = requests.post("https://api.powerbi.com/v1.0/myorg/groups", headers = headers, data = body)

        if response.status_code == HTTP_OK:
            result = response.json()
            return { "id": result["id"], "isReadOnly": result["isReadOnly"], "isOnDedicatedCapacity": result["isOnDedicatedCapacity"], "name": result["name"] }
        else:
            log.error("Error {} -- Something went wrong when trying to create a new workspace called {}".format(response.status_code, workspace_name))
            return None

def delete_workspace(workspace_id: str) -> dict:
    global token
    if(not verify_token()): return None

    headers = { "Authorization": token["bearer"] }
    response = requests.delete("https://api.powerbi.com/v1.0/myorg/groups/{}".format(workspace_id), headers = headers)

    if response.status_code == HTTP_OK:
        return { "response": response.status_code }
    else:
        log.error("Error {} -- Something went wrong when trying to delete the workspace {}".format(response.status_code, workspace_id))
        return None

def get_users_in_workspace(workspace_id: str) -> list:
    global token
    if(not verify_token()): return None

    headers = { "Authorization": token["bearer"] }
    response = requests.get("https://api.powerbi.com/v1.0/myorg/groups/{}/users".format(workspace_id), headers = headers)

    if response.status_code == HTTP_OK:
        return response.json()["value"]
    else:
        log.error("Error {} -- Something went wrong when trying to retrieve the list of users in the workspace {}".format(response.status_code, workspace_id))
        return None

def add_user_to_workspace(workspace_id: str, email: str, access: str = "Member") -> dict:
    global token
    if(not verify_token()): return None
    
    if(access in ["Admin", "Contributor", "Member"]):
        headers = { "Authorization": token["bearer"] }
        body = { "userEmailAddress": email, "groupUserAccessRight": access }
        response = requests.post("https://api.powerbi.com/v1.0/myorg/groups/{}/users".format(workspace_id), headers = headers, data = body)

        if response.status_code == HTTP_OK:
            return { "response": response.status_code }
        else:
            log.error("Error {} -- Something went wrong when trying to add {} in the workspace {}".format(response.status_code, email, workspace_id))
            return None
    else:
        log.error("Error 400 -- Please, make sure the access parameter is either \"Admin\", \"Contributor\" or \"Member\"")
        return None

def delete_user_from_workspace(workspace_id: str, email: str) -> dict:
    global token
    if(not verify_token()): return None

    headers = { "Authorization": token["bearer"] }
    response = requests.delete("https://api.powerbi.com/v1.0/myorg/groups/{}/users/{}".format(workspace_id, email), headers = headers)

    if response.status_code == HTTP_OK:
        return { "response": response.status_code }
    else:
        log.error("Error {} -- Something went wrong when trying to delete the user {} from the workspace {}".format(response.status_code, email, workspace_id))
        return None

def update_user_in_workspace(workspace_id: str, email: str, access: str = "Member") -> dict:
    global token
    if(not verify_token()): return None
    
    if(access in ["Admin", "Contributor", "Member"]):
        headers = { "Authorization": token["bearer"] }
        body = { "userEmailAddress": email, "groupUserAccessRight": access }
        response = requests.put("https://api.powerbi.com/v1.0/myorg/groups/{}/users".format(workspace_id), headers = headers, data = body)

        if response.status_code == HTTP_OK:
            return { "response": response.status_code }
        else:
            log.error("Error {} -- Something went wrong when trying to update {} in the workspace {}".format(response.status_code, email, workspace_id))
            return None
    else:
        log.error("Error 400 -- Please, make sure the access parameter is either \"Admin\", \"Contributor\" or \"Member\"")
        return None

# Report
def get_reports(workspace_id: str) -> list:
    global token
    if(not verify_token()): return None

    headers = { "Authorization": token["bearer"] }
    response = requests.get("https://api.powerbi.com/v1.0/myorg/groups/{}/reports".format(workspace_id), headers = headers)

    if response.status_code == HTTP_OK:
        return response.json()["value"]
    else:
        log.error("Error {} -- Something went wrong when trying to retrieve the list of reports in the workspace {}".format(response.status_code, workspace_id))
        return None

def get_report(workspace_id: str, report_id: str) -> list:
    global token
    if(not verify_token()): return None

    headers = { "Authorization": token["bearer"] }
    response = requests.get("https://api.powerbi.com/v1.0/myorg/groups/{}/reports/{}".format(workspace_id, report_id), headers = headers)

    if response.status_code == HTTP_OK:
        return response.json()
    else:
        log.error("Error {} -- Something went wrong when trying to retrieve the report {} in the workspace {}".format(response.status_code, report_id, workspace_id))
        return None

def delete_report(workspace_id: str, report_id: str) -> dict:
    global token
    if(not verify_token()): return None

    headers = { "Authorization": token["bearer"] }
    response = requests.delete("https://api.powerbi.com/v1.0/myorg/groups/{}/reports/{}".format(workspace_id, report_id), headers = headers)

    if response.status_code == HTTP_OK:
        return { "response": response.status_code }
    else:
        log.error("Error {} -- Something went wrong when trying to delete the report {} in the workspace {}".format(response.status_code, report_id, workspace_id))
        return None

def export_report(workspace_id: str, report_id: str, out_file: str = None) -> dict:
    global token
    if(not verify_token()): return None

    headers = { "Authorization": token["bearer"] }
    response = requests.get("https://api.powerbi.com/v1.0/myorg/groups/{}/reports/{}/export".format(workspace_id, report_id), headers = headers)

    if response.status_code == HTTP_OK:
        if out_file != None:
            with open(out_file, "wb") as file: file.write(response.content)
            return { "response": response.status_code }
        else:
            return response.content
    else:
        log.error("Error {} -- Something went wrong when trying to export the report {} in the workspace {}".format(response.status_code, report_id, workspace_id))
        return None

def import_report(workspace_id: str, report_name: str, in_file: str, name_conflict: str = "CreateOrOverwrite") -> dict:
    global token
    if(not verify_token()): return None

    if(name_conflict in ["CreateOrOverwrite", "GenerateUniqueName", "Ignore", "Overwrite"]):
        headers = { "Authorization": token["bearer"], "Content-Type": "multipart/form-data" }
        file = { "file": open(in_file, "rb") }
        response = requests.post("https://api.powerbi.com/v1.0/myorg/groups/{}/imports?datasetDisplayName={}&nameConflict={}".format(workspace_id, report_name, name_conflict), headers = headers, files = file)

        if response.status_code == HTTP_ACCEPTED:
            return response.json()
        else:
            log.error("Error {} -- Something went wrong when trying to import the report {} in the workspace {}".format(response.status_code, in_file, workspace_id))
            return None
    else:
        log.error("Error 400 -- Please, make sure the name_conflict parameter is either \"CreateOrOverwrite\", \"GenerateUniqueName\", \"Ignore\" or \"Overwrite\"")
        return None

def clone_report(workspace_id: str, report_id: str, dest_report_name: str, dest_workspace_id: str = None) -> dict:
    global token
    if(not verify_token()): return None
    
    headers = { "Authorization": token["bearer"] }
    if dest_workspace_id: body = { "name": dest_report_name, "targetWorkspaceId": dest_workspace_id }
    else: body = { "name": dest_report_name }

    response = requests.post("https://api.powerbi.com/v1.0/myorg/groups/{}/reports/{}/clone".format(workspace_id, report_id), headers = headers, data = body)

    if response.status_code == HTTP_OK:
        return { "response": response.status_code }
    else:
        log.error("Error {} -- Something went wrong when trying to clone the report {} in the workspace {}".format(response.status_code, report_id, workspace_id))
        return None

# Dataset
def get_datasets(workspace_id: str) -> list:
    global token
    if(not verify_token()): return None

    headers = { "Authorization": token["bearer"] }
    response = requests.get("https://api.powerbi.com/v1.0/myorg/groups/{}/datasets".format(workspace_id), headers = headers)

    if response.status_code == HTTP_OK:
        return response.json()["value"]
    else:
        log.error("Error {} -- Something went wrong when trying to retrieve the list of datasets in the workspace {}".format(response.status_code, workspace_id))
        return None

def get_dataset(workspace_id: str, dataset_id: str) -> list:
    global token
    if(not verify_token()): return None

    headers = { "Authorization": token["bearer"] }
    response = requests.get("https://api.powerbi.com/v1.0/myorg/groups/{}/datasets/{}".format(workspace_id, dataset_id), headers = headers)

    if response.status_code == HTTP_OK:
        return response.json()["value"]
    else:
        log.error("Error {} -- Something went wrong when trying to retrieve the dataset {} in the workspace {}".format(response.status_code, dataset_id, workspace_id))
        return None

def delete_dataset(workspace_id: str, dataset_id: str) -> dict:
    global token
    if(not verify_token()): return None

    headers = { "Authorization": token["bearer"] }
    response = requests.delete("https://api.powerbi.com/v1.0/myorg/groups/{}/datasets/{}".format(workspace_id, dataset_id), headers = headers)

    if response.status_code == HTTP_OK:
        return { "response": response.status_code }
    else:
        log.error("Error {} -- Something went wrong when trying to delete the dataset {} in the workspace {}".format(response.status_code, dataset_id, workspace_id))
        return None

def refresh_dataset(workspace_id: str, dataset_id: str, notify_option: str = "NoNotification") -> dict:
    global token
    if(not verify_token()): return None

    if(notify_option in ["MailOnCompletion", "MailOnFailure", "NoNotification"]):
        headers = { "Authorization": token["bearer"] }
        body = { "notifyOption": notify_option }
        response = requests.post("https://api.powerbi.com/v1.0/myorg/groups/{}/datasets/{}/refreshes".format(workspace_id, dataset_id), headers = headers, data = body)

        if response.status_code == HTTP_ACCEPTED:
            return { "response": response.status_code }
        else:
            log.error("Error {} -- Something went wrong when trying to refresh the dataset {} in the workspace {}".format(response.status_code, dataset_id, workspace_id))
            return None
    else:
        log.error("Error 400 -- Please, make sure the notify_option parameter is either \"MailOnCompletion\", \"MailOnFailure\" or \"NoNotification\"")
        return None

# Admin
def get_audit_logs(start_date: str, end_date: str, activity: str = None, user_id: str = None) -> list:
    global token
    if(not verify_token()): return None

    date_regex = r"^\d\d\d\d-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01]) (00|1[0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9])$"
    start_date_verification = re.search(date_regex, start_date)
    end_date_verification = re.search(date_regex, end_date)
    
    if(start_date_verification and end_date_verification):
        start_date_value = datetime.datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%dT%H:%M:%S.000Z")
        end_date_value = datetime.datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%dT%H:%M:%S.000Z")

        headers = { "Authorization": token["bearer"] }
        params = ""

        if activity:
            params += "Activity eq '{}'".format(activity)
        if user_id:
            if params != "": params += " and "
            params += "UserId eq '{}'".format(user_id)

        if params == "": url = "https://api.powerbi.com/v1.0/myorg/admin/activityevents?startDateTime='{}'&endDateTime='{}'".format(start_date_value, end_date_value)
        else: url = "https://api.powerbi.com/v1.0/myorg/admin/activityevents?startDateTime='{}'&endDateTime='{}'&$filter={}".format(start_date_value, end_date_value, params)

        response = requests.get(url, headers = headers)

        if response.status_code == HTTP_OK:
            logs = []
            while(response.json()["continuationUri"] != None):
                logs += response.json()["activityEventEntities"]
                response = requests.get(response.json()["continuationUri"], headers = headers)

                if response.status_code != HTTP_OK:
                    log.error("Error {} -- Something went wrong when trying to retrieve audit logs from {} to {}".format(response.status_code, start_date, end_date))
                    return None

            return logs
        else:
            log.error("Error {} -- Something went wrong when trying to retrieve audit logs from {} to {}".format(response.status_code, start_date, end_date))
            print(response.json())
            return None
    else:
        log.error("Error 400 -- Please, make sure the dates you gave match the following pattern: YYYY-MM-DD HH:MM:SS")
        return None

# Pages
def get_pages(workspace_id: str,report_id: str) -> list:
    global token
    if(not verify_token()): return None

    headers = { "Authorization": token["bearer"] }
    response = requests.get("https://api.powerbi.com/v1.0/myorg/groups/{}/reports/{}/pages".format(workspace_id, report_id), headers = headers)

    if response.status_code == HTTP_OK:
        return response.json()["value"]
    else:
        log.error("Error {} -- Something went wrong when trying to retrieve the list of pages in report {} in the workspace {}".format(response.status_code, report_id, workspace_id))
        return None

def get_page(workspace_id: str, report_id: str, page_name: str) -> list:
    global token
    if(not verify_token()): return None

    headers = { "Authorization": token["bearer"] }
    response = requests.get("https://api.powerbi.com/v1.0/myorg/groups/{}/reports/{}/pages/{}".format(workspace_id, report_id, page_name), headers = headers)

    if response.status_code == HTTP_OK:
        return response.json()
    else:
        log.error("Error {} -- Something went wrong when trying to retrieve the page {} in the report {} in the workspace {}".format(response.status_code, page_name, report_id, workspace_id))
        return None

# Visuals
def get_visuals(workspace_id: str, report_id: str) -> dict:

    report = export_report(workspace_id, report_id)

    if report is not None:
        input_file = zipfile.ZipFile(io.BytesIO(report))
        config = {name: json.loads(input_file.read(name)) for name in input_file.namelist() if 'Report/Layout' in name}

        res = { 
            page['name']: { 
                json.loads(visual['config'])['name']:json.loads(visual['config']) 
                for visual in page['visualContainers'] 
            } for page in config['Report/Layout']['sections'] 
        }
    
        return res
    else:
        log.error("Error {} -- Something went wrong when trying to retrieve the list of visuals in page {},  in report {} in the workspace {}".format(response.status_code, page_name, report_id, workspace_id))
        return None

# Dashboards
def get_dashboards(workspace_id: str = None) -> list:
    global token
    if(not verify_token()): return None

    headers = { "Authorization": token["bearer"] }
    if workspace_id is not None:
        response = requests.get("https://api.powerbi.com/v1.0/myorg/groups/{}/dashboards".format(workspace_id), headers = headers)
    else:
        response = requests.get("https://api.powerbi.com/v1.0/myorg/dashboards", headers = headers)

    if response.status_code == HTTP_OK:
        return response.json()["value"]
    else:
        log.error("Error {} -- Something went wrong when trying to retrieve the list of dashboard in the workspace {}".format(response.status_code, workspace_id))
        return None

# Tiles
def get_tiles(workspace_id: str = None, dashboard_id:str = None) -> list:
    global token
    if(not verify_token()): return None

    headers = { "Authorization": token["bearer"] }
    if workspace_id is not None:
        response = requests.get("https://api.powerbi.com/v1.0/myorg/groups/{}/dashboards/{}/tiles".format(workspace_id, dashboard_id), headers = headers)
    else:
        response = requests.get("https://api.powerbi.com/v1.0/myorg/dashboards/{}/tiles".format(dashboard_id, dashboard_id), headers = headers)

    if response.status_code == HTTP_OK:
        return response.json()["value"]
    else:
        log.error("Error {} -- Something went wrong when trying to retrieve the list of tiles in dashboard {} in the workspace {}".format(response.status_code, dashboard_id, workspace_id))
        return None      

# Capacities
def get_capacities() -> list:
    global token
    if(not verify_token()): return None

    headers = { "Authorization": token["bearer"] }
    response = requests.get("https://api.powerbi.com/v1.0/myorg/capacities", headers = headers)

    if response.status_code == HTTP_OK:
        return response.json()["value"]
    else:
        log.error("Error {} -- Something went wrong when trying to retrieve the list of capacities".format(response.status_code))
        return None      

def capacity_assignment_status(workspace_id: str = None ) -> dict:
    global token
    if(not verify_token()): return None

    headers = { "Authorization": token["bearer"] }
    if workspace_id is not None:
        response = requests.get("https://api.powerbi.com/v1.0/myorg/groups/{}/CapacityAssignmentStatus".format(workspace_id), headers = headers)
    else:
        log.error("Error -- must specify a workspace id to get capacity status")
        return None
    
    if response.status_code == HTTP_OK:
        return response.json()
    else:
        log.error("Error {} -- Something went wrong when trying to get capacity status of workspace {}".format(response.status_code, workspace_id))
        return None  

def assign_to_capacity(workspace_id: str = None, capacity_id: str = '00000000-0000-0000-0000-000000000000') -> dict:
    global token
    if(not verify_token()): return None

    headers = { "Authorization": token["bearer"] }
    if workspace_id is not None:
        response = requests.post(
            "https://api.powerbi.com/v1.0/myorg/groups/{}/AssignToCapacity".format(workspace_id), 
            headers = headers, 
            json = {'capacityId': capacity_id}
        )
    else:
        log.error("Error -- must specify a workspace id to assign capacity ")
        return None
    
    if response.status_code == HTTP_OK:
        return response
    else:
        log.error("Error {} -- Something went wrong when trying to assign capacity {} to workspace {}".format(response.status_code, capacity_id, workspace_id))
        return None  