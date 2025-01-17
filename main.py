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
from groq import Groq
import aiohttp
import PIL.Image
#import replicate


# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('ChannelSecret', None)
channel_access_token = os.getenv('ChannelAccessToken', None)
gemini_key = os.getenv('GEMINI_API_KEY')
groq_token = os.getenv('GROQ_API_KEY')

imgage_prompt = '''
Describe this image with scientific detail, reply in zh-TW:
'''

remove_personal_prompt = '''
Replace personal information, name with someone, address, ID number, bank account, etc. 
Just give me the modified original text, don't reply to me.
------\n
'''

need_bot_prompt = '''
Check the following text to see 
if it requires customer service assistance. 
Just answer YES/NO
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
if groq_token is None:
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
                # using local llm to remove personal information.
                determine_ret = generate_local_llm_result(f'{need_bot_prompt}, {msg}')

                # Ｃheck if determine_ret contains YES (case insensitive)
                if "yes" in determine_ret.lower():
                    # Pass to LLM to process original request.
                    ret = generate_gemini_text_complete(f'{msg}, reply in zh-TW:')
                    reply_msg = TextSendMessage(text=ret.text)
                    await line_bot_api.reply_message(
                        event.reply_token,
                        reply_msg
                    )
                else:
                    # otherwise, skip it.
                    continue
                # pass the result to gemini to generate a complete sentence.
            else:
                # Provide a default value for reply_msg
                msg = event.message.text
                # using local llm to remove personal information.
                safe_ret = generate_local_llm_result(f'{remove_personal_prompt}, {msg}')
                # pass the result to gemini to generate a complete sentence.
                ret = generate_gemini_text_complete(f'{safe_ret}, reply in zh-TW:')
                local_changed_msg = TextSendMessage(text=f'原有訊息: {msg}, \n 修正後安全訊息： {safe_ret}')
                safe_reply_msg = TextSendMessage(text=f'回覆訊息： {ret.text}')
                await line_bot_api.reply_message(
                    event.reply_token,
                    [local_changed_msg, safe_reply_msg]
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


def generate_local_llm_result(prompt):
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="gemma2-9b-it",
    )

    print(chat_completion.choices[0].message.content)
    return chat_completion.choices[0].message.content
