import calendar
import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

import jwt
from appstoreserverlibrary.api_client import APIException
from appstoreserverlibrary.models.CheckTestNotificationResponse import (
    CheckTestNotificationResponse,
)
from appstoreserverlibrary.models.ConsumptionRequest import ConsumptionRequest
from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.models.ExtendRenewalDateRequest import (
    ExtendRenewalDateRequest,
)
from appstoreserverlibrary.models.ExtendRenewalDateResponse import (
    ExtendRenewalDateResponse,
)
from appstoreserverlibrary.models.HistoryResponse import HistoryResponse
from appstoreserverlibrary.models.LibraryUtility import _get_cattrs_converter
from appstoreserverlibrary.models.MassExtendRenewalDateRequest import (
    MassExtendRenewalDateRequest,
)
from appstoreserverlibrary.models.MassExtendRenewalDateResponse import (
    MassExtendRenewalDateResponse,
)
from appstoreserverlibrary.models.MassExtendRenewalDateStatusResponse import (
    MassExtendRenewalDateStatusResponse,
)
from appstoreserverlibrary.models.NotificationHistoryRequest import (
    NotificationHistoryRequest,
)
from appstoreserverlibrary.models.NotificationHistoryResponse import (
    NotificationHistoryResponse,
)
from appstoreserverlibrary.models.OrderLookupResponse import OrderLookupResponse
from appstoreserverlibrary.models.RefundHistoryResponse import RefundHistoryResponse
from appstoreserverlibrary.models.SendTestNotificationResponse import (
    SendTestNotificationResponse,
)
from appstoreserverlibrary.models.Status import Status
from appstoreserverlibrary.models.StatusResponse import StatusResponse
from appstoreserverlibrary.models.TransactionHistoryRequest import (
    TransactionHistoryRequest,
)
from appstoreserverlibrary.models.TransactionInfoResponse import TransactionInfoResponse
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from httpx import AsyncClient, Response

from .const import VERSION

T = TypeVar("T")


