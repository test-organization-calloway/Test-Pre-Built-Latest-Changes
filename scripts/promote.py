import requests
import json
import sys
import os

hostname = os.environ.get("IAP_HOSTNAME")

if not (hostname):
  print("""
Error in promote.py: No value found assigned to CI/CD variable IAP_HOSTNAME.
This value must be defined to import Pre-Built to target IAP from pipeline.
Please define this variable according to the Prebuilt Promotion README.md and retry failed pipeline job.
""")
  sys.exit(1)

iap_ssl_cert = os.environ.get("IAP_SSL_CERT")

# If SSL certificate provided, write value to local file system
if iap_ssl_cert: 
  with open('./itential.cert', 'w') as f:
    f.write(iap_ssl_cert)

# Get path to artifact.json
artifact_path = sys.argv[1]
path = './itential.cert'

# checking if IAP_PUSH_TO_LOCAL env var is set. If not set, default this value to True
if not (os.environ.get("IAP_PUSH_TO_LOCAL")):
  push_to_local = True
elif os.environ.get("IAP_PUSH_TO_LOCAL").lower() == "true":
  push_to_local = True
else: 
  push_to_local = False

# checking if IAP_TOKEN is set -> if not, use basic auth login
token = os.environ.get("IAP_TOKEN")
basic_auth = False
if not token:
  basic_auth = True
  username = os.environ.get("IAP_USERNAME")
  pw = os.environ.get("IAP_PW")

if not (token or (username and pw)):
  print("""
Error in promote.py: No value found assigned to CI/CD variables IAP_TOKEN or IAP_USERNAME and IAP_PW.
Either IAP_TOKEN or IAP_USERNAME and IAP_PW mmust be defined to authenticate call to import Pre-Built to target IAP from pipeline.
Please define variable needed for authentication according to the Prebuilt Promotion README.md and retry failed pipeline job.
""")
  sys.exit(1)

artifact = json.load(open(f"{artifact_path}"))
# Function Definitions
# Handles getting token to authenticate into IAP
def get_token():
  print("Getting auth token")
  url = f"{hostname}/login"
  payload = json.dumps({
    "user": {
      "username": username,
      "password": pw
    }
  })

  response = requests.request(
    "POST", 
    url, 
    headers={'Content-Type': 'application/json'},
    data=payload,
    verify=path)
  if not response.status_code // 100 == 2:
    raise Exception(f"Error: Unexpected response {response.text}: Failed to get auth token")
  else: 
    return response.text

# Checks if Pre-Built already exists
def get_prebuilt(name):
  print("Checking if Pre-Built already exists on target IAP")
  url = f"{hostname}/prebuilts?equals={name}&equalsField=name"
  response = requests.request(
    "GET", 
    url,
    headers={'Cookie': f'token={token}'},
    verify=path)
  if not response.status_code // 100 == 2:
    raise Exception(f"Error: Unexpected response {response.text}: Failed to get Pre-Built from target IAP")
  else: 
    return response.text

def add_prebuilt(payload):
  print("Pre-Built does not exist on target IAP, will import Pre-Built to IAP")
  url = f"{hostname}/prebuilts/import"
  headers = {
    'Content-Type': 'application/json',
    'Cookie': f'token={token}'
  }
  response = requests.request(
    "POST",
    url,
    headers=headers,
    data=payload,
    verify=path)
  if "Invalid repository configuration" in response.text:
    print("Invalid repository configuration encountered on attempting to import Pre-Built to target IAP, using local repository configuration for import.")
    updated_payload = json.loads(payload)
    updated_payload["prebuilt"]["metadata"]["repository"] = {
      "type": "local",
      "hostname": "localhost",
      "path": "/"
    }
    response = requests.request(
      "POST",
      url,
      headers=headers,
      data=json.dumps(updated_payload),
      verify=path)
  if not response.status_code // 100 == 2:
    raise Exception(f"Error: Unexpected response {response.text}: Failed to add Pre-Built")
  else: 
    print("Successfully imported Pre-Built to target IAP")
    return response.text

def update_prebuilt(id, payload):
  print("Pre-Built found on target IAP, updating existing Pre-Built")
  url = f"{hostname}/prebuilts/{id}"
  headers = {
    'Content-Type': 'application/json',
    'Cookie': f'token={token}'
  }
  response = requests.request(
    "PUT",
    url,
    headers=headers,
    data=payload,
    verify=path)
  if "Invalid repository configuration" in response.text:
    print("Failed to promote to original repository, pushing to local scope.")
    updated_payload = json.loads(payload)
    updated_payload["prebuilt"]["metadata"]["repository"] = {
      "type": "local",
      "hostname": "localhost",
      "path": "/"
    }
    response = requests.request(
      "PUT",
      url,
      headers=headers,
      data=json.dumps(updated_payload),
      verify=path)
  if not response.status_code // 100 == 2:
      raise Exception(f"Error: Unexpected response {response.text}: Failed to update Pre-Built")
  else: 
    print("Successfully updated Pre-Built")
    return response.text

def logout():
  print("Logging out of target IAP")
  url = f"{hostname}/login?logout=true"
  headers = {
    'Content-Type': 'application/json',
    'Cookie': f'token={token}'
  }
  response = requests.request(
    "GET",
    url,
    headers=headers,
    verify=path)

# Script starts here
try: 
  if (basic_auth):
    token = get_token()

  # Set name of Pre-Built
  name = artifact["metadata"]["name"]
  print(f"Starting promotion of Pre-Built {name} to target IAP {hostname}")

  results = get_prebuilt(name)
  if push_to_local:
    print("Setting artifact.json repository configuration to local per CI/CD variable IAP_PUSH_TO_LOCAL")
    artifact["metadata"]["repository"] = {
      "type": "local",
      "hostname": "localhost",
      "path": "/"
    }
    print('Will promote Pre-Built to target IAP with local repository configuration in artifact.json')
  else:
    print('Will promote Pre-Built to target IAP with repository configuration found in artifact.json')

  payload = json.dumps({
    "prebuilt": artifact,
    "options": {
      "overwrite": True 
    }
  })

  # if Pre-Built doesn't exist, add it
  if json.loads(results)["total"] == 0:
    response = add_prebuilt(payload)
  else: # if Pre-Built exists, update it
    id = json.loads(results)["results"][0]["_id"]
    update_prebuilt(id, payload)

  # logging out
  logout()
except requests.exceptions.RequestException as exception:
  # A serious problem happened, like an SSLError or InvalidURL
  print(f"Error: {exception}")
  sys.exit(1)  
except: # error handling to catch any errors that throw a non 200 code
  error = sys.exc_info()[1]
  print(error)
  sys.exit(1)
