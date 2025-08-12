from openai import OpenAI
MAX_HISTORY_SIZE = 5
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key='',
)

chat_history = {}
username = 'jon'

def chat():
    while True:
        prompt = input('enter:')
        if username not in chat_history:
            chat_history[username] = []
        if len(chat_history[username]) > MAX_HISTORY_SIZE:
            chat_history[username].pop(0)

        chat_history[username].append({"role": "user", "content": prompt})
        completion = client.chat.completions.create(
                        model="deepseek/deepseek-r1:free",
                        messages=chat_history[username],
                        stream=False,
                    )

        model_reply = completion.choices[0].message.content
        print(model_reply)
        chat_history[username].append({"role": "assistant", "content": model_reply})

        # print('*>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
        # print(chat_history)

if '__main__' == '__main__':
    chat()