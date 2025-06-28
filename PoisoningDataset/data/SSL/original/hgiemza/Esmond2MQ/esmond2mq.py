#!/usr/bin/env python
"""
Module to publish perfSonar measurements as messages
"""

import logging
import time
import sys
import ssl
import threading
import Queue
import ConfigParser
import requests
import json
import stomp

from messaging.message import Message
from messaging.stomppy import MessageListener

class Esmond2MQ(object):
    """
    Class to publish measurements, stored in esmond archive, in message queues
    """
    
    # consts & defaults
    MAX_THREADS = 10                # number of worker threads
    FETCH_METADATA_TIME = 20        # how often new metadata (events) should be fetched from esmond
    RAW_DATA_TIME_RANGE = 1200      # time range set during the fetch of raw data (in seconds)
    GET_TIMEOUT = 40                # timeout set during GET requests (esmond)
    QUEUE_TIMEOUT = 3               # timeout while inserting/removing objects from internal queues
    QUEUE_LENGTH = 100000           # length of the pre/post-processing queues
    EVENT_TYPES = [                 # supported events
                    'packet-loss-rate',
                    'packet-count-sent',
                    'packet-count-lost',
                    'packet-trace',
                    'throughput',
                    'histogram-owdelay'
                  ]
    
    def __init__(self, config_file='./esmond2mq.conf'):
        """
        Initialises esmond publisher.
        
        Parameter:
            config_file - path to the configuration file
        """
        
        # internal logger
        self.log = logging.getLogger(__name__ + self.__class__.__name__)
        
        # read parameters from the config file
        self.__readConfiguration(config_file)
        
        # queues for preprocessed (meta) and postprocessed (meta + raw) objects
        self.__preprocessing_queue = Queue.Queue(self.QUEUE_LENGTH)
        self.__postprocessing_queue = Queue.Queue(self.QUEUE_LENGTH)
        
        # threads
        self.__threads = []                     # list of worker threads
        self.__prepare_events_thread = None     # thread that fetches metadata and splits it to events
        self.__send_messages_thread = None      # thread that sends messages to MQ
        
        # object status
        self.__stopped = True
        self.__start_time = time.time()
        self.__summary_count = 0
        
        # dummy connection
        self.__connection = stomp.Connection()
        
        # profiling
        self.__profiling_lock = threading.Lock()
        
        self.metadata_count = 0
        self.events_count = dict(zip(self.EVENT_TYPES, len(self.EVENT_TYPES)*[0]))
        self.empty_events_count = dict(zip(self.EVENT_TYPES, len(self.EVENT_TYPES)*[0]))
        self.messages_count = dict(zip(self.EVENT_TYPES, len(self.EVENT_TYPES)*[0]))
        
        self.getraw_time = 0.001    # div/0 protection
        self.getmeta_time = 0.001
            
    def __readConfiguration(self, path):
        """
        Read configuration file and set internal variables.
        """
        
        self.log.info('Reading the configuration file: %s' % path)
        try:
            parser = ConfigParser.RawConfigParser()
            parser.read(path)
            
            # message queue parameters
            broker = parser.get('main', 'MQBroker').split(":")
            self.__broker = {'host': broker[0], 'port': int(broker[1])}
            self.__ssl = {'key_file': parser.get('main', 'SSLKeyFile'), 'cert_file': parser.get('main', 'SSLCertFile')}
            
            # esmond parameters
            self.__esmond_url = parser.get('main', 'EsmondURL')

            # internal parameters (use defaults when not supplied)
            try:
                self.MAX_THREADS = int(parser.get('main', 'NbWorkers'))
            except (ConfigParser.NoOptionError, ValueError):
                self.log.warn("Number of worker threads set to the default value: %d" % self.MAX_THREADS)

            try:
                self.RAW_DATA_TIME_RANGE = int(parser.get('main', 'RDTimeRange'))
            except (ConfigParser.NoOptionError, ValueError):
                self.log.warn("Time range during the fetch of raw data set to the default value: %d min" % self.RAW_DATA_TIME_RANGE)
            
            # debug
            self.log.debug("Broker: %s:%s" % (self.__broker['host'], self.__broker['port']))
            self.log.debug("SSL certificate: %s" % self.__ssl['cert_file'])
            self.log.debug("SSL key file:    %s" % self.__ssl['key_file'])
            self.log.debug("Esmond base url: %s" % self.__esmond_url)
            self.log.debug("Time range (raw data): %s" % self.RAW_DATA_TIME_RANGE)
            self.log.debug("Number of worker threads: %d" % self.MAX_THREADS)
            
        except ConfigParser.Error as e:
            self.log.error("Coud not read the configuration file.")
            raise # stop the execution of the program
            
    def __connectToBroker(self):
        """
        Creates and starts a connection required to communicate with a message queue broker.
        
        Exception:
            stomp.exception.ConnectFailedException - forwarded from stomp::Connection::connect
        """
        
        self.__connection = stomp.Connection([(self.__broker['host'], self.__broker['port'])],
                                             use_ssl=True,
                                             ssl_version = ssl.PROTOCOL_TLSv1,
                                             ssl_key_file=self.__ssl['key_file'],
                                             ssl_cert_file=self.__ssl['cert_file'],
                                             reconnect_sleep_initial = 10,
                                             reconnect_attempts_max = 1
                                           )
        
        self.log.info("Setting the debug listener.")
        self.__connection.set_listener("", DebugListener())
        
        self.log.info("Starting the connection.")
        self.__connection.start()
        
        self.log.info("Connecting to a broker.")
        self.__connection.connect()
        
        self.log.info("Subscribing topics.")
        for type in self.EVENT_TYPES:
            self.__connection.subscribe(destination='/topic/perfsonar.' + type, ack='auto')
        
    def __sendRequest(self, url):
        """
        Send a GET request to Esmond and convert answer (JSON) to a list.
        
        Parameters:
            url - full url (starting with 'http://') pointing to data in the archive
        
        Returns:
            A list of measurements (empty list in case of an exception).
        """
        
        start_time = time.time()
        result = []
        try:
            self.log.debug("GET " + url)
            answer = requests.get(url, timeout = self.GET_TIMEOUT)
            result = json.loads(answer.text)
            
        # in case of an exception log the event and go on
        except requests.exceptions.Timeout:
            self.log.error("Timeout!")
        except (requests.exceptions.RequestException, ValueError):
            self.log.error("An error occured while retreiving data from Esmond!")
        else:
            self.log.debug("Response: %d bytes, %f sec" % (len(answer.text), time.time() - start_time))
        
        return result
        
    def __prepareEvents(self):
        """
        Fetch metadata key (not often that every self.FETCH_METADATA_TIME seconds),
        filter out relevant events and put data requred of further processing 
        in the preprocessing queue.
        """
        
        # set initial start time
        start_time = time.time() - 1
        
        while not self.__stopped:
            
            # time needed to determine how long to wait after fetching the data
            current_time = time.time()
            
            # set the end time of data to fetch to now - 1s
            end_time = time.time() - 1
            self.log.debug("Setting the end time of metadata keys to fetch: %d" % end_time)
            
            # set the output format, increase the limit and limit the events using time
            filter = '?format=json&limit=10000&time-start=%d&time-end=%d' % (start_time, end_time)
            
            # get metadata keys
            getmeta_start_time = time.time()
            metadata = self.__sendRequest(self.__esmond_url + '/esmond/perfsonar/archive/' + filter)
            self.log.info("Esmond returned %d metadata key(s) to process." % len(metadata))
            
            # profiling
            self.getmeta_time = self.getmeta_time + time.time() - getmeta_start_time
            self.metadata_count = self.metadata_count + len(metadata)
            
            self.log.debug("Iterating through metadata keys.")
            for measurement in metadata:
                for event in measurement["event-types"]:
                    
                    # filter out relevant events
                    event_type = event["event-type"]
                    if event_type in self.EVENT_TYPES and event["time-updated"] >= int(start_time) and event["time-updated"] <= int(end_time):
                        
                        
                        # add the object to the preprocessing queue
                        data = {'measurement': measurement, 'event': event}
                        while not self.__stopped:
                            try:
                                self.__preprocessing_queue.put(data, True, self.QUEUE_TIMEOUT)
                            except Queue.Full:
                                continue
                            else:
                                break
                        else:
                            return
                        
            # during next fetch, get metadata keys which were updated 1 second after the current end time
            start_time = end_time + 1
            self.log.debug("Setting the start time of metadata keys to fetch: %d" % start_time)
             
            # wait and check the stop condition
            while current_time + self.FETCH_METADATA_TIME - time.time() > 0 and not self.__stopped:
                time.sleep(1)
            
    def __joinMetaWithRawData(self):
        """
        Request the raw data for events stored in preprocessing queue.
        Put the result (meta + raw data) in the postprocessing queue.
        Discard metadata if raw data is empty.
        
        Function is run in parallel by worker threads.
        """
        
        while not self.__stopped:
            
            # wait for an object to process
            try:
                data = self.__preprocessing_queue.get(True, self.QUEUE_TIMEOUT)
            except Queue.Empty:
                continue
            
            # fetch raw data from the last self.RAW_DATA_TIME_RANGE seconds, 
            # narrow to the last result and join with event object
            # TODO: check correctness of this solution
            filter = '?format=json&time-range=%d' % self.RAW_DATA_TIME_RANGE
            
            start_time = time.time()
            raw_data = self.__sendRequest(self.__esmond_url + data['event']["base-uri"] + filter)
            end_time = time.time()
            
            data['event']['raw_count'] = len(raw_data)
            
            try:
                data['event']['raw'] = [raw_data.pop()]
            except IndexError:
                data['event']['raw'] = None
                self.log.warn('Empty raw data.')
                
                measurement = dict(data['measurement'])
                measurement['event-types'] = [data['event']]
                self.log.debug(measurement)
                
                continue
                
            finally:
                # profiling
                event_type = data['event']['event-type']

                self.__profiling_lock.acquire()
                self.getraw_time = self.getraw_time + end_time - start_time
                
                self.events_count[event_type] = self.events_count[event_type] + 1
                if data['event']['raw'] is None:
                    self.empty_events_count[event_type] = self.empty_events_count[event_type] + 1
                
                self.__profiling_lock.release()
            
            # put the data in the postprocessing queue
            while not self.__stopped:
                try:
                    self.__postprocessing_queue.put(data, True, self.QUEUE_TIMEOUT)
                except Queue.Full:
                    continue
                else:
                    break
            
    def __sendMessages(self):
        """
        Prepare and send messages created from objects in postprocessing queue (meta + raw data).
        """
        
        while not self.__stopped:
            
            # wait for an object to process
            try:
                data = self.__postprocessing_queue.get(True, self.QUEUE_TIMEOUT)
            except Queue.Empty:
                continue
            
            # prepare and send messages
            event_type = data['event']['event-type']
            
            message = Message(
                                body = json.dumps(data['event']),
                                header = {
                                            'destination': '/topic/perfsonar.' + event_type,
                                            'time': "%s" % time.time(),
                                            'source_host': data['measurement']['source'],
                                            'destination_host': data['measurement']['destination']
                                         }
                             )
            
            # send the message
            while not self.__stopped:
                
                self.log.debug("Sending message: %s" % message.header)
                try:
                    self.__connection.send(message.body, **message.header)
                except stomp.exception.NotConnectedException:
                    self.log.warn("Could not send a message. Trying to reconnect...")
                    
                    # wait until new connection is established
                    while not self.__stopped:
                        try:
                            self.__connectToBroker()
                        except stomp.exception.ConnectFailedException:
                            self.log.error("Failed to reconnect.")
                        else:
                            break
                
                # message was succesfully sent - break the loop
                else:
                    break
            
            # profiling
            self.messages_count[event_type] = self.messages_count[event_type] + 1
            
    def startPublishing(self):
        
        self.log.info('Starting Esmond publisher.')
        
        self.__stopped = False
        
        # create thread that prepares splits metdata to separate events (additional processing needed)
        self.__prepare_events_thread = threading.Thread(target=self.__prepareEvents, name='PrepareEvents')
        self.__prepare_events_thread.setDaemon(True)
        self.__prepare_events_thread.start()
        
        # create worker threads to fetch raw data
        for i in range(self.MAX_THREADS):
            t = threading.Thread(target=self.__joinMetaWithRawData, name='Worker %d' % i)
            t.setDaemon(True)
            t.start()
            self.__threads.append(t)
        
        # start a thread that prepares and sends messages to the message queue
        self.__send_messages_thread = threading.Thread(target=self.__sendMessages, name='SendMessages')
        self.__send_messages_thread.setDaemon(True)
        self.__send_messages_thread.start()
        
    def stopPublishing(self):
        """
        Join all threads and stop message publishing.
        """
        
        self.log.info('Stopping Esmond publisher.')
        
        # set internal status
        self.__stopped = True
        
        # wait for the thread that prepares events
        self.__prepare_events_thread.join()
        
        # wait until all worker threads finish
        for thread in self.__threads:
            thread.join()
        
        # wait for the thread that sends messages
        self.__send_messages_thread.join()
        
    def printSummary(self):
        """Print summary of publisher activity."""
        
        self.__summary_count = self.__summary_count + 1
        events_sum = sum(self.events_count.values())
        empty_events_sum = sum(self.empty_events_count.values())
        messages_sum = sum(self.messages_count.values())
        run_time = time.time() - self.__start_time
        
        if events_sum == 0:
            empty_ratio = 0
        else:
            empty_ratio = empty_events_sum / float(events_sum) * 100
        
        self.log.debug("Printing summary %d" % self.__summary_count)
        print "\n----SUMMARY %d----" % self.__summary_count
        
        # div/0 protection
        if self.metadata_count <> 0:
            print "Fetch metadata: %d sec, avg. %f sec/entry" % (self.getmeta_time, self.getmeta_time/self.metadata_count)
        if events_sum <> 0:
            print "Fetch raw data: %d sec, avg. %f sec/event, %d threads" % (self.getraw_time, self.getraw_time/events_sum, len(self.__threads))
        
        print "\nMetadata processed: %d (avg. %f entries/sec)" % (self.metadata_count, self.metadata_count/run_time)
        print "Events processed: %d (avg. %f events/sec)" % (events_sum, events_sum/run_time)
        print " Types: %s" % self.events_count
        
        print "\nQueues:"
        print " Preprocessing:  %d" % self.__preprocessing_queue.qsize()
        print " Postprocessing: %d" % self.__postprocessing_queue.qsize()
        
        print "\nMessages sent: %d" % messages_sum
        print " Types: %s" % self.messages_count
        
        print "\nEmpty raw data (total): %.0f%% (%d/%d)" % (empty_ratio, empty_events_sum, events_sum)
        for event_type, count in self.events_count.items():
            if count > 0:
                empty_count = self.empty_events_count[event_type]
                print " %s: %.0f%% (%d/%d)" % (event_type, empty_count/float(count) * 100, empty_count, count)
        
        print "Run time: %ds" % run_time
        print "---------------"
        sys.stdout.flush()


