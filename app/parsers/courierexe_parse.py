from bs4 import BeautifulSoup
import requests
import json
import logging

logger = logging.getLogger('parser')


def courierexe(orderno):
    url = "https://home.courierexe.ru/178/tracking"

    params = {
        "orderno": orderno,
        "singlebutton": "submit"
    }

    headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,"
                    "image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8,it;q=0.7",
            "cookie": "PHPSESSID=pd0apr1en20lsphs6r2f5ghp6r; "
                    "_csrf=f1dcfc532e329c03f9464faf503cc8315d80ff1b7306197c20e7bbccf0369106a%3A2%3A%7B"
                    "i%3A0%3Bs%3A5%3A%22_csrf%22%3Bi%3A1%3Bs%3A32%3A%22YWMCORltU4wwvVINjaVnH9qJv2RxieQD%22%3B%7D",
            "priority": "u=0, i",
            "referer": f"https://home.courierexe.ru/178/tracking?orderno={orderno}&singlebutton=submit",
            "sec-ch-ua": "\"Google Chrome\";v=\"131\", \"Chromium\";v=\"131\", \"Not_A Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "iframe",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }

    response = requests.get(url, params=params, headers=headers)

    html = response.text

    #soup = BeautifulSoup(html, 'html.parser')

    soup = BeautifulSoup(html, 'html5lib')

    # Находим таблицу. Здесь мы опираемся на известные атрибуты (class и т.д.)
    table = soup.find('table', {'class': 'table-striped'})

    data = {}

    if table:
        # Ищем все строки в таблице
        rows = table.find('tbody').find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) == 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                data[key] = value
    info=json.dumps(data, ensure_ascii=False)
    # Вывод словаря
    logger.info(f"Полученные данные для order number {orderno}: {info}")
    return info

orderno = "9196-495886"
courierexe(orderno)