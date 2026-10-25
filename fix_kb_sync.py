"""
Fix KB sync issue and test retrieve.
"""
import boto3, json, time

# Clear any env var interference
import os
for k in ['AWS_SESSION_TOKEN', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_DEFAULT_REGION', 'AWS_REGION']:
    os.environ.pop(k, None)

# Load from .env
env_path = os.path.join(os.path.dirname(__file__), '.env')
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and '=' in line and not line.startswith('#'):
            k, _, v = line.partition('=')
            os.environ[k.strip()] = v.strip()

REGION = 'eu-north-1'
KB_ID = 'D2NLPJX6RP'
DS_ID = 'QFNLQ72WXB'

print("Step 1: Test model invoke directly as IAM user...")
try:
    br = boto3.client('bedrock-runtime', region_name=REGION)
    resp = br.invoke_model(
        modelId='amazon.titan-embed-text-v2:0',
        body=json.dumps({'inputText': 'test', 'dimensions': 1024}),
        contentType='application/json',
        accept='application/json'
    )
    emb = json.loads(resp['body'].read())
    print("  Model invoke SUCCESS, embedding dims:", len(emb.get('embedding', [])))
    model_ok = True
except Exception as e:
    print("  Model invoke FAIL:", e)
    model_ok = False

print()
print("Step 2: Check AOSS collection data access policy...")
aoss = boto3.client('opensearchserverless', region_name=REGION)

# The KB uses collection wopdeqrpd3skr33g9jle but policy covers bedrock-knowledge-base-rax4yk
# We need to add a data access policy for the correct collection
try:
    # List all data access policies
    pols = aoss.list_access_policies(type='data')
    print("  Existing data access policies:")
    for p in pols.get('accessPolicySummaries', []):
        print("   -", p['name'])
    
    # Create correct data access policy for our collection
    collection_arn = 'arn:aws:aoss:eu-north-1:824508926583:collection/wopdeqrpd3skr33g9jle'
    kb_role_arn = 'arn:aws:iam::824508926583:role/service-role/AmazonBedrockExecutionRoleForKnowledgeBase_6saiy'
    admin_arn = 'arn:aws:iam::824508926583:user/HarveenKaur-IAM-Admin'
    
    new_policy = [
        {
            "Rules": [
                {
                    "Resource": ["collection/wopdeqrpd3skr33g9jle"],
                    "Permission": [
                        "aoss:DescribeCollectionItems",
                        "aoss:CreateCollectionItems", 
                        "aoss:UpdateCollectionItems"
                    ],
                    "ResourceType": "collection"
                },
                {
                    "Resource": ["index/wopdeqrpd3skr33g9jle/*"],
                    "Permission": [
                        "aoss:UpdateIndex",
                        "aoss:DescribeIndex",
                        "aoss:ReadDocument",
                        "aoss:WriteDocument",
                        "aoss:CreateIndex"
                    ],
                    "ResourceType": "index"
                }
            ],
            "Principal": [kb_role_arn, admin_arn],
            "Description": "KB and admin access to vector collection"
        }
    ]
    
    try:
        r = aoss.create_access_policy(
            name='kb-vector-collection-access',
            type='data',
            policy=json.dumps(new_policy)
        )
        print("  Created new AOSS data access policy for collection wopdeqrpd3skr33g9jle")
    except aoss.exceptions.ConflictException:
        r = aoss.update_access_policy(
            name='kb-vector-collection-access',
            type='data',
            policy=json.dumps(new_policy),
            policyVersion='1'
        )
        print("  Updated existing AOSS data access policy")

except Exception as e:
    print("  AOSS error:", e)

print()
print("Step 3: Wait 5s for policy propagation, then trigger ingestion...")
time.sleep(5)

try:
    client = boto3.client('bedrock-agent', region_name=REGION)
    resp = client.start_ingestion_job(knowledgeBaseId=KB_ID, dataSourceId=DS_ID)
    job_id = resp['ingestionJob']['ingestionJobId']
    print("  Ingestion job started:", job_id)
    
    for i in range(30):
        time.sleep(5)
        s = client.get_ingestion_job(knowledgeBaseId=KB_ID, dataSourceId=DS_ID, ingestionJobId=job_id)
        status = s['ingestionJob']['status']
        stats = s['ingestionJob'].get('statistics', {})
        print(f"  [{(i+1)*5}s] {status} | {stats}")
        if status in ('COMPLETE', 'FAILED', 'STOPPED'):
            break

    print()
    print("Step 4: Test KB retrieve...")
    rt = boto3.client('bedrock-agent-runtime', region_name=REGION)
    resp2 = rt.retrieve(
        knowledgeBaseId=KB_ID,
        retrievalQuery={'text': 'What is the return policy for electronics?'}
    )
    results = resp2.get('retrievalResults', [])
    print(f"  KB retrieve: {len(results)} result(s)")
    if results:
        print("  Snippet:", results[0].get('content',{}).get('text','')[:200])

except Exception as e:
    print("  Error:", type(e).__name__, e)

print("\nDone.")
