#coding: utf-8

import os
import sys
import json
import requests
import socket
import socks 
import urllib2
from lxml import etree
from datetime import datetime, timedelta


# Working hours
start_hour = 7
stop_hour  = 22

# Container for message lines
my_all_messages = []

# Observation points
observ_points = {
	"3477": 'Красноярск - Черемушки',
	"3478": 'Красноярск - Березовка',
	"3479": 'Красноярск - Северный',
	"3480": 'Красноярск - Солнечный',
	"3481": 'Красноярск - Кубеково',
	"3482": 'Ачинск - Юго-Восточный',
	"3821": 'Красноярск - Ветлужанка',
	"3822": 'Зеленогорск',
}


# Danger substances database
substances = {
	"2":     ("Бензол", 0.3),
	"58":    ("Диоксид азота", 0.2),
	"59":    ("Оксид азота", 0.4),
	"60":    ("Аммиак", 0.2),
	"61":    ("Взвешенные частицы до 10 мкм", 0.3),
	"62":    ("Диоксид серы", 0.5),
	"63":    ("Оксид углерода", 5.0),
	"64":    ("Сероводород", 0.008),
	"68":    ("Фенол", 0.01),
	"296":   ("Гидрофторид", 0.02),
	"298":   ("Формальдегид", 0.05),
	"300":   ("Толуол", 0.6),
	"301":   ("Этилбензол", 0.02),
	"302":   ("Хлорбензол", 0.1),
	"311":   ("Фториды твердые",0.2),
	"316":   ("Марганец", 0,01),
	"317":   ("Свинец", 0,001),
	"348":   ("Взвешенные частицы до 2.5 мкм", 0.16),
	"350":   ("Стирол", 0.04),
	"351":   ("Ксилол", 0.3),

}


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
		message+=line+'+%0A+%0A'

	url = "https://api.telegram.org/bot289181758:AAFkQFzTYBQZWF3IjHJK5x6a7EDlgtp2MtA/sendMessage?text=" + message + "&chat_id=%40apollo84test"

	#url = "https://api.telegram.org/bot289181758:AAFkQFzTYBQZWF3IjHJK5x6a7EDlgtp2MtA/sendMessage?text=" + message + "&chat_id=%40mchskrsk_112"
	#url = "https://api.telegram.org/bot289181758:AAFkQFzTYBQZWF3IjHJK5x6a7EDlgtp2MtA/sendMessage?text=" + message + "&chat_id=%40mchs24test"

	r = urllib2.urlopen(url, timeout=24).read()
	return json.loads(r)['ok']




def detect_current_values():
	"""Detect current values of substances"""

	# Detect today & tomorrow date for request
	today = datetime.today()
	tomorrow = today + timedelta(days=1)
	today = today.strftime('%Y-%m-%d').lstrip().rstrip()
	tomorrow =  tomorrow.strftime('%Y-%m-%d').lstrip().rstrip()

	# URL for request the data values
	url = 'http://gis.krasn.ru/sc/api/1.0/projects/1/values.xml?key=vkj4uih0gf92h4hf&time_begin=%s 00:00:00&time_end=%s 00:00:00&limit=30000' % (today, tomorrow)

	# Load HTML page
	page = requests.get(url).content

	# Obtain data as an element tree
	root = etree.fromstring(page)
	results = {}

	#--------------------------------------------------------------------------------
	# Handle tree elements 
	for appt in root.getchildren():
		# Get tree element value
		for el in appt.getchildren():
			# Get element attributes values
			site, indicator, time, location_x, location_y = el.get('site'), el.get('indicator'), el.get('time'), el.get('location_x'), el.get('location_y') 
			# Get element value
			if not el.text:
				value = "None"
			else:
				value = el.text
				value = float(value)
				
			# Handle the current measure point
			if observ_points.has_key(site) and substances.has_key(indicator):

				subst_name, limit_value = substances[indicator]
			 	limit_value = float(limit_value)			

				# Check if substance value bigger then normal value
				k = '%s_%s'.decode('utf-8') % (indicator, site)

				if (value > limit_value):
					results[k] = (value, u'faulty',)    # Value is bigger then normal
				else:
					results[k] = (value, u'ok',)        # Value is lower then normal
		
			else:
				continue

	#------------------------------
	return results


