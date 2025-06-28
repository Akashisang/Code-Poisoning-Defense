import json
import threading
import ssl
import queue

import asyncio
from nats.aio.client import Client as NatsClient
from nats.aio import errors as nats_errors

from wysteria.middleware.abstract_middleware import WysteriaConnectionBase
from wysteria import constants as consts
from wysteria import domain
from wysteria import errors


_DEFAULT_URI = "nats://localhost:4222"  # default localhost, nats port
_CLIENT_ROUTE = "w.client.%s"  # From a client

# wysteria nats protocol routes
_KEY_CREATE_COLLECTION = _CLIENT_ROUTE % "cc"
_KEY_CREATE_ITEM = _CLIENT_ROUTE % "ci"
_KEY_CREATE_VERSION = _CLIENT_ROUTE % "cv"
_KEY_CREATE_RESOURCE = _CLIENT_ROUTE % "cr"
_KEY_CREATE_LINK = _CLIENT_ROUTE % "cl"

_KEY_DELETE_COLLECTION = _CLIENT_ROUTE % "dc"
_KEY_DELETE_ITEM = _CLIENT_ROUTE % "di"
_KEY_DELETE_VERSION = _CLIENT_ROUTE % "dv"
_KEY_DELETE_RESOURCE = _CLIENT_ROUTE % "dr"

_KEY_FIND_COLLECTION = _CLIENT_ROUTE % "fc"
_KEY_FIND_ITEM = _CLIENT_ROUTE % "fi"
_KEY_FIND_VERSION = _CLIENT_ROUTE % "fv"
_KEY_FIND_RESOURCE = _CLIENT_ROUTE % "fr"
_KEY_FIND_LINK = _CLIENT_ROUTE % "fl"

_KEY_GET_PUBLISHED = _CLIENT_ROUTE % "gp"
_KEY_SET_PUBLISHED = _CLIENT_ROUTE % "sp"

_KEY_UPDATE_COLLECTION = _CLIENT_ROUTE % "uc"
_KEY_UPDATE_ITEM = _CLIENT_ROUTE % "ui"
_KEY_UPDATE_VERSION = _CLIENT_ROUTE % "uv"
_KEY_UPDATE_RESOURCE = _CLIENT_ROUTE % "ur"
_KEY_UPDATE_LINK = _CLIENT_ROUTE % "ul"


NATS_MSG_RETRIES = 3
_NATS_MIN_TIMEOUT = 2  # seconds, chosen by experimentation


def _load_ssl_context(key, cert, verify=False):
    """Util func to load an ssl context.

    Args:
        key (str): path to file
        cert (str): path to file
        verify (bool): if true, we'll verify the server's certs

    Returns:
        ssl_context
    """
    purpose = ssl.Purpose.SERVER_AUTH if verify else ssl.Purpose.CLIENT_AUTH
    tls = ssl.create_default_context(purpose=purpose)
    tls.protocol = ssl.PROTOCOL_TLSv1_2
    tls.load_cert_chain(certfile=cert, keyfile=key)
    return tls


