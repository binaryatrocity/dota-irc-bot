from ircutils import bot, events, format
import requests
import simplejson as json
import urllib2, random, re
import HTMLParser
from collections import deque

class DotaMatch:
    api_key="4CEC40C492B1AB15EEBA07681E6EDBBD"
    hero_data = {}

    def __init__(self, channel, user, command, params):
        self.channel = channel
        self.requester = user
        self.command = command

        if not params:
            self.query = [user]
        else:
            self.query = params

        self.matches = []
        self.notice = []
        self.steam_id = ''

    def get_hero_values(self):
        xhr = urllib2.Request("https://api.steampowered.com/IEconDOTA2_570/GetHeroes/v0001/?key="+self.api_key+"&language=en_us")
        o = urllib2.build_opener()
        f = o.open(xhr)
        data = json.load(f)

        for hero in data['result']['heroes']:
            self.hero_data[hero['id']] = hero

    def lookup_player(self, query):
        xhr = urllib2.Request("http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key="+self.api_key+"&vanityurl="+query[0])
        o = urllib2.build_opener()
        f = o.open(xhr)
        data = json.load(f)

        if data['response']['success'] == 1:
            self.steam_id = data['response']['steamid']
        else:
            self.steam_id = 'NULL'

    def get_latest_match_id(self):
            if self.command == "!MATCHBYID":
                return True

            xhr = urllib2.Request("https://api.steampowered.com/IDOTA2Match_570/GetMatchHistory/V001/?key="+self.api_key+"&account_id="+self.steam_id)
            o = urllib2.build_opener()
            f = o.open(xhr)
            data = json.load(f)

            # did we get matches back?
            try:
                self.matches = data['result']['matches']
                return True
            except KeyError:
                return False
    
    def get_match_info(self):
            try:
                xhr = urllib2.Request("https://api.steampowered.com/IDOTA2Match_570/GetMatchDetails/V001/?key="+self.api_key+"&match_id="+str(self.matches[0]['match_id']))
                o = urllib2.build_opener()
                f = o.open(xhr)
                data = json.load(f)
            except Exception as e:
                self.notice.append("Problem connecting to the Dota2 API.")
            else:
                # get users 32-bit SteamID so we can look them up
                sid = int(self.steam_id) - 76561197960265728
                p = {}

                for player in data['result']['players']:
                    if player['account_id'] == sid:
                        p = player
                        break
                if not p:
                    self.notice.append("Player {} not found in match {}.".format(self.query[0], self.query[1]))
                    return

                hero_id = self.hero_data[p['hero_id']]['localized_name']
                kills = p['kills']
                deaths = p['deaths']
                assists = p['assists']
                last_hits = p['last_hits']
                gpm = p['gold_per_min']
                time = data['result']['duration'] / 60

                if( p['player_slot'] & (1<<7) == 0 ):
                    team = 'Radiant'
                else:
                    team = 'Dire'

                if( team is 'Dire' and not bool(data['result']['radiant_win'])):
                    result = 'Victory!'
                elif( team is 'Radiant' and bool(data['result']['radiant_win'])):
                    result = 'Victory!'
                else:
                    result = 'Defeat!'
                
                # print match info 
                self.notice.append("Match for \x02{0}\x02 - Hero: \x0311{1}\x03, K/D/A: \x0303{2}/{3}/{4}\x03, Last Hits: \x0306{5}\x03, GPM: \x0308{6}\x03. Game Length: {7} mins. Team: {8} - {9}.".format(self.query[0], hero_id, kills, deaths, assists, last_hits, gpm, time, team, result))

    def list_latest_matches(self):
            # get users 32-bit SteamID so we can look them up
            sid = int(self.steam_id) - 76561197960265728
            p = {}
            self.notice.append("Recent Matches for " + self.query[0] + ":")

            for count, match in enumerate(self.matches):
                if count > 3:
                    break
            
                try:
                    xhr = urllib2.Request("https://api.steampowered.com/IDOTA2Match_570/GetMatchDetails/V001/?key="+self.api_key+"&match_id="+str(match['match_id']))
                    o = urllib2.build_opener()
                    f = o.open(xhr)
                    data = json.load(f)
                except Exception as e:
                    self.notice.append("There was an error connecting to the Dota2 API.")
                else:
                    for player in data['result']['players']:
                        if player['account_id'] == sid:
                            p = player
                            break

                    print self.hero_data[p['hero_id']]
                    hero_id = self.hero_data[p['hero_id']]['localized_name']
                    kills = p['kills']
                    deaths = p['deaths']
                    assists = p['assists']

                    if( p['player_slot'] & (1<<7) == 0 ):
                        team = 'Radiant'
                    else:
                        team = 'Dire'

                    if( team is 'Dire' and not bool(data['result']['radiant_win'])):
                        result = 'Victory!'
                    elif( team is 'Radiant' and bool(data['result']['radiant_win'])):
                        result = 'Victory!'
                    else:
                        result = 'Defeat!'
                    
                    self.notice.append(" [\x02{0}\x02]:  \x0311{1}\x03 - \x0303{2}/{3}/{4}\x03 - {5}".format(match['match_id'], hero_id, kills, deaths, assists, result))

