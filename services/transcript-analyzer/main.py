import os

from ddtrace import patch_all
from dotenv import load_dotenv
from openai import OpenAI
from psychology_common import setup_logging

logger = setup_logging()
patch_all()

load_dotenv()


def main():
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"},
        ],
    )
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