def _retry(func):
    """Simple wrapper func that retries the given func some number of times
    on any exception(s).

    Warning: Care should be taken to use this on idempotent functions only

    Args:
        func:

    Returns:
        ?
    """
    def retry_func(*args, **kwargs):
        for count in range(0, NATS_MSG_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except (errors.RequestTimeoutError, queue.Empty):
                if count >= NATS_MSG_RETRIES:
                    raise
    return retry_func


class _AsyncIONats(threading.Thread):
    """Tiny class to handle queuing requests through asyncio.

    Essentially, a wrapper class around the Nats.IO asyncio implementation to provide us with
    the functionality we're after. This makes for a much nicer interface to work with than
    the incredibly annoying & ugly examples https://github.com/nats-io/asyncio-nats .. ewww.
    """

    _MAX_RECONNECTS = 10

    def __init__(self, url, tls):
        threading.Thread.__init__(self)
        self._conn = None
        self._outgoing = queue.Queue()  # outbound messages added in request()
        self._running = False

        self.opts = {  # opts to pass to Nats.io client
            "servers": [url],
            "allow_reconnect": True,
            "max_reconnect_attempts": self._MAX_RECONNECTS,
        }

        if tls:
            self.opts["tls"] = tls

    @asyncio.coroutine
    def main(self, loop):
        """Connect to remote host(s)

        Raises:
            NoServersError
        """
        # explicitly set the asyncio event loop so it can't get confused ..
        asyncio.set_event_loop(loop)

        self._conn = NatsClient()

        try:
            yield from self._conn.connect(io_loop=loop, **self.opts)
        except nats_errors.ErrNoServers as e:
            # Could not connect to any server in the cluster.
            raise errors.NoServersError(e)

        while self._running:
            if self._outgoing.empty():
                # No one wants to send a message
                continue

            if not self._conn.is_connected:
                # give nats more time to (re)connect
                continue

            reply_queue, key, data = self._outgoing.get_nowait()  # pull request from queue
            if reply_queue is None:
                # we're passed None only when we're supposed to exit. See stop()
                break

            try:
                result = yield from self._conn.request(key, bytes(data, encoding="utf8"))
                reply_queue.put_nowait(result.data.decode())
            except nats_errors.ErrConnectionClosed as e:
                reply_queue.put_nowait(errors.ConnectionClosedError(e))
            except (nats_errors.ErrTimeout, queue.Empty) as e:
                reply_queue.put_nowait(errors.RequestTimeoutError(e))
            except Exception as e:  # pass all errors up to the caller
                reply_queue.put_nowait(e)

        yield from self._conn.close()

    def request(self, data: dict, key: str, timeout: int=5) -> dict:
        """Send a request to the server & await the reply.

        Args:
            data: data to send
            key: the key (subject) to send the message to
            timeout: some time in seconds to wait before calling it quits

        Returns:
            dict

        Raises:
            RequestTimeoutError
            ConnectionClosedError
            NoServersError
        """
        q = queue.Queue(maxsize=NATS_MSG_RETRIES)  # create a queue to get a reply on
        self._outgoing.put_nowait((q, key, data))  # add our message to the outbound queue
        try:
            result = q.get(timeout=max([_NATS_MIN_TIMEOUT, timeout]))  # block for a reply
        except queue.Empty as e:  # we waited, but nothing was returned to us :(
            raise errors.RequestTimeoutError("Timeout waiting for server reply. Original %s" % e)

        if isinstance(result, Exception):
            raise result
        return result

    def stop(self):
        """Stop the service, killing open connection(s)
        """
        # set to false to kill coroutine running in main()
        self._running = False

        # interpreted as a poison pill (causes main() loop to break)
        self._outgoing.put((None, None, None))

        if not self._conn:
            return

        try:
            # flush & kill the actual connections
            self._conn.flush()
            self._conn.close()
        except Exception:
            pass

    def run(self):
        """Start the service
        """
        if self._running:
            return

        self._running = True

        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.main(loop))
        try:
            loop.close()
        except Exception:
            pass