class DebugListener(MessageListener):
    
    def __init__(self):
        self.log = logging.getLogger(__name__ + self.__class__.__name__)
    
    def error(self, message):
        self.log.error("Error %s" % message)
    
    def message(self, message):
        self.log.debug("""New message:
=====================================HEADER====================================
%s, %s, %s (src), %s (dst)
======================================BODY=====================================
%s""" %
                            (
                             message.header.get("destination"), \
                             message.header.get("time"), \
                             message.header.get("source_host"), \
                             message.header.get("destination_host"), \
                             message.get_body()
                            )
                           )


 
if __name__ == "__main__":
    
    # logging
    format = '%(asctime)s, %(module)s(%(threadName)s), %(levelname)s: %(message)s'
    logging.basicConfig(format=format)
    logging.getLogger(__name__ + "Esmond2MQ").setLevel(logging.INFO)
    logging.getLogger(__name__ + "DebugListener").setLevel(logging.ERROR)
    
    # create test instance and start publishing
    esmond_publisher = Esmond2MQ()
    esmond_publisher.startPublishing()
    
    # wait for Ctrl-C or sys.exit() and printing summary every 10 seconds
    try:
        while True:
            if int(time.time())%10 == 0:
                esmond_publisher.printSummary()
            time.sleep(1)
        
    except (KeyboardInterrupt, SystemExit):
        print "Interrupt signal detected."
        
    # stop publishing and print the last summary
    finally:
        try:
            print "Trying to shutdown gracefully... (press Ctrl-C to shutdown forcibly)"
            esmond_publisher.stopPublishing()
            esmond_publisher.printSummary()
        except KeyboardInterrupt:
            print "Killed forcibly!"
