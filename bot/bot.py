import os
from ciscosparkbot import SparkBot
from ciscosparkapi import CiscoSparkAPI
import requests
import re

# Get Bot details from environment
bot_email = os.getenv("QOSBOTEMAIL")
spark_token = os.getenv("QOSBOTTOKEN")
bot_url = os.getenv("QOSBOTURL")
bot_app_name = os.getenv("QOSBOTNAME")

# Get EDQOS App details from environment
edqos_app_url = os.getenv("EDQOSAPPURL")


"""
_sessions =  [
                {
                    personId,
                    roomId,
                    policy_scope
                }
            ]
"""
_sessions = []


def create_session(person_id, room_id, scope):
    _sessions.append({'personId': person_id, 'roomId': room_id, 'policyScope': scope})

def current_session(person_id, room_id):
    person_matches = [session for session in _sessions if session['personId'] == person_id]
    for match in person_matches:
        if match['roomId'] == room_id:
            return match

# EDQoS App API functions
def get_policy_tags():
    r = requests.get(edqos_app_url + "/api/policy_tags/")
    if r.status_code == 200:
        return r.json()

def get_applications(search):
    if not search:
        return None
    else:
        r = requests.get(edqos_app_url + "/api/applications/?search=" + search)
        if r.status_code == 200:
            return r.json()

def get_app_relevance(scope, app):
    r = requests.get(edqos_app_url + "/api/relevance/?app=" + app + "&policy=" + scope)
    if r.status_code == 200:
        return r.json()

# Create bot functions
def list_policy_tags(incoming_msg):
    tags = get_policy_tags()
    message = ""
    if tags:
        for tag in tags:
            message += "* {}\n".format(tag)
    return message

def set_policy_scope(incoming_msg):
    s = re.search('set policy scope (\S+)', incoming_msg.text)
    scope = s.group(1)
    if scope not in get_policy_tags():
        return "Invalid policy scope"
    else:
        create_session(incoming_msg.personId, incoming_msg.roomId, scope)
        return "Set policy scope for session to {}".format(scope)

def current_policy_scope(incoming_msg):
    person_id = incoming_msg.personId
    room_id = incoming_msg.roomId
    session = current_session(person_id, room_id)
    if session:
        return session['policyScope']
    else:
        return "No policy scope set yet; use \"set policy scope\" to set one."

def search_app(incoming_msg):
    person_id = incoming_msg.personId
    room_id = incoming_msg.roomId
    s = re.search('search app (\S+)', incoming_msg.text)
    search = s.group(1)
    session = current_session(person_id, room_id)
    message = ""
    if session:
        scope = session['policyScope']
        apps = get_applications(search)
        if len(apps) > 15:
            return "Search yielded {} results; try being more specific"
        for app in apps:
            relevance = get_app_relevance(scope, app)
            message += "* {} has relevance {}\n".format(app, relevance)
    else:
        apps = get_applications(search)
        if len(apps) > 15:
            return "Search yielded {} results; try being more specific"
        for app in apps:
            message += "* {}\n".format(app)
    return message

# Initialize bot
bot = SparkBot(bot_app_name, spark_bot_token=spark_token,
               spark_bot_url=bot_url, spark_bot_email=bot_email)

# Add bot commands and run bot
bot.add_command('list policy tags', 'This will list the policy tags configured on APIC EM', list_policy_tags)
bot.add_command('set policy scope', 'This will set the policy scope that you wish to modify for the session', set_policy_scope)
bot.add_command('current policy scope', 'This will return the current policy scope for the session', current_policy_scope)
bot.add_command('search app', 'This will return applications matching search criteria; if scope already set, it will also return the applications relevance level', search_app)
bot.run(host='0.0.0.0', port=5000)
