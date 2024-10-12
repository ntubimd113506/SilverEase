from ollama import Client

client = Client(host="http://localhost:11434")

while True:
    print("輸入問題:")
    ques = input()
    if ques == "/E":
        break

    response = client.chat(
        model="llama3.1",
        messages=[
            {
                "role": "user",
                "content": f"""
        請使用**繁體中文**回答後再用**英語**回答\n\n

        {ques}\n\n
    
        """,
            },
        ],
    )
    print("--------------------")
    print(response["message"]["content"])
    print()
