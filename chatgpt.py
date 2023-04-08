import openai
import yaml

with open('config.yaml', encoding='utf-8') as f:
    conf = yaml.load(f, yaml.SafeLoader)['chatgpt']
    
openai.api_key = conf['token']
temperature = conf['temperature']
max_tokens = conf['max_tokens']


def gpt35(message:str):
    completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": message}], temperature=temperature, max_tokens=max_tokens)
    return completion
