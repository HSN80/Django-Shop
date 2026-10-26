"""Client for the Zibal payment gateway (https://gateway.zibal.ir)."""
import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

OK_RESULT = 100          # request accepted / payment verified
ALREADY_VERIFIED = 201   # verify was already called for this payment


class GatewayError(Exception):
    """Raised when the gateway cannot be reached or rejects a request."""


def to_gateway_mobile(phone):
    """Convert ``+989123456789`` to the ``09123456789`` form the gateway expects.

    Returns an empty string if the number is not an Iranian mobile number.
    """
    match = re.fullmatch(r'\+98(9\d{9})', str(phone))
    return f'0{match.group(1)}' if match else ''


class ZibalGateway:
    """Thin wrapper around the Zibal ``request`` and ``verify`` endpoints.

    The merchant code comes from ``settings.ZIBAL_MERCHANT``; the value
    ``"zibal"`` selects the sandbox. Amounts are in Rials.
    """

    API = 'https://gateway.zibal.ir/v1/'
    START = 'https://gateway.zibal.ir/start/'
    TIMEOUT = 10  # seconds

    def __init__(self, merchant=None):
        self.merchant = merchant or settings.ZIBAL_MERCHANT

    def _post(self, path, payload):
        try:
            response = requests.post(self.API + path, json=payload, timeout=self.TIMEOUT)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.exception('Zibal %s call failed', path)
            raise GatewayError('ارتباط با درگاه پرداخت برقرار نشد. لطفاً دوباره تلاش کنید.') from exc

    def request(self, amount, order_id, callback_url, mobile='', description=''):
        """Create a payment and return its ``trackId``.

        Raises:
            GatewayError: If the gateway is unreachable or does not accept the request.
        """
        payload = {
            'merchant': self.merchant,
            'amount': amount,
            'callbackUrl': callback_url,
            'orderId': str(order_id),
            'description': description,
        }
        if mobile:
            payload['mobile'] = mobile

        data = self._post('request', payload)
        if data.get('result') != OK_RESULT or not data.get('trackId'):
            logger.error('Zibal rejected the request: %s', data)
            raise GatewayError(data.get('message') or 'درخواست پرداخت پذیرفته نشد.')
        return data['trackId']

    def start_url(self, track_id):
        """Return the gateway page the customer must be sent to."""
        return f'{self.START}{track_id}'

    def verify(self, track_id):
        """Ask the gateway for the final state of a payment and return its raw reply."""
        return self._post('verify', {'merchant': self.merchant, 'trackId': track_id})