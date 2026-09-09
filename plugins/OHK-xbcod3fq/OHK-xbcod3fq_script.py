from common.methods import set_progress
from infrastructure.models import Environment

def get_dynamodb_client():
    """Creates a new DynamoDB client only when needed."""
    set_progress("Creating new DynamoDB connection.")
    env = Environment.objects.get(id=14)
    resource_handler = env.resource_handler.cast()
    wrapper = resource_handler.get_api_wrapper()

    return wrapper.get_boto3_client(
        "dynamodb",
        resource_handler.serviceaccount,
        resource_handler.servicepasswd,
        "ap-southeast-2",
    )

def inbound_web_hook_get(*args, parameters=None, **kwargs):
    if parameters is None:
        parameters = {}

    set_progress(f"Processing webhook request. args: {args}, kwargs: {kwargs}, parameters: {parameters}")

    user_input = ("@Ris").strip().lower() 
    #return user_input
    # user_input = parameters.get("application_name", "").strip().lower()  
    # return user_input

    # Ensure input is exactly 4 characters before making a DB connection
    # if len(user_input) != 4:
    #     return {"options": [], "initialValue": ""}

    # client = get_dynamodb_client()  

    # TABLE_NAME = "snow_busappsync"

    # scan_params = {
    #     "TableName": TABLE_NAME,
    #     "ProjectionExpression": "#name",  # Fetch only 'name'
    #     "ExpressionAttributeNames": {"#name": "name"},
    # }

    # # Perform scan
    # dynamo_response = client.scan(**scan_params)

    # # Post-filtering for case-insensitive match
    # options = [
    #     {"id": item["name"]["S"], "name": item["name"]["S"]}
    #     for item in dynamo_response.get("Items", [])
    #     if "name" in item and user_input in item["name"]["S"].lower() 
    # ]
    options = [{'id': '@Risk (Metro)', 'name': '@Risk (Metro)'}, {'id': 'eBusiness Change Password (ECP)', 'name': 'eBusiness Change Password (ECP)'}, {'id': 'Collibra Browser Extension', 'name': 'Collibra Browser Extension'}, {'id': 'Point to Point', 'name': 'Point to Point'}, {'id': 'Data Pro', 'name': 'Data Pro'}, {'id': 'TrackData', 'name': 'TrackData'}, {'id': 'DRIVES 24 External Access', 'name': 'DRIVES 24 External Access'}, {'id': 'CAST', 'name': 'CAST'}, {'id': 'Centrelink DRIVES Servlet', 'name': 'Centrelink DRIVES Servlet'}, {'id': 'Rural & Regional Bus Reporting System', 'name': 'Rural & Regional Bus Reporting System'}]
    initialValue = options[0]["name"] if options else ""

    return {"options": options, "initialValue": initialValue}