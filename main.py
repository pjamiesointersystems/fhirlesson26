import requests
import os
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()
OPEN_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI()

def main():
    print("Hello from lesson26!")
    user_input = input("What should the post be about?")
    openai_post = create_post(user_input)
    print(f"OpenAI post: {openai_post}\n")




def create_post(topic: str) -> str:
    response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are an expert social media manager and you excel at creating LinkedIn posts based on user input. Avoid using hashtags, emojis, or jargon. Keep the post professional and concise."},
        {"role": "user", "content": f"Create a LinkedIn post about: {topic}"}
    ],
    temperature=0.7
)
    # return response_text.strip()
    return response.choices[0].message.content.strip()    

                


if __name__ == "__main__":
    main()
