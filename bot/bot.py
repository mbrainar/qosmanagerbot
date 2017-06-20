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
                    policyScope
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


#
# EDQoS App API functions
#
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

def set_app_relevance(scope, app, relevance):
    data = {'app': app, 'policy': scope, 'relevance': relevance}
    r = requests.post(edqos_app_url + "/api/relevance/", data=data)
    if r.status_code == 200:
        return r.json()


#
# Create bot functions
#
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
    message = ""
    if scope not in get_policy_tags():
        return "Invalid policy scope"
    else:
        session = current_session(incoming_msg.personId, incoming_msg.roomId)
        if session:
            _sessions.remove(session)
            message = "Updating existing session; "
        message = message + "Set policy scope for session to {}".format(scope)
        create_session(incoming_msg.personId, incoming_msg.roomId, scope)
        return message

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
        if len(apps) == 0:
            return "No application name matching {}".format(search)
        elif len(apps) > 15:
            return "Search yielded {} results; try being more specific".format(len(apps))
        for app in apps:
            relevance = get_app_relevance(scope, app)
            message += "* {} has relevance {}\n".format(app, relevance)
    else:
        apps = get_applications(search)
        if len(apps) == 0:
            return "No application name matching {}".format(search)
        elif len(apps) > 15:
            return "Search yielded {} results; try being more specific".format(len(apps))
        for app in apps:
            message += "* {}\n".format(app)
    return message

def set_relevance(incoming_msg):
    person_id = incoming_msg.personId
    room_id = incoming_msg.roomId
    s = re.search('set relevance\s(\S+)\s(\S+)', incoming_msg.text)
    app = s.group(1) if s else None
    relevance = s.group(2) if s else None
    message = None
    valid_relevance = ['Business-Relevant', 'Default', 'Business-Irrelevant']
    if not app or not relevance:
        return "You need to specify an application name and relevance level"
    elif app not in get_applications(app):
        return "No application name matching {}".format(app)
    elif relevance not in valid_relevance:
        return "{} is not a valid relevance; please use: {}".format(relevance, ', '.join(valid_relevance))

    session = current_session(person_id, room_id)
    scope = session['policyScope']
    if not scope:
        return "No policy scope set yet; use \"set policy scope\" to set one."

    current_relevance = get_app_relevance(scope, app)
    if current_relevance == relevance:
        return "{} is already set to {}; no action needed".format(app, current_relevance)
    else:
        task_id = set_app_relevance(scope, app, relevance)
        if task_id:
            message = "Success; {} has been set to {}".format(app, relevance)
    return message


#
# Initialize bot
#
bot = SparkBot(bot_app_name, spark_bot_token=spark_token,
               spark_bot_url=bot_url, spark_bot_email=bot_email)

# Add bot commands
bot.commands = dict()
bot.add_command('list policy tags', 'This will list the policy tags configured on APIC EM', list_policy_tags)
bot.add_command('set policy scope', 'This will set the policy scope that you wish to modify for the session', set_policy_scope)
bot.add_command('current policy scope', 'This will return the current policy scope for the session', current_policy_scope)
bot.add_command('search app', 'This will return applications matching search criteria; if scope already set, it will also return the applications relevance level', search_app)
bot.add_command('set relevance', 'This will set the relevance level for the provided app; ex. set relevance <app name> <relevance>', set_relevance)

# Run bot
bot.run(host='0.0.0.0', port=5000)
