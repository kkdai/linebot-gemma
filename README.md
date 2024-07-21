# Gemini Helper

## Project Background

## Screenshot

![image](https://github.com/kkdai/linebot-gemini-python/assets/2252691/466fbe7c-e704-45f9-8584-91cfa2c99e48)


## Features

## Technologies Used

- Python 3
- FastAPI
- LINE Messaging API
- Google Generative AI
- Aiohttp
- PIL (Python Imaging Library)

## Setup

1. Clone the repository to your local machine.
2. Set the following environment variables:
   - `ChannelSecret`: Your LINE channel secret.
   - `ChannelAccessToken`: Your LINE channel access token.
   - `GEMINI_API_KEY`: Your Gemini API key for AI processing.
3. Install the required dependencies by running `pip install -r requirements.txt`.
4. Start the FastAPI server with `uvicorn main:app --reload`.

## Usage

To use the Receipt Helper, send a picture of your receipt to the LINE bot. The bot will process the image, extract the data, and provide a JSON representation of the receipt. For text-based commands or queries, simply send the command or query as a message to the bot.

## Commands

- `!清空`: Clears all the scanned receipt history for the user.

## Contributing

If you'd like to contribute to this project, please feel free to submit a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
