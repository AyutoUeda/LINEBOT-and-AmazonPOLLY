import os
import sys
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, AudioSendMessage, AudioMessage
)
from linebot.exceptions import (
    LineBotApiError, InvalidSignatureError
)
import logging

logger = logging.getLogger()
logger.setLevel(logging.ERROR)

channel_secret = os.environ['LINE_CHANNEL_SECRET']
channel_access_token = os.environ['LINE_CHANNEL_ACCESS_TOKEN']

if channel_secret is None:
    logger.error('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    logger.error('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

import boto3
from boto3 import Session
from boto3 import resource
from contextlib import closing

def lambda_handler(event, context):
    if "x-line-signature" in event["headers"]:
        signature = event["headers"]["x-line-signature"]
    elif "X-Line-Signature" in event["headers"]:
        signature = event["headers"]["X-Line-Signature"]
    body = event["body"]
    
    ok_json = {"isBase64Encoded": False,
              "statusCode": 200,
              "headers": {},
              "body": ""}
    error_json = {"isBase64Encoded": False,
                  "statusCode": 500,
                  "headers": {},
                  "body": "Error"}
                  
    @handler.add(MessageEvent, message=TextMessage)
    def message(event):
        text=event.message.text
        message_id=event.message.id
        
        s3 = resource('s3')
        bucket = s3.Bucket("linebot-polly")
        
        polly_client = boto3.Session(
                    aws_access_key_id=os.environ['aws_access_key_id'],                     
                    aws_secret_access_key=os.environ['aws_secret_access_key'],
                    region_name='ap-northeast-1').client('polly')
    
        response = polly_client.synthesize_speech(VoiceId='Mizuki',
                        OutputFormat='mp3', 
                        Text = text)
                        
        with closing(response["AudioStream"]) as stream:
            bucket.put_object(Key=f"{message_id}.mp3", Body=stream.read())
        
        original_content_url=f"https://linebot-polly.s3-ap-northeast-1.amazonaws.com/{message_id}.mp3"
        
        line_bot_api.reply_message(
        event.reply_token,
        AudioSendMessage(
            original_content_url=original_content_url,
            duration=5000
        ))
            
        # line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))
    try:
        handler.handle(body, signature)
    except LineBotApiError as e:
        logger.error("Got exception from LINE Messaging API: %s\n" % e.message)
        for m in e.error.details:
            logger.error("  %s: %s" % (m.property, m.message))
        return error_json
    except InvalidSignatureError:
        return error_json

    return ok_json