class AppStoreServerAPIAsyncClient:
    def __init__(
        self,
        signing_key: bytes,
        key_id: str,
        issuer_id: str,
        bundle_id: str,
        environment: Environment,
        http_client: AsyncClient | None = None,
    ):
        if environment == Environment.PRODUCTION:
            self._base_url = "https://api.storekit.itunes.apple.com"
        else:
            self._base_url = "https://api.storekit-sandbox.itunes.apple.com"
        self._signing_key = serialization.load_pem_private_key(
            signing_key, password=None, backend=default_backend()
        )
        self._key_id = key_id
        self._issuer_id = issuer_id
        self._bundle_id = bundle_id
        if http_client is None:
            http_client = AsyncClient(timeout=15)
        self._http_client = http_client

    def _generate_token(self) -> str:
        future_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        return jwt.encode(
            {
                "bid": self._bundle_id,
                "iss": self._issuer_id,
                "aud": "appstoreconnect-v1",
                "exp": calendar.timegm(future_time.timetuple()),
            },
            self._signing_key,  # type: ignore
            algorithm="ES256",
            headers={"kid": self._key_id},
        )

    async def _make_request(
        self,
        path: str,
        method: str,
        queryParameters: Dict[str, Union[str, List[str]]],
        body,
        destination_class: Type[T],
    ) -> T:
        url = self._base_url + path
        c = _get_cattrs_converter(type(body)) if body is not None else None
        json: dict[str, Any] | None = c.unstructure(body) if body is not None else None  # type: ignore
        headers = {
            "User-Agent": f"aio-app-store-server-library/python/{VERSION}",
            "Authorization": "Bearer " + self._generate_token(),
            "Accept": "application/json",
        }

        response = await self._execute_request(
            method, url, queryParameters, headers, json
        )  # type: ignore
        if response.status_code >= 200 and response.status_code < 300:
            if destination_class is None:
                return
            c = _get_cattrs_converter(destination_class)
            response_body = response.json()
            return c.structure(response_body, destination_class)
        else:
            # Best effort parsing of the response body
            if (
                "content-type" not in response.headers
                or response.headers["content-type"] != "application/json"
            ):
                raise APIException(response.status_code)
            try:
                response_body = response.json()
                raise APIException(
                    response.status_code,
                    response_body["errorCode"],
                    response_body["errorMessage"],
                )
            except APIException as e:
                raise e
            except Exception as e:
                raise APIException(response.status_code) from e

    async def _execute_request(
        self,
        method: str,
        url: str,
        params: Dict[str, Union[str, List[str]]],
        headers: Dict[str, str],
        json: Dict[str, Any],
    ) -> Response:
        return await self._http_client.request(
            method, url, params=params, headers=headers, json=json
        )

    async def extend_renewal_date_for_all_active_subscribers(
        self, mass_extend_renewal_date_request: MassExtendRenewalDateRequest
    ) -> MassExtendRenewalDateResponse:
        """
        Uses a subscription's product identifier to extend the renewal date for all of its eligible active subscribers.
        https://developer.apple.com/documentation/appstoreserverapi/extend_subscription_renewal_dates_for_all_active_subscribers

        :param mass_extend_renewal_date_request: The request body for extending a subscription renewal date for all of its active subscribers.
        :return: A response that indicates the server successfully received the subscription-renewal-date extension request.
        :throws APIException: If a response was returned indicating the request could not be processed
        """
        return await self._make_request(
            "/inApps/v1/subscriptions/extend/mass",
            "POST",
            {},
            mass_extend_renewal_date_request,
            MassExtendRenewalDateResponse,
        )

    async def extend_subscription_renewal_date(
        self,
        original_transaction_id: str,
        extend_renewal_date_request: ExtendRenewalDateRequest,
    ) -> ExtendRenewalDateResponse:
        """
        Extends the renewal date of a customer's active subscription using the original transaction identifier.
        https://developer.apple.com/documentation/appstoreserverapi/extend_a_subscription_renewal_date

        :param original_transaction_id:    The original transaction identifier of the subscription receiving a renewal date extension.
        :param extend_renewal_date_request: The request body containing subscription-renewal-extension data.
        :return: A response that indicates whether an individual renewal-date extension succeeded, and related details.
        :throws APIException: If a response was returned indicating the request could not be processed
        """
        return await self._make_request(
            "/inApps/v1/subscriptions/extend/" + original_transaction_id,
            "PUT",
            {},
            extend_renewal_date_request,
            ExtendRenewalDateResponse,
        )

    async def get_all_subscription_statuses(
        self, transaction_id: str, status: List[Status] = None
    ) -> StatusResponse:
        """
        Get the statuses for all of a customer's auto-renewable subscriptions in your app.
        https://developer.apple.com/documentation/appstoreserverapi/get_all_subscription_statuses

        :param transaction_id: The identifier of a transaction that belongs to the customer, and which may be an original transaction identifier.
        :param status: An optional filter that indicates the status of subscriptions to include in the response. Your query may specify more than one status query parameter.
        :return: A response that contains status information for all of a customer's auto-renewable subscriptions in your app.
        :throws APIException: If a response was returned indicating the request could not be processed
        """
        queryParameters: Dict[str, List[str]] = dict()
        if status is not None:
            queryParameters["status"] = [str(s.value) for s in status]

        return await self._make_request(
            "/inApps/v1/subscriptions/" + transaction_id,
            "GET",
            queryParameters,
            None,
            StatusResponse,
        )

    async def get_refund_history(
        self, transaction_id: str, revision: str
    ) -> RefundHistoryResponse:
        """
        Get a paginated list of all of a customer's refunded in-app purchases for your app.
        https://developer.apple.com/documentation/appstoreserverapi/get_refund_history

        :param transaction_id: The identifier of a transaction that belongs to the customer, and which may be an original transaction identifier.
        :param revision:              A token you provide to get the next set of up to 20 transactions. All responses include a revision token. Use the revision token from the previous RefundHistoryResponse.
        :return: A response that contains status information for all of a customer's auto-renewable subscriptions in your app.
        :throws APIException: If a response was returned indicating the request could not be processed
        """

        queryParameters: Dict[str, List[str]] = dict()
        if revision is not None:
            queryParameters["revision"] = [revision]

        return await self._make_request(
            "/inApps/v2/refund/lookup/" + transaction_id,
            "GET",
            queryParameters,
            None,
            RefundHistoryResponse,
        )

    async def get_status_of_subscription_renewal_date_extensions(
        self, request_identifier: str, product_id: str
    ) -> MassExtendRenewalDateStatusResponse:
        """
        Checks whether a renewal date extension request completed, and provides the final count of successful or failed extensions.
        https://developer.apple.com/documentation/appstoreserverapi/get_status_of_subscription_renewal_date_extensions

        :param request_identifier: The UUID that represents your request to the Extend Subscription Renewal Dates for All Active Subscribers endpoint.
        :param product_id:         The product identifier of the auto-renewable subscription that you request a renewal-date extension for.
        :return: A response that indicates the current status of a request to extend the subscription renewal date to all eligible subscribers.
        :throws APIException: If a response was returned indicating the request could not be processed
        """
        return await self._make_request(
            "/inApps/v1/subscriptions/extend/mass/"
            + product_id
            + "/"
            + request_identifier,
            "GET",
            {},
            None,
            MassExtendRenewalDateStatusResponse,
        )

    async def get_test_notification_status(
        self, test_notification_token: str
    ) -> CheckTestNotificationResponse:
        """
        Check the status of the test App Store server notification sent to your server.
        https://developer.apple.com/documentation/appstoreserverapi/get_test_notification_status

        :param test_notification_token: The test notification token received from the Request a Test Notification endpoint
        :return: A response that contains the contents of the test notification sent by the App Store server and the result from your server.
        :throws APIException: If a response was returned indicating the request could not be processed
        """
        return await self._make_request(
            "/inApps/v1/notifications/test/" + test_notification_token,
            "GET",
            {},
            None,
            CheckTestNotificationResponse,
        )

    async def get_notification_history(
        self,
        pagination_token: str,
        notification_history_request: NotificationHistoryRequest,
    ) -> NotificationHistoryResponse:
        """
        Get a list of notifications that the App Store server attempted to send to your server.
        https://developer.apple.com/documentation/appstoreserverapi/get_notification_history

        :param pagination_token: An optional token you use to get the next set of up to 20 notification history records. All responses that have more records available include a paginationToken. Omit this parameter the first time you call this endpoint.
        :param notification_history_request: The request body that includes the start and end dates, and optional query constraints.
        :return: A response that contains the App Store Server Notifications history for your app.
        :throws APIException: If a response was returned indicating the request could not be processed
        """
        queryParameters: Dict[str, List[str]] = dict()
        if pagination_token is not None:
            queryParameters["paginationToken"] = [pagination_token]

        return await self._make_request(
            "/inApps/v1/notifications/history",
            "POST",
            queryParameters,
            notification_history_request,
            NotificationHistoryResponse,
        )

    async def get_transaction_history(
        self,
        transaction_id: str,
        revision: Optional[str],
        transaction_history_request: TransactionHistoryRequest,
    ) -> HistoryResponse:
        """
        Get a customer's in-app purchase transaction history for your app.
        https://developer.apple.com/documentation/appstoreserverapi/get_transaction_history

        :param transaction_id: The identifier of a transaction that belongs to the customer, and which may be an original transaction identifier.
        :param revision:              A token you provide to get the next set of up to 20 transactions. All responses include a revision token. Note: For requests that use the revision token, include the same query parameters from the initial request. Use the revision token from the previous HistoryResponse.
        :return: A response that contains the customer's transaction history for an app.
        :throws APIException: If a response was returned indicating the request could not be processed
        """
        queryParameters: Dict[str, List[str]] = dict()
        if revision is not None:
            queryParameters["revision"] = [revision]

        if transaction_history_request.startDate is not None:
            queryParameters["startDate"] = [str(transaction_history_request.startDate)]

        if transaction_history_request.endDate is not None:
            queryParameters["endDate"] = [str(transaction_history_request.endDate)]

        if transaction_history_request.productIds is not None:
            queryParameters["productId"] = transaction_history_request.productIds

        if transaction_history_request.productTypes is not None:
            queryParameters["productType"] = [
                product_type.value
                for product_type in transaction_history_request.productTypes
            ]

        if transaction_history_request.sort is not None:
            queryParameters["sort"] = [transaction_history_request.sort.value]

        if transaction_history_request.subscriptionGroupIdentifiers is not None:
            queryParameters[
                "subscriptionGroupIdentifier"
            ] = transaction_history_request.subscriptionGroupIdentifiers

        if transaction_history_request.inAppOwnershipType is not None:
            queryParameters["inAppOwnershipType"] = [
                transaction_history_request.inAppOwnershipType.value
            ]

        if transaction_history_request.revoked is not None:
            queryParameters["revoked"] = [str(transaction_history_request.revoked)]

        return await self._make_request(
            "/inApps/v1/history/" + transaction_id,
            "GET",
            queryParameters,
            None,
            HistoryResponse,
        )

    async def get_transaction_info(
        self, transaction_id: str
    ) -> TransactionInfoResponse:
        """
        Get information about a single transaction for your app.
        https://developer.apple.com/documentation/appstoreserverapi/get_transaction_info

        :param transaction_id The identifier of a transaction that belongs to the customer, and which may be an original transaction identifier.
        :return: A response that contains signed transaction information for a single transaction.
        :throws APIException: If a response was returned indicating the request could not be processed
        """
        return await self._make_request(
            "/inApps/v1/transactions/" + transaction_id,
            "GET",
            {},
            None,
            TransactionInfoResponse,
        )

    async def look_up_order_id(self, order_id: str) -> OrderLookupResponse:
        """
        Get a customer's in-app purchases from a receipt using the order ID.
        https://developer.apple.com/documentation/appstoreserverapi/look_up_order_id

        :param order_id: The order ID for in-app purchases that belong to the customer.
        :return: A response that includes the order lookup status and an array of signed transactions for the in-app purchases in the order.
        :throws APIException: If a response was returned indicating the request could not be processed
        """
        return await self._make_request(
            "/inApps/v1/lookup/" + order_id, "GET", {}, None, OrderLookupResponse
        )

    async def request_test_notification(self) -> SendTestNotificationResponse:
        """
        Ask App Store Server Notifications to send a test notification to your server.
        https://developer.apple.com/documentation/appstoreserverapi/request_a_test_notification

        :return: A response that contains the test notification token.
        :throws APIException: If a response was returned indicating the request could not be processed
        """
        return await self._make_request(
            "/inApps/v1/notifications/test",
            "POST",
            {},
            None,
            SendTestNotificationResponse,
        )

    async def send_consumption_data(
        self, transaction_id: str, consumption_request: ConsumptionRequest
    ):
        """
        Send consumption information about a consumable in-app purchase to the App Store after your server receives a consumption request notification.
        https://developer.apple.com/documentation/appstoreserverapi/send_consumption_information

        :param transaction_id: The transaction identifier for which you're providing consumption information. You receive this identifier in the CONSUMPTION_REQUEST notification the App Store sends to your server.
        :param consumption_request:    The request body containing consumption information.
        :raises APIException: If a response was returned indicating the request could not be processed
        """
        await self._make_request(
            "/inApps/v1/transactions/consumption/" + transaction_id,
            "PUT",
            {},
            consumption_request,
            None,
        )
