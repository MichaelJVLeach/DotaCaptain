import os, logging, argparse
from dota2py import api
from util import get_game_mode_string
from pymongo import MongoClient
from time import sleep
from sys import exit

#client = MongoClient(os.getenv('DOTABOT_DB_SERVER', 'localhost'), 27017)
#client = MongoClient(('ITW8039800.comm.ad.roke.co.uk', 'localhost'), 27017)
client = MongoClient('localhost', 27017)
db = client['dotaDB']
match_collection = db.matches

logging.basicConfig(filename='..\log.txt')
logger = logging.getLogger('dotabot')

def setup():
    '''Setup the API, etc.'''
    logger.setLevel(logging.DEBUG)

    #API_KEY = os.getenv('DOTABOT_API_KEY')
    API_KEY = '8F002160EB2A8474EBC95F9CAAA24A1F'
    if not API_KEY:
        raise NameError('Please set the DOTABOT_API_KEY environment variables.')
    api.set_api_key(API_KEY)

def is_valid_match(gmd_result):
    '''Returns True if the given match details result should be considered,
    and False otherwise.'''
    for player in gmd_result['players']:
        if player['leaver_status'] is not 0:
            return False
    return True

def process_replay(match_id):
    '''Download, parse, and record data from the replay of the given match_id.'''
    # TODO
    pass

def process_match_details(match_id):
    '''Get the details of the given match_id, check if it's valid, and
    if it is, add it as a record in the database and spawn a thread to
    download and parse the corresponding replay.'''
    sleep(1.0)
    gmd = api.get_match_details(match_id)['result']

    if not is_valid_match(gmd):
        logger.debug('Not considering match %s.' % match_id)
        return

    match_collection.insert(gmd)

    game_mode = get_game_mode_string(gmd['game_mode'])
    logger.debug('Processed Match ID: %s - Game Mode: %s' % (match_id, game_mode))
    print('Processed: ', match_id)
    # TODO:
    # Spawn replay parser thread if there aren't too many already

def count_items_in_collection():
    '''Counts the number of matches stored in the database'''
    return match_collection.count()

def main():
    '''The main entry point of dotabot.'''
    start_match_id = None
    print('Start items in database: ', count_items_in_collection())
    while True:
        # Note: GetMatchHistory returns a list of matches in descending order,
        # going back in time.
        sleep(1.0)
        logger.debug('Doing GMH query for start_at_match_id=%s' % start_match_id)
        print('Aquiring new matches')
        #gmh = api.get_match_history(start_at_match_id=start_match_id,
                                    #skill=3,
                                    #game_mode=2,
                                    #min_players=10)['result']
        gmh = api.get_match_history(skill=3,game_mode=2,min_players=10)['result']
        error_code = gmh['status']
        matches = gmh['matches']

        if error_code is not 1:
            msg = 'GMH query at match_id %s had error code %s. Retrying.' % (start_match_id, error_code)
            logger.debug(msg)
            continue

        if len(matches) is 1:
            logger.debug('Finished processing all 500 most recent matches.')

        for match in matches:
            match_id = match['match_id']
            last_match_id = match_id
            if match_collection.find_one({'match_id':match_id}) != None:
                logger.debug('Encountered match %s already in database.' % match_id)
                # exit loop so we don't process already stored games
                continue

            while True:
                try:
                    process_match_details(match_id)
                except:
                    print('Unable to process match: 503 Server Error: Service Unavailable')
                    continue
                break
        print('Items in database: ', count_items_in_collection())
        logger.debug('Match_id of last match of GMH query: %s' % last_match_id)
        # We don't want to record the last match twice, so subtract 1
        start_match_id = last_match_id - 1

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Bot for collecting data from 500 most recent DOTA2 matches')
    args = p.parse_args()

    setup()
    main()