class DoobBot(bot.SimpleBot):
    auth_pool = deque() 
    actions = ["!MATCH", "!MATCHES", "!MATCHBYID"]

    def on_channel_message(self, event):
        url = re.search('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F[0-9a-fA-F]))+', event.message)
        channel = event.target
        user = event.source
        message = event.message.split();
        command = message[0].upper()
        params = message[1:]

        if url:
            self.do_printurltitle(channel, user, url.group())
        elif command == "!ROLL":
            self.do_rolldice(channel, user, params)
        elif command == "!BTCX":
            self.do_getbtcinfo(channel, user, False, params)
        elif command == "!BTC":
            self.do_getbtcinfo(channel, user, True, params)
        elif command == "!WEATHER":
            self.do_getweather(channel, user, params)
        elif command == "!REDDITNEWS":
            self.do_getnews(channel, user, params)
        elif command == "!OW":
            self.do_overwatch(channel, user, params)
        elif command == "!ABOUT":
            self.send_message(channel, "I am DotaBot, I bring info about Dota2 Matches. Ask for a !match. See !help for more.")
        elif command == "!HELP":
            self.send_message(user, "I am DotaBot - these are my available commands.")
            self.send_message(user, "!MATCH <steam_vanity_name> - Get info about users latest match, if no argument passes your IRC nickname.")
            self.send_message(user, "!MATCHES <steam_vanity_name> - Get a list of recent matches for the user, if no argument passes your IRC nickname.")
            self.send_message(user, "!MATCHBYID <steam_vanity_name> <match_id_#> - Get info about particular match by ID#.")
            self.send_message(user, "!ROLL ?D? - Simulate dice rolling (e.g. !roll 1d6 or !roll 5d20)")
            self.send_message(user, "!WEATHER <name or zip> - Query wunderground for weather data")
            self.send_message(user, "!REDDITNEWS <subreddit> - Pull a new story from <subreddit>, defaults to dota2.")
            self.send_message(user, "!DOTANEWS - pulls latest news story about Dota2 from Steamworks.")
            self.send_message(user, "!BTC - List current price of BTC in various fiat currencies.")
            self.send_message(user, "!BTCX <amount> <currency> - Convert <amount> bitcoins to the local currency of choice.")
            self.send_message(user, "Written by binaryatrocity - br4n@atr0phy.net")
        elif command in self.actions:
            m = DotaMatch(channel, user, command, params)
            self.auth_pool.append(m);
            self.send_message('NICKSERV', 'STATUS {0}'.format(user))

    def on_private_notice(self, event):
        if(event.message[0] == "2"):
            c = self.auth_pool.popleft()
            c.lookup_player(c.query)
            if c.steam_id == 'NULL':
                self.send_message(c.channel, "Unable to find SteamID for player "+c.query[0])
            else:
                status = c.get_latest_match_id()
                if status:
                    if c.command == "!MATCHES": c.list_latest_matches()
                    elif c.command == "!MATCH": c.get_match_info()
                    elif c.command == "!MATCHBYID":
                        c.matches.append({'match_id':c.query[1]})
                        c.get_match_info()
                    
                    for msg in c.notice:
                        self.send_message(c.channel, msg)
                else:
                    self.send_message(c.channel, "No matches found for player "+c.query[0])

        elif(event.message[0] == "1" or event.message[0] == "0"):
            c = self.auth_pool.popleft()
            self.send_message(c.channel, "You must be registered with NickServ before requesting match info! '/msg NickServ register HELP' for more info.")

    def on_private_message(self, event):
        user = event.source
        message = event.message.split()
        command = message[0].upper()
        params = message[1:]

        if command.upper() == "SAY":
            mstr = ''
            for msg in params:
                mstr = mstr +' '+ msg
            self.send_message(self.user, mstr)
        if command.upper() == "QUIT":
            self.disconnect(params)

    def do_getnews(self, channel, user, params):
        if not params:
            params.append('dota2')
        try:
            raw_data = urllib2.Request("http://www.reddit.com/r/"+params[0]+"/new.json?sort=new")
            o = urllib2.build_opener()
            f = o.open(raw_data)
            data = json.load(f)
        except urllib2.HTTPError as e:
            self.send_message(channel, "There was a problem accessing news.")
        except Exception as e:
            print e
        else:
            items = [ x['data'] for x in data['data']['children'] ]

            rand = random.randint(0,10)

            notice = "News from r/{0}: {1} - [{2}]".format(params[0], items[rand]['title'], items[rand]['url'])
            self.send_message(channel, notice)

    def do_printurltitle(self, channel, user, url):
        try:
            html_parser = HTMLParser.HTMLParser()
            title = html_parser.unescape(urllib2.urlopen(url, timeout=1).read(10000).split('<title>')[1].split('</title>')[0].strip()).encode('utf-8')
            notice = "{}'s URL: {}".format(user, title)
            self.send_message(channel, notice)
        except urllib2.URLError:
            pass
        except IndexError:
            pass
        except Exception as e:
            print e

    def do_getweather(self, channel, user, params):
        try:
            raw_data = urllib2.Request("http://api.openweathermap.org/data/2.5/weather?q="+params[0]+"&units=imperial")
            o = urllib2.build_opener()
            f = o.open(raw_data)

            data = json.load(f)
            city = data['name']
            country = data['sys']['country']
            lat, lon = data['coord']['lat'], data['coord']['lon']
            condition = data['weather'][0]['main']
            temp = data['main']['temp']
            humidity = data['main']['humidity']
            high = data['main']['temp_max']
            low = data['main']['temp_min']
            winds = data['wind']['speed']

            notice = "Weather for {}, {} ({}, {}): Currently {} at {} degrees with {}% humidity and winds at {} mph. High: {}, Low: {}".format(city, country, lat, lon, condition, temp, humidity, winds, high, low)
            self.send_message(channel, notice)
        except urllib2.HTTPError as e:
            self.send_message(channel, "Unable to find weather for "+params[0])
        except urllib2.URLError as e:
            self.send_message(channel, "There was a problem accessing weather info.")
        except Exception as e:
            print e 

    def do_getbtcinfo(self, channel, user, exch, params):
        if not exch:
            try:
                data = json.load(urllib2.build_opener().open(urllib2.Request("http://blockchain.info/tobtc?currency="+params[1].upper()+"&value="+params[0])))

                notice = "{}: Value of {} {} in BTC is \x03{}\x03".format(user, params[0], params[1].upper(), data)
                self.send_message(channel, notice)
            except Exception:
                pass
        else:
            try:
                data = json.load(urllib2.build_opener().open(urllib2.Request("http://blockchain.info/ticker")))

                notice = "Current price of BTC: USD[{}], GBP[{}], EUR[{}]".format(data['USD']['last'], data['GBP']['last'], data['EUR']['last'])
                self.send_message(channel, notice)
                pass
            except Exception as e:
                print e

    def do_rolldice(self, channel, user, params):
        try:
            dice = params[0].split('d')
            rolls = []
            for roll in range(0,int(dice[0])):
                rolls.append(random.randint(1,int(dice[1])))
        except Exception as e:
            pass
        else:
            notice = "Rolls for {}: {!s}. Total of {}".format(user, rolls, sum(rolls))
            self.send_message(channel, notice)

    def do_overwatch(self, channel, user, params):
        ow_url = "https://owapi.net/api/v1/u"
        battletag = params[0]
        battletag = battletag.replace('#', '-')
        print params

        try:
            print '1'
            if params[1].upper() == 'STATS':
                api_url = "{}/{}/stats".format(ow_url, battletag)
                #data = json.load(urllib2.build_opener(urllib2.HTTPSHandler()).open(urllib2.Request(api_url)))
                data = requests.get(api_url)
                sd = data.json()['overall_stats']
                message = u"{}'s Overwatch Stats: Lvl {} - {} Games ({}W/{}L) for {}% win rate.".format(
                        user, sd['level'], sd['games'], sd['wins'], sd['losses'], sd['win_rate'])
            elif params[1].upper() == 'HEROES':
                print '2'
                api_url = "{}/{}/heroes".format(ow_url, battletag)
                data = json.load(urllib2.build_opener(urllib2.HTTPSHandler()).open(urllib2.Request(api_url)))
                print '3'
                sd = data['heroes']
                print '4'
                import pudb; pudb
                message = u"{}'s Overwatch Heroes:\r \
                    {} [{} games, {} kda, {} winrate]\r \
                    {} [{} games, {} kda, {} winrate]\r \
                    {} [{} games, {} kda, {} winrate]".format(
                            user,
                            sd[0]['name'], sd[0]['games'], sd[0]['kpd'], sd[0]['winrate'],
                            sd[1]['name'], sd[1]['games'], sd[1]['kpd'], sd[1]['winrate'],
                            sd[2]['name'], sd[2]['games'], sd[2]['kpd'], sd[2]['winrate']
                )
        except IndexError as e:
            message = '!ow [battletag] [stats/heroes]'
            print e

        # Send data to channel
        self.send_message(channel, message.encode('ascii', 'replace'))
        print "message sent"


# Create a new bot, and run it!
if __name__ == "__main__":
    doob = DoobBot("MatchBot")
    init_match = DotaMatch('#atr0phy', 'SYSTEM', 'START', 'INIT')
    init_match.get_hero_values()
    doob.connect("irc.oftc.net", channel=['#dotanoobs', '#digital-deception', '#atr0phy'])
    doob.start()
