"""The SquonkServer class handles get, post and delete requests against  
   the squonk base_url using the SquonkAuth class to refresh the      
   authentication token when required.

"""

import requests
import json
import logging
from email.policy import default
from collections import namedtuple
try:
    from .SquonkAuth import SquonkAuth
except:
    from SquonkAuth import SquonkAuth
from collections import namedtuple

# The search result.
# A namedtuple.
SearchResult = namedtuple('SearchResult', 'status_code message json')

class SquonkException(Exception):
    """A basic exception used by the Squonk API
    """
    pass

class SquonkServer:

    def __init__(self, auth, base_url):

        # general settings
        self._base_url = base_url
        self._auth = auth
        logging.debug('SquonkServer created:'+self._base_url)

    # set a request
    def send(self,type,request,form_data=None):
        # Always try to refresh the access token.
        # The token is only refreshed if it is close to expiry.
        self._auth.check_token()

        token = self._auth.get_token()
        url = str(self._base_url + '/' + request)
        logging.debug('SEND:' + type + ' ' + url)
        response = None
        if type == 'get':
            headers = {'Authorization': str('bearer ' + token) }
            response = requests.get(url, headers=headers, verify=True, allow_redirects=True)
        else:
            if type == 'post':
                headers = {'Authorization': str('bearer ' + token), 'Content-Type': 'multipart/form'}
                response = requests.post(url, files=form_data, headers = headers )
            else:
                if type == 'delete':
                    headers = {'Authorization': str('bearer ' + token) }
                    response = requests.delete(url, headers=headers, verify=True, allow_redirects=True)
                else:
                    raise SquonkException('type must be get, post or delete')
        status_code = response.status_code
        logging.debug('GOT response '+str(status_code))
        if not response.status_code in [200, 201]:
            if response.status_code == 404:
                print(response.text)
            else:
                print(response.content)
        return response