def load_values_fromfile(fname):
	"""
		fname - full name of file to load values from
	"""
	# Load previous data hash
	values = open(fname, 'r')
	prev_data = values.read()
	prev_data_set = json.loads(prev_data)
	values.close()
	return prev_data_set



def make_decision(k, cur_val, cur_status, prev_val, prev_status, one_hour_val, one_hour_status):
	"""Construct message line depending on situation about air conditions"""
	global my_all_messages

	subst,obj = k.encode('utf-8').split('_')
	subst_pdk = substances[subst][1]

	if prev_status==u'ok' and cur_status==u'faulty':
		if (cur_val >= (subst_pdk*10)):
			s = "На объекте наблюдений- '%s', значение вещества - '%s' превышает ПДК более чем в 10 раз, текущее значение измерения - %s, ПДК - %s" % (observ_points[obj], substances[subst][0], cur_val, subst_pdk)			
		else:
			s = "На объекте наблюдений- '%s', зафиксировано превышение вещества - '%s', текущее значение измерения - %s, ПДК - %s" % (observ_points[obj], substances[subst][0], cur_val, subst_pdk) 
		
		# Push sring to storage
		my_all_messages.append(s)
		folder_name = os.getcwd()+'/' + datetime.today().strftime('%Y-%m-%d').lstrip().rstrip()
		log_file = folder_name + '/'+ 'messages.log'
	
		# Save messages to log
		log = open(log_file, 'a')
		log.write(datetime.today().strftime('%Y-%m-%d %H:%M:%S') + " - " + s + '\n\n')
		log.close()

		return

	if (prev_status==u'faulty') and (cur_status==u'faulty') and (one_hour_status==u'faulty') and (one_hour_val!=None) and (one_hour_val < cur_val):
		s = "На объекте наблюдений- '%s', уровень вещества - '%s', остается на высоком уровне. Значение измерения 1 час назад - %s, текущее значение измерения - %s, ПДК - %s" % (observ_points[obj], substances[subst][0],one_hour_val, cur_val, subst_pdk)
		my_all_messages.append(s)
		folder_name = os.getcwd()+'/' + datetime.today().strftime('%Y-%m-%d').lstrip().rstrip()
		log_file = folder_name + '/'+ 'messages.log'
	
		# Save messages to log
		log = open(log_file, 'a')
		log.write(datetime.today().strftime('%Y-%m-%d %H:%M:%S') + " - " + s + '\n\n')
		log.close()

		return
		
	if prev_status==u'faulty' and cur_status==u'ok':
		s = "На объекте наблюдений- '%s', уровень вещества - '%s' нормализовался, текущее значение измерения- %s, ПДК - %s" % (observ_points[obj], substances[subst][0], cur_val, subst_pdk)
		my_all_messages.append(s)
		folder_name = os.getcwd()+'/' + datetime.today().strftime('%Y-%m-%d').lstrip().rstrip()
		log_file = folder_name + '/'+ 'messages.log'
	
		# Save messages to log
		log = open(log_file, 'a')
		log.write(datetime.today().strftime('%Y-%m-%d %H:%M:%S') + " - " + s + '\n\n')
		log.close()
		return



# Determine working hours schedule
now_hour = datetime.now().hour
now_min  = datetime.now().minute


