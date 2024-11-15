from flask import Flask, request, jsonify
import asyncio
import os
from playwright.async_api import async_playwright

app = Flask(__name__)

async def scrape_comments(url):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.connect(os.environ['BROWSER_PLAYWRIGHT_ENDPOINT'])
            context = await browser.new_context(
                ignore_https_errors=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US"
            )
            await context.add_init_script("""
                const defaultGetter = Object.getOwnPropertyDescriptor(
                    Navigator.prototype,
                    "webdriver"
                )?.get;
                if (defaultGetter) {
                    Object.defineProperty(Navigator.prototype, "webdriver", {
                        get: new Proxy(defaultGetter, {
                            apply: (target, thisArg, args) => {
                                Reflect.apply(target, thisArg, args);
                                return false;
                            },
                        }),
                    });
                }
            """)

            # Abrir uma nova página e navegar para a URL
            page = await context.new_page()
            await page.goto(url, wait_until="load")

            # Selecionar todos os elementos <h4>, <p> e <span> correspondentes
            titles = await page.query_selector_all('h4[data-testid="compain-title-link"].sc-1pe7b5t-1.bVKmkO')
            descriptions = await page.query_selector_all('p.sc-1pe7b5t-2.eHoNfA')
            statuses = await page.query_selector_all('span.sc-1pe7b5t-4')

            # Extrair os textos de todos os elementos <h4> e <p>
            titles_text = [await title.inner_text() for title in titles]
            descriptions_text = [await description.inner_text() for description in descriptions]

            # Identificar e extrair o status com base nas classes CSS específicas
            statuses_text = []
            for status in statuses:
                status_class = await status.get_attribute("class")
                if "ihkTSQ" in status_class:
                    statuses_text.append("Respondida")
                elif "cZrVnt" in status_class:
                    statuses_text.append("Não respondida")
                elif "jKvVbt" in status_class:
                    statuses_text.append("Resolvido")
                elif "dwDQii" in status_class:
                    statuses_text.append("Não resolvido")
                else:
                    statuses_text.append("Status desconhecido")

            # Montar o resultado em ordem especificada
            data = []
            for i in range(min(len(titles_text), len(descriptions_text), len(statuses_text))):
                data.append({
                    "Título": titles_text[i],
                    "Descrição": descriptions_text[i],
                    "Status": statuses_text[i]
                })

            # Fechar o navegador
            await browser.close()

            return {"Comentários": data}
    except Exception as e:
        return {"error": str(e)}

@app.route('/comments', methods=['GET'])
def scrape_comments_route():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "Parâmetro 'url' é obrigatório"}), 400

    data = asyncio.run(scrape_comments(url))
    return jsonify(data)

if __name__ == '__main__':
    app.run()
