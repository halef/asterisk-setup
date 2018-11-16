#!/usr/bin/env python
"""Asterisk AGI script to enable logging and forwarding to OpenSIPS.

This module handles call routing, recording and logging. It needs to be called
from the asterisk dialplan via the AGI() diaplan application.

Usage
-----
The dialplan needs to first set Set(AGISIGHUP=no), then call
AGI(<path/to/agi_call_opensips.py, ARG1, ARG2, ARG3, ARG4)

Parameters
----------
ARG1 : int
    JVoiceXML extension to call
ARG2 : str
    Use case name that will be logged to the database.
ARG3 : str
    Autoscaling group to use. Defaults to DEFAULT_AUTOSCALING_GROUP
ARG4 : str
    Name of opensips peer. Defaults to DEFAULT_OPENSIPS_PEER


Example
-------

exten => 12,1,Set(AGISIGHUP=no)
exten => 12,2,AGI(/export/Apps/asterisk/agi/agi_call_opensips.py,7709, development, autoscale, OPENSIPS)


NOTES:
	
	Asterisk commands, functions, applciations, run via AGI (e.g. agi.exec_command...) are listed here:

	https://wiki.asterisk.org/wiki/display/AST/Asterisk+Command+Reference

WARNING
-------
Currently, we still have hardcoded values below for:
    - logging server url
    - asterisk server ip
    - path to busy prompt

We need to change those before deploying in a different environment.

"""
import configparser
import json
import os
import sys
import traceback

import requests

from asterisk.agi import AGI

__location__ = ospath.realpath(
	os.path.join(os.getcwd(), os.path.dirname(__file__))
)
config_file = os.path.join(__location__, 'call_opensips.ini')
config = configparser.ConfigParser(config.read(config_file))

ASTERISK_IP = config['DEFAULT']['ASTERISK_IP']
GANESHA_URL = config['DEFAULT']['GANESHA_URl']
BUSY_AUDIO_FILE = config['DEFAULT']['PATH_TO_BUSY_AUDIO_FILE']

DEFAULT_AUTOSCALING_GROUP = 'autoscale'
DEFAULT_OPENSIPS_PEER = 'OPENSIPS' 

def saveHalefCallStartDetails(call_id, recording_filename, server_ip, extension,
                       start_time):
    """Send the ASTERISK_CALL_START event to the logging server."""
    url = GANESHA_URL
    payload = {
        'api_version': 1,
        'event_type': 'ASTERISK_CALL_START',
        'call_id': call_id,
        'recording': recording_filename,
        'server_ip': server_ip,
        'extension': extension,
        'start_time': start_time
    }
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    return response


def saveHalefEndStartDetails(call_id, transfer_state_name, end_time):
    """Send the ASTERSIK_CALL_END event to the logging server."""
    url = GANESHA_URL
    payload = {
        'api_version': 1,
        'event_type': 'ASTERISK_CALL_END',
        'call_id': call_id,
        'transfer_state_name': transfer_state_name,
        'end_time': end_time
    }
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    return response


def play_busy(agi, user_hangup):
    """Play busy message."""
    if not user_hangup:
        try:
            agi.answer()
            agi.stream_file(BUSY_AUDIO_FILE)
        except Exception:
            user_hangup = True
    return user_hangup


def dial(agi, 
         user_hangup,
         jvxml_extension,
         autoscaling_group,
         opensips_peer):
    """Call OpenSIPS with given JVoiceXML extension."""
    if not user_hangup:
        try:
            agi.exec_command('SIPAddHeader', 
                             'X-Autoscaling-Group:{}'
                             .format(autoscaling_group))
            agi.exec_command('Dial', 'SIP/{}@{}'.format(jvxml_extension,
                             opensips_peer), 15)
        except Exception:
            user_hangup = True
    return user_hangup


def record(agi, user_hangup, call_id):
    """Start individual and full duplex call recording ."""
    if not user_hangup:
        try:
            agi.exec_command('Monitor', 'wav', '{}'.format(call_id))
            agi.exec_command('MixMonitor', '{}.wav'.format(call_id))
        except Exception:
            user_hangup = True
    return user_hangup


def hangup(agi, user_hangup):
    """End the call."""
    if not user_hangup:
		# only hang up is there is a call already. Not 1 == SIP CANCEL
		if channel_status(agi) > 0:
			agi.hangup()

