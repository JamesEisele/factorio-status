'''
# RCON commands of interest
# https://wiki.factorio.com/console
    - `/version`: current game version
    - `/time`: info about how old the map is
    - `/players`: all players that have connected
    - `/players online`: online players that have connected
'''

from prometheus_client import start_http_server, Gauge, Counter
import time
import os
import logging
import re

from dotenv import load_dotenv
import factorio_rcon

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define Prometheus metrics for items we scrape.
game_version_metric = Gauge('factorio_game_version', 'Factorio game version running on server (RCON `/version`)', ['game_version'])
gamesave_age_h_metric = Gauge('factorio_gamesave_age', 'How old the Factorio map is in hours (RCON `/time`)')
unique_player_count_metric = Gauge('factorio_unique_player_count', 'Number of unique players that have joined (RCON `/players count`)')
online_player_count_metric = Gauge('factorio_online_player_count', 'Number of online players (RCON `/players online count`)')

# Define Prometheus metrics for scrape process itself.
process_time_s_metric = Gauge('factorio_exporter_process_time_s', 'Time to scrape & process Factorio instance data')

build_info_metric = Gauge('factorio_exporter_ver', 'Build version', ['build_ver'])
build_info_metric.labels('0.1.0').set(1)

def main():
    exporter_port = int(os.getenv('FACTORIO_EXPORTER_PORT', '9042'))
    scrape_interval_s = int(os.getenv('SCRAPE_INTERVAL_S'))

    # Read-in and validate RCON auth from .env file.
    try:
        rcon_password = os.getenv('FACTORIO_RCON_PASSWORD')
        if rcon_password == None:
            raise ValueError('Failed to find auth cookie from .env file. Is "FACTORIO_RCON_PASSWORD" set in .env file?')
        elif rcon_password == 'placeholdersecret':
            raise ValueError('Detected placeholder FACTORIO_RCON_PASSWORD value. Set this to your Factorio server\'s RCON password.')
    except ValueError as error:
        logger.error(f'Error occurred: {error}')
        quit(logger.critical(f'Cannot proceed without RCON authentication access. Quitting...'))

    # Read-in RCON host target & port from .env file.
    try:
        rcon_host = os.getenv('FACTORIO_RCON_HOST')
        if rcon_host == None:
            raise ValueError('Failed to find RCON host from .env file. Is "FACTORIO_RCON_HOST" set?')
    except ValueError as error:
        logger.error(f'Error occurred: {error}')
        quit(logger.critical(f'Cannot proceed without Factorio RCON host to scrape. Quitting...'))
    try:
        rcon_port = os.getenv('FACTORIO_RCON_PORT')
        if rcon_port == None:
            raise ValueError('Failed to find RCON port from .env file. Is "FACTORIO_RCON_PORT" set?')
        else:
            rcon_port = int(rcon_port)
    except ValueError as error:
        logger.error(f'Error occurred: {error}')
        quit(logger.critical(f'Cannot proceed without Factorio RCON port to scrape. Quitting...'))

    start_http_server(exporter_port)
    logger.info(f'Running Factorio exporter on port {exporter_port}. Scraping every {scrape_interval_s} seconds against "{rcon_host}:{rcon_port}".')

    while True:
        start_process_time = time.time()

        rcon_response = scrape_factorio_rcon(rcon_host, rcon_port, rcon_password)
        parsed_rcon_response = parse_factorio_rcon(rcon_response)

        game_version_metric.labels(game_version=parsed_rcon_response['/version']).set(1)
        gamesave_age_h_metric.set(parsed_rcon_response['/time'])
        unique_player_count_metric.set(len(parsed_rcon_response['/players']))
        online_player_count_metric.set(len(parsed_rcon_response['/players online']))

        # TODO: Build status page stuff.
        '''
        # Example JSON from `parsed_rcon_response`
        {
            "/version": "2.0.28",
            "/time": 110.7,
            "/players": [
                "jsmith",
            ],
            "/players online": [
                "jsmith"
            ]
        }
        '''

        end_process_time = time.time()

        process_duration = end_process_time - start_process_time
        process_time_s_metric.set(process_duration)

        sleep_duration = max(scrape_interval_s - process_duration, 0)  # Ensure positive duration.
        time.sleep(sleep_duration)

