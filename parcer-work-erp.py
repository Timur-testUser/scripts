import requests
from bs4 import BeautifulSoup

# Отправляем запрос на страницу
url = "https://example.com"  
response = requests.get(url)

# Получаем HTML-код страницы
html_code = response.text

# Создаем объект BeautifulSoup для парсинга HTML-кода
soup = BeautifulSoup(html_code, 'html.parser')

# Ищем слова "Растут CRC-ошибки" на странице
search_term = "Растут CRC-ошибки"
results = [element for element in soup.find_all(text=lambda t: t and search_term in t)]

# Если слова найдены, ищем поле "openProcess" в той же колонке
if results:
    for result in results:
        # Ищем поле "openProcess" в HTML-коде
        open_process_element = result.find_parent().find('input', {'name': 'openProcess'})
        if open_process_element:

          # В работе