if now_hour >= start_hour and now_hour < stop_hour:
	print 'it is working time'

	#-----------------------------------------------
	#               First time launch in a day
	#-----------------------------------------------
	if now_hour==7 and now_min >= 0 and now_min < 5:
	#if now_hour==15 and now_min >= 40 and now_min < 48:
		
		# Create folder for today
		folder_name = os.getcwd()+'/'+datetime.today().strftime('%Y-%m-%d').lstrip().rstrip()
		try:
			os.mkdir(folder_name)
		except OSError:
			print 'Folder exists!'
			sys.exit(1)

		#------Grab current info -----------------------
		cur_values = detect_current_values()


		# Save initial values to fname='1'
		dumps = json.dumps(cur_values)
		fout  = open(folder_name + '/'+ '1', 'w')
		fout.write(dumps)
		fout.close()

		# Initialize counter for current day
		fout  = open(folder_name + '/'+ 'counter.txt', 'w')
		fout.write("1")
		fout.close()


		#-------Manipulate by the values----
		#***************************
		# fkey = u'58_3481'
		# cur_values[fkey] = (10.35, u'faulty')

		# fkey = u'59_3482'
		# cur_values[fkey] = (0.45, u'faulty') 
		
		# List of messages about events
		messages = []
		for key in cur_values:
			subst,obj = key.encode('utf-8').split('_')
			
			val,status = cur_values[key]
			pdk = substances[subst][1]

			if status==u'faulty':
				if (val >= (pdk*10)):
					s = "На объекте наблюдений- '%s', значение вещества - '%s' превышает ПДК более чем в 10 раз, текущее значение измерения - %s, ПДК - %s" % (observ_points[obj], substances[subst][0], val, pdk)			
				else:
					s = "На объекте наблюдений- '%s', зафиксировано превышение вещества - '%s', текущее значение измерения - %s, ПДК - %s" % (observ_points[obj], substances[subst][0], val, pdk)
				folder_name = os.getcwd()+'/' + datetime.today().strftime('%Y-%m-%d').lstrip().rstrip()
				log_file = folder_name + '/'+ 'messages.log'
	
				# Save messages to log
				log = open(log_file, 'a')
				log.write(datetime.today().strftime('%Y-%m-%d %H:%M:%S') + " - " + s + '\n\n')
				log.close()

				messages.append(s)

		# If we have some messages  -send it to channel
		if len(messages) > 0:
			messages.append('Информация с сайта http://krasecology.ru/')
			all_message = '\n'.join(messages)
			send_text(all_message)



	#-----------------------------------------------
	#               Further launches in a day
	#-----------------------------------------------
	else:
		folder_name = os.getcwd()+'/' + datetime.today().strftime('%Y-%m-%d').lstrip().rstrip()

		# Get current count value			
		fin  = open(folder_name + '/'+ 'counter.txt', 'r')
		cur_file_index = fin.read()
		cur_file_index = int(cur_file_index.lstrip().rstrip())
		fin.close()

		# Generate file names			
		prev_fname = folder_name + '/' + str(cur_file_index)
		next_fname = folder_name + '/' + str(cur_file_index + 1)

		# Determine 1 hour ago fname
		if cur_file_index > 12:
			fname_hour_ago = folder_name + '/' + str(cur_file_index - 12)
			one_hours_values = load_values_fromfile(fname_hour_ago)
		else:
			one_hours_values = None

		#------Grab current info -----------------------
		cur_values  = detect_current_values()

		#------Grab prev launch info -----------------------
		prev_values = load_values_fromfile(prev_fname)


		#-------Manipulate by the values----
		#***************************
		#fkey = u'62_3822'
		#cur_values[fkey] = (2.36, u'faulty')
		#fkey = u'62_3821'
		#cur_values[fkey] = (200.36, u'faulty')
		

		# Serialize data and store it to the next file name
		dumps = json.dumps(cur_values)
		fout  = open(next_fname, 'w')
		fout.write(dumps)
		fout.close()

		# Store next file index to the file
		fout  = open(folder_name + '/'+ 'counter.txt', 'w')
		fout.write(str(cur_file_index+1))
		fout.close()


		# Send alarm messages
		for k in cur_values.keys():

			# Get current launch params
			subs, observ = k.split('_')
			cur_val, cur_status  = cur_values[k]
			
			# Get previous launch parameters
			try:
				prev_val, prev_status  = prev_values[k]
			except KeyError:
				prev_val, prev_status = None, None

			# Get 1 hour ago launch parameters
			try:
				one_hour_val, one_hour_status  = one_hours_values[k]
			except:
				one_hour_val, one_hour_status = None, None

			# Handle current measured value
			make_decision(k, cur_val, cur_status, prev_val, prev_status, one_hour_val, one_hour_status)
			
		# If we have some messages  -send it to channel
		if len(my_all_messages) > 0:
			my_all_messages.append('Информация с сайта http://krasecology.ru/')
			my_all_messages = '\n'.join(my_all_messages)
			send_text(my_all_messages)				
else: 
	print 'it is sleep time'