# logs to the Asterisk log (e.g. /export/Apps/asterisk/var/log/asterisk/full)
class loggerClass:
	agi = None
	callerid = None
	use_case_name = None
	DEFAULT_LOG_LEVEL = 'NOTICE'
	#LOG_LEVEL can be ERROR, WARNING, NOTICE, DEBUG, VERBOSE or DTMF
	
	def __init__(self,agi):
		self.agi = agi
		# LOG_LEVEL one of ERROR, WARNING, NOTICE, DEBUG, VERBOSE, DTMF
		self.agi.exec_command('LOG',self.DEFAULT_LOG_LEVEL, 'loggerClass __init__')
		self.callerid = agi.get_variable('SIPCALLID')
		
		self.use_case_name = self.agi.env.get('agi_arg_2', '')
		self.msgPrefix = 'CALLERID(name:' + self.callerid + "|" + self.use_case_name + ') '
	
	def info(self,msg):
		self.log('NOTICE',msg)

	def warn(self,msg):
		self.log('WARNING',msg)

	def error(self,msg):
		self.log('ERROR',msg)

	def log(self,LOG_LEVEL,msg):
		if not self.callerid:
			self.callerid = ""
		if not self.use_case_name:
			self.use_case_name = ""
		if type(msg) == list:
				msg = " ".join(msg)
		if type(msg) == str:
			msg = self.msgPrefix + msg
			self.agi.exec_command('LOG',LOG_LEVEL, msg)
		else:
			msg = self.msgPrefix + msg
			self.agi.exec_command('LOG','ERROR', msg + 'UNKNOWN ERROR in: ' + os.path.basename(__file__))
			

			
def channel_status(agi):
	# see https://wiki.asterisk.org/wiki/display/AST/AGICommand_channel+status
	status = agi.channel_status()
	logger = logger(agi)
	if status == 0:
		logger.info( 'CALL STATUS: ' + 'CHANNEL IS DOWN AND AVAILABLE')
	elif status == 1:
		logger.info( 'CALL STATUS: ' + 'CHANNEL IS DOWN, BUT RESERVED')
	elif status == 2:
		logger.info( 'CALL STATUS: ' + 'CHANNEL IS OFF HOOK')
	elif status == 3:
		logger.info( 'CALL STATUS: ' + 'DIGITS (OR EQUIVALENT) HAVE BEEN DIALED')
	elif status == 4:
		logger.info( 'CALL STATUS: ' + 'LINE IS RINGING')
	elif status == 5:
		logger.info( 'CALL STATUS: ' + 'REMOTE END IS RINGING')
	elif status == 6:
		logger.info( 'CALL STATUS: ' + 'LINE IS UP')
	elif status == 7:
		logger.info( 'CALL STATUS: ' + 'LINE IS BUSY')
	else:
		logger.info( 'CALL STATUS: ' + 'UNKNOWN')
		
	return status

def exitHangup(agi):
	_exit(agi,'HANGUP')

def exitSuccess(agi):
	_exit(agi,'SUCCESS')
	
def exitFailure(agi):
	_exit(agi,'FAILURE')
	

def _exit(agi,agiStatus):
	if agi:
		logger = logger(agi)
		try:
			logger.info("SCRIPT ENDED ")
			agi.env.set('AGISTATUS',agiStatus)
			agi.hangup()
			sys.exit(0)
		except Exception:
			logMsg = ['python stack trace: '] + traceback.format_exc().split()		
			logger.error( logMsg)

		
		
		
