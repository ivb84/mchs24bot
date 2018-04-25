#coding: utf-8

import bs4
import sys
import requests
import psycopg2
import socket
import socks 
import json
import urllib2



def send_text(lines):
	""""Send message over Telegram proxy server"""

	# Configuration
	SOCKS5_PROXY_HOST = 's5.citadel.cc'
	SOCKS5_PROXY_PORT = 61080


	# Remove this if you don't plan to "deactivate" the proxy later
	default_socket = socket.socket

	# Set up a proxy
	socks.set_default_proxy(socks.SOCKS5, SOCKS5_PROXY_HOST, SOCKS5_PROXY_PORT)
	socket.socket = socks.socksocket



	message = ""
	lines_set = lines.split('\n')
	for line in lines_set:
		message+=line+'+%0A'

	url = "https://api.telegram.org/bot289181758:AAFkQFzTYBQZWF3IjHJK5x6a7EDlgtp2MtA/sendMessage?text=" + message + "&chat_id=%40mchskrsk_112"	
	r = urllib2.urlopen(url, timeout=24).read()
	return json.loads(r)['ok']






# Устанавливаем соедининие с БД
conn   = psycopg2.connect(host='10.116.4.4', database='otoevm', user='pgsql', password='12345')
cursor = conn.cursor()


# Авторизоваться в админке на портале
session = requests.Session()
session.post('http://24.mchs.gov.ru/admin/auth', {
 	'username': 'admin_24',
 	'password': 'KvEVtLTpFc',
 	'remember': 1,
})

# Подгрузим страницу с оперативными новостями
r = session.get('http://24.mchs.gov.ru/admin/structure_item/item/224055')
html = r.text

# Начинаем парсить страницу
soup = bs4.BeautifulSoup(html, "html.parser")
trs = soup.find_all("tr", { "class" : "document-enabled"})

# Итерируем по строкам таблицы новостей
for tr in trs:
	# Получаем id новости
	news_id = tr['rel'].encode('utf8').lstrip().rstrip()
	tds = tr.find_all("td")
	
	# Проверим есть ли обработана ли эта новость в прошлом
	query = """SELECT * FROM mchs24_storm where news_id = '%s'""" % (news_id)
	cursor.execute(query)
	rows = cursor.fetchall()

	# Проверяем - новая ли новость
	if len(rows) == 0: 
		# Формируем ссылку на страницу с новостью
		news_link = 'http://24.mchs.gov.ru/admin/structure_item/documents/224055/edit/%s/?type=document_dailyforecast&page=1&per_page=10' % (news_id)
		
		# Подгрузим новость
		r = session.get(news_link)
		html = r.text		

		# Начинаем парсить страницу
		soup = bs4.BeautifulSoup(html, "html.parser")
		txt_area = soup.find("textarea")

		# Извлекаем тело сообщения
		soup = bs4.BeautifulSoup(txt_area.get_text(), "html.parser")
		
		tags_p = soup.find_all("p")
		total_mess = ''
		for tag_p in tags_p:
			message = tag_p.get_text().encode('utf8').lstrip().rstrip()
			total_mess+=message + '\n'

		# Выводим текстовое сообщение
		total_mess = total_mess.lstrip().rstrip() 
		send_text(total_mess)

		#bot.send_message(CHANNEL_NAME, total_mess.lstrip().rstrip())

		# Сохраним информацию об обработанной новости в БД
		query = """INSERT INTO mchs24_storm (news_id) VALUES ('%s')""" % (news_id)
		cursor.execute(query)
		conn.commit()

# Закрываем WEB-сессию
session.close()

# Закрываем соединение с БД
cursor.close()
conn.close()
