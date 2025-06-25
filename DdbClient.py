import boto3

class DdbClient:
    def __init__(self, table = 'content_meta_data'):
        # Initialize DynamoDB resource
        self.client = boto3.resource('dynamodb', region_name='us-east-1')  # change region as needed
        self.table =  self.client.Table('MyTable')

    def insert(content_id: str,  zip_code: int, user_id: str):

        # Insert a row (item)
        response = table.put_item(
            Item={
                'content_id': '123',              # Primary key
                'zip_code': 22180,
                'user_id': 'mark0871',
                'description': 'kitchen'
            }
        )

        print("PutItem succeeded:", response)