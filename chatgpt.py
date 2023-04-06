import json
import openai

with open('config/openai.json', encoding='utf-8') as f:
    conf = json.load(f)
openai.api_key = conf['Token']
temperature=conf['temperature']
max_tokens=conf['max_tokens']

def gpt35(message:str)->str:
    completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": message}], temperature=temperature, max_tokens=max_tokens)
    return completion.choices[0].message.content