def main():
	"""Wrap the main program logic."""
	# Initialize AGI and set variables.
	agi = None

	agi = AGI()
	logger = loggerClass(agi)
	# agi.hangup()
	
	try:
		user_hangup = False		
		transfer_state = 'PREDIAL'
		call_id = agi.get_variable('SIPCALLID')
		# hangup(agi,False)
		called_number = agi.env.get('agi_dnid', None)
		jvxml_extension = agi.env.get('agi_arg_1', None)
		use_case_name = agi.env.get('agi_arg_2', None)
		autoscaling_group = agi.env.get('agi_arg_3', DEFAULT_AUTOSCALING_GROUP)
		opensips_peer = agi.env.get('agi_arg_4', DEFAULT_OPENSIPS_PEER)

		log_callerid = agi.env.get('agi_callerid', None)
		log_uniqueid = agi.env.get('agi_uniqueid', None)
		

		if not called_number:
			logger.error( 'Could not get called number.')
			exitFailure(agi)

		if not (jvxml_extension and use_case_name):
			logger.error( 'You need to provide jvxml_extension and use_case_name.')
			exitFailure(agi)

		# Asterisk already displays the below input values
		logger.info(' called_number SHOULD BE:  <4 digits freeswitch extension><4 digits asterisk extension or garbage i guess><frontend UUID from javascript>')
		logger.info( ' called_number=[{}]'.format(called_number))
		logger.info( ' jvxml_extension=[{}]'.format(jvxml_extension))
		logger.info( ' use_case_name=[{}]'.format(use_case_name))
		logger.info( ' autoscaling_group=[{}]'.format(autoscaling_group))
		logger.info( ' opensips_peer=[{}]'.format(opensips_peer))
		logger.info( ' log_callerid=[{}]'.format(log_callerid))
		logger.info( ' log_uniqueid=[{}]'.format(log_uniqueid))

		# Get information required for logging and send ASTERISK_START_CALL event.
		freeswitch_extension = called_number[:4]
		start_time = agi.get_variable('CDR(start)')
		recording_filename = '{}.wav'.format(call_id)
		server_ip = os.environ.get('ASTERISK_SERVER_IP', ASTERISK_IP)
		saveHalefCallStartDetails(call_id, recording_filename, server_ip, freeswitch_extension,
						   start_time)

		# Set variables which are read out by JVoiceXML
		agi.set_variable('CALLERID(name)', call_id + '|' + use_case_name)
		agi.set_variable('CALLERID(num)', called_number)

		# Start recording
		user_hangup = record(agi, user_hangup, call_id)

		# Make the call
		user_hangup = dial(agi, 
						   user_hangup,
						   jvxml_extension,
						   autoscaling_group=autoscaling_group,
						   opensips_peer=opensips_peer)
						   
		# see https://www.voip-info.org/wiki/view/Asterisk+variable+DIALSTATUS
		dial_status = agi.get_variable('DIALSTATUS')

		# If we don't get an answer, play back we are busy
		if user_hangup is False:
			if dial_status == 'NOANSWER':
				transfer_state = 'NOANSWER'
				user_hangup = play_busy(agi, user_hangup)
			elif dial_status == 'CHANUNAVAIL':
				transfer_state = 'CHANUNAVAIL'
				user_hangup = play_busy(agi, user_hangup)
			elif dial_status == 'DONTCALL':
				transfer_state = 'DONTCALL'
				user_hangup = play_busy(agi, user_hangup)
			elif dial_status == 'TORTURE':
				transfer_state = 'TORTURE'
				user_hangup = play_busy(agi, user_hangup)
			elif dial_status == 'INVALIDARGS':
				transfer_state = 'INVALIDARGS'
				user_hangup = play_busy(agi, user_hangup)
			elif dial_status == 'CANCEL':
				transfer_state = 'CANCEL'
				user_hangup = play_busy(agi, user_hangup)
			elif dial_status == 'CONGESTION':
				transfer_state = 'BUSY'
				user_hangup = play_busy(agi, user_hangup)
			elif dial_status == 'ANSWER':
				transfer_state = 'SUCCESS'
			else:
				transfer_state = 'NOANSWER'
				user_hangup = play_busy(agi, user_hangup)

		# Finish call
		agi.exec_command('StopMixMonitor')
		hangup(agi, user_hangup)

		# Get information required for logging and send ASTERISK_END_CALL event.
		call_id = call_id
		transfer_state_name = transfer_state
		end_time = agi.get_variable('CDR(end)')
		saveHalefEndStartDetails(call_id, transfer_state_name, end_time)
		exitSuccess(agi)
	except AGIHangup:
		logger.info( "HUNGUP OCCURRED")
		sys.exit(0)
	except AGIAppError:	
		raise
	except Exception:
		logMsg = ['python stack trace: '] + traceback.format_exc().split()		
		logger.error( logMsg)
		exitFailure(agi)
	finally:
		logger.info("SCRIPT ENDED ")
	
	
	
if __name__ == '__main__':
    main()