class NatsMiddleware(WysteriaConnectionBase):
    """Wysteria middleware client using Nats.io to manage transport

    Using python nats client (copied & modified in libs/ dir)
    https://github.com/jackytu/python-nats/blob/master/nats/client.py

    """
    def __init__(self, url: str=None, tls=None):
        """Construct new client

        Url as in "nats://user:password@host:port"

        Args:
            url (str)
            tls (ssl_context)
        """
        if not url:
            url = _DEFAULT_URI

        ssl_context = None
        if tls:
            if tls.enable:
                ssl_context = _load_ssl_context(tls.key, tls.cert, verify=tls.verify)

        self._conn = _AsyncIONats(url, ssl_context)

    def connect(self):
        """Connect to remote host(s)

        Raises:
            Exception if unable to establish connection to remote host(s)
        """
        self._conn.setDaemon(True)
        self._conn.start()

    def close(self):
        """Close remote connection"""
        self._conn.stop()

    @_retry
    def _sync_idempotent_msg(self, data: dict, key: str, timeout: int=3):
        """Send an idempotent message to the server and wait for a reply.

        This will be retried on failure(s) up to NATS_MSG_RETRIES times.

        Args:
            data (dict): json data to send
            key (str): message subject
            timeout (int): seconds to wait for reply

        Returns:
            dict

        Raises:
            errors.RequestTimeoutError
        """
        return self._single_request(data, key, timeout=timeout)

    def _single_request(self, data: dict, key: str, timeout: int=5) -> int:
        """

        Args:
            data: dict
            key: str (subject key)
            timeout: time in seconds to wait before erroring

        Returns:
            dict
        """
        if not isinstance(data, str):
            data = json.dumps(data)

        reply = self._conn.request(data, key, timeout=timeout)
        return json.loads(reply)

    def _generic_find(self, query: list, key: str, limit: int, offset: int):
        """Send a find query to the server, return results (if any)

        Args:
            query ([domain.QueryDesc]):
            key (str):
            limit (int):
            offset (int):

        Returns:
            []dict

        Raises:
            Exception on server err
        """
        data = {
            "query": [q.encode() for q in query if q.is_valid],
            "limit": limit,
            "offset": offset,
        }

        reply = self._sync_idempotent_msg(data, key)

        err_msg = reply.get("Error")
        if err_msg:  # wysteria replied with an err, we should raise it
            raise Exception(err_msg)

        # the server replies with UpperCase strings, but we want to python-ise to lowercase
        return [{k.lower(): v for k, v in result.items()} for result in reply.get("All", [])]

    def find_collections(self, query: list, limit: int=consts.DEFAULT_QUERY_LIMIT, offset: int=0):
        """Query server & return type appropriate matching results

        Args:
            query ([]domain.QueryDesc): search query(ies) to execute
            limit (int): limit number of returned results
            offset (int): return results starting from some offset

        Returns:
            []domain.Collection

        Raises:
            Exception on network / server error
        """
        return [
            domain.Collection(self, **c) for c in self._generic_find(
                query, _KEY_FIND_COLLECTION, limit, offset
            )
        ]

    def find_items(self, query: list, limit: int=consts.DEFAULT_QUERY_LIMIT, offset: int=0):
        """Query server & return type appropriate matching results

        Args:
            query ([]domain.QueryDesc): search query(ies) to execute
            limit (int): limit number of returned results
            offset (int): return results starting from some offset

        Returns:
            []domain.Item

        Raises:
            Exception on network / server error
        """
        return [
            domain.Item(self, **c) for c in self._generic_find(
                query, _KEY_FIND_ITEM, limit, offset
            )
        ]

    def find_versions(self, query: list, limit: int=consts.DEFAULT_QUERY_LIMIT, offset: int=0):
        """Query server & return type appropriate matching results

        Args:
            query ([]domain.QueryDesc): search query(ies) to execute
            limit (int): limit number of returned results
            offset (int): return results starting from some offset

        Returns:
            []domain.Version

        Raises:
            Exception on network / server error
        """
        return [
            domain.Version(self, **c) for c in self._generic_find(
                query, _KEY_FIND_VERSION, limit, offset
            )
        ]

    def find_resources(self, query: list, limit: int=consts.DEFAULT_QUERY_LIMIT, offset: int=0):
        """Query server & return type appropriate matching results

        Args:
            query ([]domain.QueryDesc): search query(ies) to execute
            limit (int): limit number of returned results
            offset (int): return results starting from some offset

        Returns:
            []domain.Resource

        Raises:
            Exception on network / server error
        """
        return [
            domain.Resource(self, **c) for c in self._generic_find(
                query, _KEY_FIND_RESOURCE, limit, offset
            )
        ]

    def find_links(self, query: list, limit: int=consts.DEFAULT_QUERY_LIMIT, offset: int=0):
        """Query server & return type appropriate matching results

        Args:
            query ([]domain.QueryDesc): search query(ies) to execute
            limit (int): limit number of returned results
            offset (int): return results starting from some offset

        Returns:
            []domain.Link

        Raises:
            Exception on network / server error
        """
        return [
            domain.Link(self, **c) for c in self._generic_find(
                query, _KEY_FIND_LINK, limit, offset
            )
        ]

    def get_published_version(self, oid: str):
        """Item ID to find published version for

        Args:
            oid (str): item id to find published version for

        Returns:
            wysteria.domain.Version or None

        Raises:
            Exception on network / server error
        """
        reply = self._sync_idempotent_msg(
            {"id": oid}, _KEY_GET_PUBLISHED
        )

        err_msg = reply.get("Error")
        if err_msg:
            raise Exception(err_msg)

        data = reply.get("Version", None)
        if not data:
            return None

        # the server replies with UpperCase keys, we want to pythonize to lowercase
        return domain.Version(self, **{k.lower(): v for k, v in data.items()})

    def publish_version(self, oid: str):
        """Version ID mark as published

        Args:
            oid (str): version id to publish

        Raises:
            Exception on network / server error
        """
        reply = self._sync_idempotent_msg(
            {"id": oid}, _KEY_SET_PUBLISHED
        )

        err_msg = reply.get("Error")
        if err_msg:
            raise Exception(err_msg)

    def _sync_update_facets_msg(self, oid: str, facets: dict, key: str, find_func):
        """Specific call to update the facets on an object matching the given `oid`

        Args:
            oid (str):
            facets (dict):
            key (str):
            find_func (func): function (str, str) -> []Version or []Item

        Raises:
            RequestTimeoutError
            ? Exception on network / server error
        """
        data = json.dumps({
            "id": oid,
            "facets": facets,
        })
        find_self = [domain.QueryDesc().id(oid)]

        reply = {}
        for count in range(0, NATS_MSG_RETRIES + 1):
            # Fire the update request to wysteria
            try:
                reply = self._single_request(data, key)
                break  # if nothing goes wrong, we break out of the loop
            except (errors.RequestTimeoutError, queue.Empty) as e:
                if count >= NATS_MSG_RETRIES:
                    raise

            # We sent an Update and it broke, let's not retry unless our
            # change *didn't* go through
            retry = False
            matching_wysteria_objects = find_func(find_self)
            if not matching_wysteria_objects:
                break  # the obj has been deleted / id invalid? Let's break

            # Check if the keys we want to set are set already
            matching_obj = matching_wysteria_objects[0]
            for key, value in facets.items():
                if matching_obj.facets.get(key, "") != str(value):
                    retry = True
                    break

            # if all our desired facets are now set, then we can break out
            if not retry:
                break

        err_msg = reply.get("Error")
        if err_msg:
            raise Exception(err_msg)

    def update_version_facets(self, oid: str, facets: dict):
        """Update version with matching ID with given facets.

        This is smart enough to only retry failed updates if the given update
        didn't set the desired fields when it failed.

        It's not perfect, but should be serviceable.

        Args:
            oid (str): version ID to update
            facets (dict): new facets (these are added to existing facets)

        Raises:
            Exception on network / server error
        """
        self._sync_update_facets_msg(
            oid,
            facets,
            _KEY_UPDATE_VERSION,
            self.find_versions
        )

    def update_item_facets(self, oid: str, facets: dict):
        """Update item with matching ID with given facets

        Args:
            oid (str): item ID to update
            facets (dict): new facets (these are added to existing facets)

        Raises:
            Exception on network / server error
        """
        self._sync_update_facets_msg(
            oid,
            facets,
            _KEY_UPDATE_ITEM,
            self.find_items
        )

    def update_collection_facets(self, oid: str, facets: dict):
        """Update collection with matching ID with given facets

        Args:
            oid (str): collection ID to update
            facets (dict): new facets (these are added to existing facets)

        Raises:
            Exception on network / server error
        """
        self._sync_update_facets_msg(
            oid,
            facets,
            _KEY_UPDATE_COLLECTION,
            self.find_collections
        )

    def update_resource_facets(self, oid: str, facets: dict):
        """Update resource with matching ID with given facets

        Args:
            oid (str): resource ID to update
            facets (dict): new facets (these are added to existing facets)

        Raises:
            Exception on network / server error
        """
        self._sync_update_facets_msg(
            oid,
            facets,
            _KEY_UPDATE_RESOURCE,
            self.find_resources
        )

    def update_link_facets(self, oid: str, facets: dict):
        """Update link with matching ID with given facets

        Args:
            oid (str): link ID to update
            facets (dict): new facets (these are added to existing facets)

        Raises:
            Exception on network / server error
        """
        self._sync_update_facets_msg(
            oid,
            facets,
            _KEY_UPDATE_LINK,
            self.find_links
        )

    def _generic_create(
        self, request_data: dict, find_query: list, key: str, find_func, timeout: int=3
    ):
        """Creation requests for
         - collection
         - item
         - resource
         - link

        Are similar enough that we can refactor their create funcs into one.
        Versions however, are a different animal.

        Args:
            request_data (dict): json data to send as creation request
            find_query ([]domain.QueryDesc): query to uniquely find the obj
            key (str): nats subject to send
            find_func: function to find desired obj
            timeout (float): time to wait before retry

        Returns:
            str
        """
        reply = {}
        for count in range(0, NATS_MSG_RETRIES + 1):
            # send creation request
            try:
                reply = self._single_request(request_data, key)
                break  # if nothing went wrong, we've created it successfully
            except (errors.RequestTimeoutError, queue.Empty) as e:
                if count >= NATS_MSG_RETRIES:
                    raise

            # something went wrong, see if we created item
            results = find_func(find_query)
            if not results:
                continue  # we didn't create it, try again

            # We did create it, return the id
            return results[0].id

        err_msg = reply.get("Error")
        if err_msg:
            self.translate_server_exception(err_msg)

        return reply.get("Id")

    def create_collection(self, collection: domain.Collection):
        """Create collection with given name, return ID of new collection

        Args:
            collection (domain.Collection):

        Returns:
            str
        """
        data = json.dumps({
            "Collection": collection.encode(),
        })
        find_query = [
            domain.QueryDesc()
                .name(collection.name)
                .parent(collection.parent)
        ]
        return self._generic_create(
            data,
            find_query,
            _KEY_CREATE_COLLECTION,
            self.find_collections
        )

    def create_item(self, item: domain.Item):
        """Create item with given values, return ID of new item

        Args:
            item (wysteria.domain.Item): input item

        Returns:
            str

        Raises:
            Exception on network / server error
        """
        data = json.dumps({
            "Item": item.encode(),
        })
        find_query = [
            domain.QueryDesc()
                .item_type(item.item_type)
                .item_variant(item.variant)
                .parent(item.parent)
        ]
        return self._generic_create(
            data,
            find_query,
            _KEY_CREATE_ITEM,
            self.find_items
        )

    def create_version(self, version: domain.Version):
        """Create item with given values, return ID of new version

        Args:
            version (wysteria.domain.Version): input version

        Returns:
            str, int

        Raises:
            Exception on network / server error
        """
        # We can't uniquely identify the version we're hoping to create as the
        # server will increment the version number for us.
        # We could have the wysteria server implement a version reservation
        # scheme, but since we usually only care about the published version
        # we're just going to try again ..
        # ToDo: Consider version number reservation
        reply = self._sync_idempotent_msg(
            {
                "Version": version.encode(),
            },
            _KEY_CREATE_VERSION
        )

        err_msg = reply.get("Error")
        if err_msg:
            self.translate_server_exception(err_msg)

        return reply.get("Id"), reply.get("Version")

    def create_resource(self, resource: domain.Resource):
        """Create item with given values, return ID of new resource

        Args:
            resource (wysteria.domain.Resource): input resource

        Returns:
            str

        Raises:
            Exception on network / server error
        """
        data = json.dumps({
            "Resource": resource.encode(),
        })
        find_query = [
            domain.QueryDesc()
                .resource_type(resource.resource_type)
                .name(resource.name)
                .resource_location(resource.location)
                .parent(resource.parent)
        ]
        return self._generic_create(
            data,
            find_query,
            _KEY_CREATE_RESOURCE,
            self.find_resources
        )

    def create_link(self, link: domain.Link):
        """Create item with given values, return ID of new link

        Args:
            link (wysteria.domain.Link): input link

        Returns:
            str

        Raises:
            Exception on network / server error
        """
        data = json.dumps({
            "Link": link.encode(),
        })
        find_query = [
            domain.QueryDesc()
                .link_source(link.source)
                .link_destination(link.destination)
        ]
        return self._generic_create(
            data,
            find_query,
            _KEY_CREATE_LINK,
            self.find_links
        )

    def _generic_delete(self, oid: str, key: str):
        """Call remote delete function with given params

        Args:
            oid (str):
            key (str):

        Returns:
            None

        Raises:
            Exception on any network / server err
        """
        reply = self._sync_idempotent_msg(
            {"id": oid}, key
        )

        err_msg = reply.get("Error")
        if err_msg:
            self.translate_server_exception(err_msg)

    def delete_collection(self, oid: str):
        """Delete the matching obj type with the given id

        Args:
            oid (str): id of obj to delete

        Raises:
            Exception if deletion fails / network error
        """
        self._generic_delete(oid, _KEY_DELETE_COLLECTION)

    def delete_item(self, oid: str):
        """Delete the matching obj type with the given id

        (Links will be deleted automatically)

        Args:
            oid (str): id of obj to delete

        Raises:
            Exception if deletion fails / network error
        """
        self._generic_delete(oid, _KEY_DELETE_ITEM)

    def delete_version(self, oid: str):
        """Delete the matching obj type with the given id

        (Links will be deleted automatically)

        Args:
            oid (str): id of obj to delete

        Raises:
            Exception if deletion fails / network error
        """
        self._generic_delete(oid, _KEY_DELETE_VERSION)

    def delete_resource(self, oid: str):
        """Delete the matching obj type with the given id

        Args:
            oid (str): id of obj to delete

        Raises:
            Exception if deletion fails / network error
        """
        self._generic_delete(oid, _KEY_DELETE_RESOURCE)
