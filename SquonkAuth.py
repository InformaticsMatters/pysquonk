"""A Python wrapper around the Informatics Matters Squonk service REST API 
   authentication

Authentication obtains a REST API token from the Squonk server.
Facillitates automatic token renewel so, for the lifetime of your request
processing you should only need to authenticate once.

"""

import datetime
import os
import pprint
import sys
import urllib

import requests
import logging

# The version of this module.
# Modify with every change, complying with
# semantic 2.0.0 rules.
__version__ = '1.0.0'

class SquonkAuthException(Exception):
    """A basic exception used by the SquonkAuth class.
    """
    pass

class SquonkAuth:
    """The SquonkAuth REST API wrapper class.

    Provides convenient and auto-refreshed token-based access to
    the REST API.
    """

    INTERNAL_ERROR_CODE = 600

    CLIENT_ID = 'squonk-jobexecutor'
    REQUEST_TIMOUT_S = 20

    # The minimum remaining life of a token (or refresh token) (in seconds)
    # before an automatic refresh is triggered.
    TOKEN_REFRESH_DEADLINE_S = datetime.timedelta(seconds=45)

    def __init__(self, auth_uri, username=None, password=None, client_secret=None):
        """Initialises the SquonkAuth module.
        An API token is collected when you 'authenticate'.

        :param auth_uri: The squonk authentication host and designated port,
                             i.e. http://fragnet.squonk.it:8080
        :type auth_uri: ``str``
        :param username: A squonk username
        :type username: ``str``
        :param password: The squonk user's password
        :type password: ``str``
        :param client_secret: The squonk servers client secret
        :type password: ``str``
        """

        if not ((username and password) or client_secret):
            raise SquonkAuthException('Must specify username and password or client secret')
        # We do nothing other then record parameters
        # to be used elsewhere in the class...
        self._username = username
        self._password = password
        self._client_secret = client_secret
        self._auth_uri = auth_uri

        self._access_token = None
        self._access_token_expiry = None
        self._refresh_token = None
        self._refresh_token_expiry = None

        logging.debug('auth_uri={} username={}'.format(self._auth_uri,
                                              self._username))

    def _extract_tokens(self, json):
        """Gets tokens from a valid json response.
        The JSON is expected to contain an 'access_token',
        'refresh_token', 'expires_in' and 'refresh_expires_in'.

        We calculate the token expiry times here,
        which is used by 'check_token()' to automatically
        renew the token.

        :param json: The JSON payload, containing tokens
        """
        if 'access_token' not in json:
            logging.error('access_token is not in the json')
            return False
        if 'expires_in' not in json:
            logging.error('expires_in is not in the json')
            return False
        if 'refresh_token' not in json:
            logging.error('refresh_token is not in the json')
            return False

        # The refresh token may not have an expiry...
        if 'refresh_expires_in' not in json:
            logging.debug('refresh_expires_in is not in the json')

        time_now = datetime.datetime.now()
        self._access_token =json['access_token']
        self._access_token_expiry = time_now + \
                                    datetime.timedelta(seconds=json['expires_in'])
        self._refresh_token = json['refresh_token']
        if 'refresh_expires_in' in json:
            self._refresh_token_expiry = time_now + \
                                         datetime.timedelta(seconds=json['refresh_expires_in'])
        else:
            logging.debug('Setting _refresh_expires_in to None (no refresh expiry)...')
            self._refresh_token_expiry = None

        logging.debug('_access_token_expiry={}'.format(self._access_token_expiry))
        logging.debug('_refresh_token_expiry={}'.format(self._refresh_token_expiry))

        # OK if we get here...
        return True

    def _get_new_token(self):
        """Gets a (new) API access token.
        """
        logging.debug('Getting a new access token...')

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        if self._username:
            logging.debug('authenticate using username, password')
            payload = {'grant_type': 'password',
                       'client_id': SquonkAuth.CLIENT_ID,
                       'username': self._username,
                       'password': self._password}
        else:
            logging.debug('authenticate using client_secret')
            payload = {'grant_type': 'client_credentials',
                       'client_id': SquonkAuth.CLIENT_ID,
                       'client_secret': self._client_secret}
        try:
            resp = requests.post(self._auth_uri,
                                 data=payload,
                                 headers=headers,
                                 timeout=SquonkAuth.REQUEST_TIMOUT_S)
        except requests.exceptions.ConnectTimeout:
            logging.warning('_get_new_token() POST timeout')
            return False

        if resp.status_code != 200:
            logging.warning('_get_new_token() resp.status_code={}'.format(resp.status_code))
            return False

        # Get the tokens from the response...
        logging.debug('Got token.')
        return self._extract_tokens(resp.json())

    def _refresh_existing_token(self):
        """Refreshes an (existing) API access token.
        """
        logging.debug('Refreshing the existing access token...')

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        payload = {'grant_type': 'refresh_token',
                   'client_id': SquonkAuth.CLIENT_ID,
                   'refresh_token': self._refresh_token}
        try:
            resp = requests.post(self._auth_uri,
                                 data=payload,
                                 headers=headers,
                                 timeout=SquonkAuth.REQUEST_TIMOUT_S)
        except requests.exceptions.ConnectTimeout:
            logging.warning('_refresh_existing_token() POST timeout')
            return False

        if resp.status_code != 200:
            logging.warning('_refresh_existing_token() resp.status_code={}'.format(resp.status_code))
            return False

        # Get the tokens from the response...
        logging.debug('Refreshed token.')
        return self._extract_tokens(resp.json())

    def check_token(self):
        """Refreshes the access token if it's close to expiry.
        (i.e. if it's within the refresh period). If the refresh token
        is about to expire (i.e. there's been a long time between searches)
        then we get a new token.

        :returns: False if the token could not be refreshed.
        """
        logging.debug('Checking token...')

        time_now = datetime.datetime.now()
        remaining_token_time = self._access_token_expiry - time_now
        if remaining_token_time >= SquonkAuth.TOKEN_REFRESH_DEADLINE_S:
            # Token's got plenty of time left to live.
            # No need to refresh or get a new token.
            logging.debug('Token still has plenty of life remaining.')
            return

        # If the refresh token is still 'young' (or has no expiry time)
        # then we can rely on refreshing the existing token using it. Otherwise
        # we should collect a whole new token...
        #
        # We set the reaming to me to the limit (which means we'll refresh)
        # but we replace that with any remaining time in the refresh token).
        # So - if there is not expiry time for the refresh token then
        # we always refresh.
        remaining_refresh_time = SquonkAuth.TOKEN_REFRESH_DEADLINE_S
        if self._refresh_token_expiry:
            remaining_refresh_time = self._refresh_token_expiry - time_now
        if remaining_refresh_time >= SquonkAuth.TOKEN_REFRESH_DEADLINE_S:
            # We should be able to refresh the existing token...
            logging.debug('Token too old, refreshing...')
            status = self._refresh_existing_token()
        else:
            # The refresh token is too old,
            # we need to get a new token...
            logging.debug('Refresh token too old, getting a new token...')
            status = self._get_new_token()

        # Raise exception if failure
        if status:
            logging.debug('Got new token.')
        else:
            raise SquonkAuthException('Refresh Failure')

    def authenticate(self):
        """Authenticates against the server provided in the class initialiser.
        Here we obtain a fresh access and refresh token.

        :returns: True on success

        :raises: SquonkAuthException on error
        """
        logging.debug('Authenticating...')

        status = self._get_new_token()
        if not status:
            raise SquonkAuthException('Unsuccessful Authentication')

        logging.debug('Authenticated.')

    def get_token(self):
        return self._access_token
