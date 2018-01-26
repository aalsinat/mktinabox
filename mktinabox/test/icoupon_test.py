import logging
import time
import urllib
import json
from urllib2 import Request, urlopen, URLError, HTTPError
import urllib2

GRANT_TYPE = "client_credentials"
CLIENT_ID = "AreasPOS"
CLIENT_SECRET_PPD = "qYGqKOWR6qP7hp8KpfuUpSMF8BzdG2a76GaOh1SGyNqPBmFP0BZAeifIF8wf6a"
CLIENT_SECRET_LIVE = "kelxTByKeM7YUw58EjFU0xIj8jGcdDUZlqQh5tTHZYU8e7GA5bOHQm7keBDMy6"
URL_LIVE = "https://icoupon.global/api/token"
URL_PPD = "https://ppd.icoupon.global/api/token"
REDEEM_URL = "https://icoupon.global/api/v1/coupons"
SERVICE_PROVIDER = 8432897
OUTLET_REF = 3143501
OUTLET_NAME = "Cafe di Roma"
ITERATIONS = 100


def get_token(timeout=10):
    """
    Function to request an access token for a given API key.
    :param url: iCoupon REST API resource URL to request an access token
    :param grant_type: OAuth grant type
    :param client_id: OAuth client identifier
    :param client_secret: OAuth client secret key
    :param timeout: maximum time for request in seconds
    :return: string containing authorization token
    """
    headers_info = {
        'Content-Type': 'application/json',
    }
    data = {
        'grant_type': GRANT_TYPE,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET_LIVE
    }
    request = Request(URL_LIVE, data=urllib.urlencode(data), headers=headers_info)
    try:
        response = urlopen(request, timeout=timeout)
    except URLError as e:
        if hasattr(e, 'reason'):
            logger.error('We failed to reach the server.')
            logger.error('Reason: %s', e.reason)
            # logger.error('Error url: %s', e.geturl())
            # logger.error('Error info: %s', e.info())
            logger.error('Error info: %s', e)
            raise e
        elif hasattr(e, 'code'):
            logger.error('The server could not fulfill the request.')
            logger.error('Error code: %s', e.code)
            # logger.error('Error url: %s', e.geturl())
            # logger.error('Error info: %s', e.info())
            logger.error('Error info: %s', e)
            raise e
    else:
        body = json.loads(response.read())
        logger.info('Response from token request (%d, %s)', response.getcode(), body['access_token'])
        response.close()
        return response.getcode(), body

def redeem_coupon(url, access_token, action='redeem', location_ref='ALC', timeout=10):
    """
    Function to redeem coupons using iCoupon REST API
    :param access_token: the bearer token that needs to be provided in every call
    :param till_ref: till specific data, hopefully check or receipt identifier
    :param location_ref: the airport or site code
    :param trading_outlet: unique identifier of the trading outlet
    :param trading_name: the name of the trading outlet
    :param service_provider: retailer unique identifier
    :param action: the action to perform on the coupon
    :param url: iCoupon REST API resource URL to redeem coupons.
    :param coupon_ref: coupon identifier
    :param timeout: maximum time for request in seconds
    :return: response code from REST API request
    """
    headers_info = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {}'.format(access_token)
    }
    data = {
        'action': action,
        'tillRef': "T001-134004",
        'locationRef': location_ref,
        'serviceProviderRef': str(SERVICE_PROVIDER),
        'tradingOutletRef': str(OUTLET_REF),
        'tradingOutletName': OUTLET_NAME
    }
    logger.info('Redeeming coupon ICP5139829')
    logger.info('Headers: %s', headers_info)
    redeem_url = url + '/' + "ICP5139829"
    logger.info('Redeem url: %s', redeem_url)
    encoded_data = json.dumps(data).encode('utf-8', 'replace')
    logger.info('Data: %s', encoded_data)
    opener = urllib2.build_opener(urllib2.HTTPHandler)
    request = urllib2.Request(redeem_url, data=encoded_data, headers=headers_info)
    request.get_method = lambda: 'PUT'
    try:
        response = opener.open(request, timeout=timeout)
        body = json.loads(response.read())
        logger.info('Response from %s coupon request (%d, %s)', action, response.getcode(), body['redemption'])
        response.close()
    except HTTPError as error:
        logger.error('Response from %s coupon request %s', action, error)
        logger.error('Reason: %s', error.reason)
        message = error.read()
        logger.error('message: %s', message)
        raise error

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s')
    logger = logging.getLogger(__name__)
    logger.info("Starting iterations: %d", ITERATIONS)
    good = 0
    bad = 0
    for i in range(0, ITERATIONS):
        try:
            status, token = get_token()
            redeem_coupon(REDEEM_URL, token['access_token'])
            good += 1
        except URLError as e:
            bad += 1
        time.sleep(1)
    logger.info('Requests (good: %d/ bad:%d)', good, bad)
