import requests
from duckduckgo_search import DDGS

print("AI Chatbot with References")
print("Type 'exit' to quit\n")

while True:
    question = input("You: ")

    if question.lower() == "exit":
        break

    try:
        # Search top 3 links
        links = []
        with DDGS() as ddgs:
            results = ddgs.text(question, max_results=3)

            for r in results:
                if "href" in r:
                    links.append(r["href"])
                elif "url" in r:
                    links.append(r["url"])

        # AI answer
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": question,
                "stream": False
            },
            timeout=120
        )

        answer = response.json()["response"]

        print("\nBot:")
        print(answer)

        print("\nReferences:")
        if links:
            for i, link in enumerate(links, 1):
                print(f"{i}. {link}")
        else:
            print("No references found")

        print("\n" + "-" * 50 + "\n")

    except Exception as e:
        print("Error:", e)