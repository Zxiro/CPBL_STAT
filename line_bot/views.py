import requests
import logging
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from django.shortcuts import render
from django.http.request import HttpRequest
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from sendfile import sendfile
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextSendMessage, TextMessage
from .fsm import TocMachine

# Create your views here.
logging.basicConfig(level=logging.DEBUG)
line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)

def index(req):
    return HttpResponse('My first line bot app build on Django')
machine = {}

@csrf_exempt
def callback(req : HttpRequest):

    if req.method =='POST':#data in the msg-body
        signature = req.META['HTTP_X_LINE_SIGNATURE']
        body = req.body.decode('utf-8')
        try:
            events = parser.parse(body, signature) #The event get by the HTTP method POST
            #print(events)
        except InvaildSignatureError:
            return HttpResponseForbidden()
        except LineBotApiError:
            return HttpResponseBadRequest()
        
        for event in events:
            if event.source.user_id not in machine:
                machine[event.source.user_id] = TocMachine(
                    states = ['start', 'fsm', 'options', 'player', 'year', 'player_stat','player_name', 'att', 'def', 'team', 'team_stat', 
                    'league',  'league_yt'], 
                    transitions =[
                        { #start to fsm
                            "trigger" : "advance",
                            "source" : "start",
                            "dest" : "fsm",
                            "conditions" : "going_fsm"
                        }, 
                        { #start to options
                            "trigger" : "advance",
                            "source" : "start",
                            "dest" : "options",
                            "conditions" : "going_option"
                        },
                        { #options to player
                            "trigger" : "advance",
                            "source" : "options",
                            "dest" : "player_name",
                            "conditions" : "going_player_name"
                        },
                        { #options to player
                            "trigger" : "advance",
                            "source" : "player_name",
                            "dest" : "player",
                            "conditions" : "going_player"
                        },
                        { #players to year
                            "trigger" : "advance",
                            "source" : "player",
                            "dest" : "player_name",
                            "conditions" : "going_player_name"
                        },
                        { #players to year
                            "trigger" : "advance",
                            "source" : "player",
                            "dest" : "year",
                            "conditions" : "going_year"
                        },
                        { #players to year
                            "trigger" : "advance",
                            "source" : "year",
                            "dest" : "player_stat",
                            "conditions" : "going_player_stat"
                        },
                        { #year to att
                            "trigger" : "advance",
                            "source" : "player_stat",
                            "dest" : "att",
                            "conditions" : "going_att"
                        },
                        { #year to def
                            "trigger" : "advance",
                            "source" : "player_stat",
                            "dest" : "def",
                            "conditions" : "going_def"
                        },
                        { #options to team
                            "trigger" : "advance",
                            "source" : "options",
                            "dest" : "team",
                            "conditions" : "going_team"
                        },
                        { #team_year to team_stat
                            "trigger" : "advance",
                            "source" : "team",
                            "dest" : "team_stat",
                            "conditions" : "going_team_stat"
                        },
                        { #
                            "trigger" : "advance",
                            "source" : "options",
                            "dest" : "league",
                            "conditions" : "going_league"
                        },
                        { #team_year to team_stat
                            "trigger" : "advance",
                            "source" : "league",
                            "dest" : "league_yt",
                            "conditions" : "going_league_yt"
                        },                         
                        { #options and fsm go back to start
                            "trigger" : "advance",
                            "source" : ["start", "fsm", "options"],
                            "dest" : "start",
                            "conditions" : "back_start"
                        },
                        { #options and fsm go back to start
                            "trigger" : "advance",
                            "source" : ["league_yt"],
                            "dest" : "league",
                            "conditions" : "back_league"
                        },
                        { #
                            "trigger" : "advance",
                            "source" : ["team_stat"],
                            "dest" : "team",
                            "conditions" : "back_team"
                        },
                        { #att and def go back to year
                            "trigger" : "advance",
                            "source" : ["att", "def", 'player_stat'],
                            "dest" : "player",
                            "conditions" : "back_player"
                        },
                        { #att and def go back to year
                            "trigger" : "advance",
                            "source" : ["att", "def", 'player_stat'],
                            "dest" : "year",
                            "conditions" : "back_year"
                        },                        
                        { #player, team and league go back to options
                            "trigger" : "advance",
                            "source" : ['player', 'team', 'league','league_yt',
                            'year', 'player_stat','att', 'def', 'team_stat'],
                            "dest" : "options",
                            "conditions" : "back_options"
                        }, 
                    ],
                    initial="options", #init needs to be start can use this para to debug
                    auto_transitions = False,
                    show_conditions = True,
                )
            machine[event.source.user_id].get_graph().draw("fsm.png", prog="dot", format="png")
            #Wait for the input
            if not isinstance(event, MessageEvent):
                continue
            if not isinstance(event.message, TextMessage):
                continue
            if not isinstance(event.message.text, str):
                continue
            response = machine[event.source.user_id].advance(event)
            if response == False:
                line_bot_api.reply_message(  # 回復傳入的訊息文字
                    event.reply_token,
                    TextSendMessage(text= "Invalid command, try again")
                )
            #machine.get_graph().draw("fsm.png", prog="dot", format="png")
        return HttpResponse()
    else:
        return HttpResponseBadRequest()