def scrape_factorio_rcon(rcon_host, rcon_port, rcon_password):
    '''
    Send request to RCON port, scrape data

    Params:
        rcon_host: str; Factorio RCON host instance to scrape.
        rcon_port: int; Factorio RCON host instance port to scrape.
        rcon_password: str; Factorio RCON host instance password.
    Raises:
        # TODO: review these (they shouldn't really be here anyway...)
        RCONNotConnected: if the client is not connected to the RCON server.
        InvalidResponse: if the server returns an invalid response.
        RCONClosed: if the server closes the connection.
        RCONSendError: if any other error occurs while sending the request (including a timeout).
        RCONReceiveError: if any other error occurs while receiving the response (including a timeout).
    Returns:
        response: 
        dict of format key: response.
    '''

    try:
        client = factorio_rcon.RCONClient(rcon_host, rcon_port, rcon_password)
        # To keep it simple, all commands should be in our list below and we'll
        # convert them into a dict later due to the factorio_rcon library. This
        # is preferred in order to allow expected dict calls when parsing later.
        command_list = [
            '/version',
            '/time',
            '/players',
            '/players online',
        ]
        command_dict = {}
        for command in command_list:
            command_dict[command] = command
        response = client.send_commands(command_dict)

    except Exception as error:
        raise error

    return(response)

def parse_factorio_rcon(rcon_response):
    '''
    # TODO: documentation
    '''

    parsed_rcon_response = {}

    # Parse `/version`.
    # Expected value format: '2.0.28'
    parsed_rcon_response['/version'] = rcon_response['/version']

    # Parse `/time`
    # Expected value format: '110 hours, 28 minutes and 57 seconds'
    # TODO: I'm curious what this looks like for a fresh server w/ no players that have joined, maybe default to None?
    try:
        time_str = rcon_response['/time']
        hours = int(time_str.split()[0])
        minutes = int(time_str.split()[2])
        seconds = int(time_str.split()[5])
        total_hours = round(hours + (minutes / 60) + (seconds / 3600), 2)
        parsed_rcon_response['/time'] = total_hours
    except:
        # TODO: change to use proper error logging and nicer value handling on error.
        print('Failed to parse returned time from RCON `/time` command.')

    # Parse `/players` (unique player names that have joined)
    # Expected value format: 'Players (1):\n  ur-mom'
    parsed_rcon_response['/players'] = []
    value_match = re.search(r'\((\d+)\)', rcon_response['/players'])
    if value_match:
        unique_player_count = int(value_match.group(1))

        if unique_player_count > 0:
            raw_unique_player_strings = rcon_response['/players'].split('\n  ')[1:]
            parsed_rcon_response['/players'] = raw_unique_player_strings

    # Parse `/players online`
    # Expected value format: 'Online players (0):', 'Online players (1):\n  jsmith (online)'
    #
    # Factorio RCON adds ' (online)' to player names that are in-game.
    # E.g., "jsmith (online)". No other potential statuses are documented in
    # the Factorio wikibut they should ideally get filtered out as well.
    parsed_rcon_response['/players online'] = []
    value_match = re.search(r'\((\d+)\)', rcon_response['/players online'])
    if value_match:
        online_player_count = int(value_match.group(1))

        if online_player_count > 0:
            raw_online_player_strings = rcon_response['/players online'].split('\n  ')[1:]
            for player_string in raw_online_player_strings:
                if ' (online)' in player_string:
                    destat_player_string = player_string.replace(' (online)', '')
                    parsed_rcon_response['/players online'].append(destat_player_string)

    return parsed_rcon_response

if __name__ == '__main__':
    main()