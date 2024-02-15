# aio-appstoreserverlibrary

app-store-server-library-python asyncio API client, based on official version


## Usage

```python
from appstoreserverlibrary.api_client import AppStoreServerAPIClient, APIException
from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.models.SendTestNotificationResponse import SendTestNotificationResponse

private_key = read_private_key("/path/to/key/SubscriptionKey_ABCDEFGHIJ.p8") # Implemenation will vary

key_id = "ABCDEFGHIJ"
issuer_id = "99b16628-15e4-4668-972b-eeff55eeff55"
bundle_id = "com.example"
environment = Environment.SANDBOX

client = AppStoreServerAPIAsyncClient(private_key, key_id, issuer_id, bundle_id, environment)


async def test_notifi():
    try:    
        response = await client.request_test_notification()
        print(response)
    except APIException as e:
        print(e)
```
