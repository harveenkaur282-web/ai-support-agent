import boto3, json

bedrock = boto3.client('bedrock', region_name='eu-north-1')

# Check current use case / model access config
try:
    r = bedrock.get_use_case_for_model_access()
    print('Current use case:', json.dumps(r, default=str, indent=2))
except Exception as e:
    print('get_use_case error:', e)

# Submit use case to unlock models
try:
    r2 = bedrock.put_use_case_for_model_access(
        formData=json.dumps({
            "useCaseDetails": "Customer support AI agent for e-commerce platform using Bedrock Knowledge Base with Titan embeddings and Nova language model for order tracking, product recommendations, and support queries.",
            "intendedUsers": "Internal development and Udacity project submission",
            "industry": "Technology",
            "companyName": "Personal Project"
        })
    )
    print('Use case submitted:', r2['ResponseMetadata']['HTTPStatusCode'])
except Exception as e:
    print('put_use_case error:', type(e).__name__, e)

# Try batch request model access (newer API)
try:
    r3 = bedrock.put_foundation_model_entitlement(
        modelId='amazon.titan-embed-text-v2:0'
    )
    print('Entitlement:', r3)
except Exception as e:
    print('entitlement error:', type(e).__name__, str(e)[:100])
