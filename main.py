from linebot.models import (
    MessageEvent, TextSendMessage
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.aiohttp_async_http_client import AiohttpAsyncHttpClient
from linebot import (
    AsyncLineBotApi, WebhookParser
)
from fastapi import Request, FastAPI, HTTPException
import google.generativeai as genai
import os
import sys
from io import BytesIO

import aiohttp
import PIL.Image
import replicate


# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('ChannelSecret', None)
channel_access_token = os.getenv('ChannelAccessToken', None)
gemini_key = os.getenv('GEMINI_API_KEY')
replicate_token = os.getenv('REPLICATE_API_TOKEN')

imgage_prompt = '''
Describe this image with scientific detail, reply in zh-TW:
'''

remove_personal_prompt = '''
"取代掉個人資料，姓名用某人，地址，身份字號，銀行帳號等。 只要給我移除後的文字\n
------\n
'''


if channel_secret is None:
    print('Specify ChannelSecret as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify ChannelAccessToken as environment variable.')
    sys.exit(1)
if gemini_key is None:
    print('Specify GEMINI_API_KEY as environment variable.')
    sys.exit(1)
if replicate_token is None:
    print('Specify REPLICATE_API_TOKEN as environment variable.')
    sys.exit(1)

# Initialize the FastAPI app for LINEBot
app = FastAPI()
session = aiohttp.ClientSession()
async_http_client = AiohttpAsyncHttpClient(session)
line_bot_api = AsyncLineBotApi(channel_access_token, async_http_client)
parser = WebhookParser(channel_secret)

# Initialize the Gemini Pro API
genai.configure(api_key=gemini_key)


@app.post("/")
async def handle_callback(request: Request):
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = await request.body()
    body = body.decode()

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    for event in events:
        if not isinstance(event, MessageEvent):
            continue

        if (event.message.type == "text"):
            # check if in group or not
            if event.source.type == "group":
                # Provide a default value for reply_msg
                msg = event.message.text
                reply_msg = TextSendMessage(text=msg)
                await line_bot_api.reply_message(
                    event.reply_token,
                    reply_msg
                )
            else:
                # Provide a default value for reply_msg
                msg = event.message.text
                ret = generate_gemini_text_complete(f'{msg}, reply in zh-TW:')
                reply_msg = TextSendMessage(text=ret.text)
                await line_bot_api.reply_message(
                    event.reply_token,
                    reply_msg
                )
        elif (event.message.type == "image"):
            message_content = await line_bot_api.get_message_content(
                event.message.id)
            image_content = b''
            async for s in message_content.iter_content():
                image_content += s
            img = PIL.Image.open(BytesIO(image_content))

            result = generate_result_from_image(img, imgage_prompt)
            reply_msg = TextSendMessage(text=result.text)
            await line_bot_api.reply_message(
                event.reply_token,
                reply_msg
            )
            return 'OK'
        else:
            continue

    return 'OK'


def generate_gemini_text_complete(prompt):
    """
    Generate a text completion using the generative model.
    """
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    return response


def generate_result_from_image(img, prompt):
    """
    Generate a image vision result using the generative model.
    """

    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([prompt, img], stream=True)
    response.resolve()
    return response


def generate_result_from_replicate(prompt):
    output = replicate.run(
        "lucataco/gemma2-9b-it:24464993111a1b52b2ebcb2a88c76090a705950644dca3a3955ee40d80909f2d",
        input={
            "top_k": 50,
            "top_p": 0.9,
            "prompt": prompt,
            "temperature": 0.27,
            "max_new_tokens": 512,
            "repetition_penalty": 1.2
        }
    )

    # The lucataco/gemma2-9b-it model can stream output as it's running.
    # The predict method returns an iterator, and you can iterate over that output.
    for item in output:
        # https://replicate.com/lucataco/gemma2-9b-it/api#output-schema
        print(item, end="")
