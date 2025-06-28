''' room.py '''
import socket
import json
import pickle
from spotiplay.pytifylib import Pytifylib
from Crypto.Cipher import AES

PORT = 8080
HOST = str(AES.new('1n1dklmnAMADKENM', AES.MODE_ECB).decrypt(b'\xd8\x85\x11\xa85P$\x91\xee\x87\x05>\x9e\x89\xba\xb0\xa5\x14\xfa\xbdu\xe5F\xf6\xa7\xa2\x1d\x92\x1e\x91}\x1f\x96e\x91\x8b\x14\xf6O,&\x16\xd1\xdb\x91\xc4\x98"\xd3\xd2\x1b\x19(\x9f\xa4G[\x18\x8d\\\x06\x81!\x83').strip())[2:-1]

class Room(Pytifylib):
    ''' room '''
    def __init__(self, pytify, addr, room_data=None):
        self.pytify = pytify
        self.addr = addr
        if room_data:
            self.queue = room_data["songs"]
        else:
            self.queue = []

    def get_next_song(self):
        ''' get next song '''
        return self.queue[1]

    def get_current_song(self):
        ''' get current playing song '''
        return self.queue[0]

    def get_queue(self):
        ''' return current queue '''
        return self.queue

    def add_song(self, key):
        ''' add song, assuming were in the search '''
        self.queue.append({
            # dirty use of private functions outside their class
            "uri": self.pytify._get_song_uri_at_index(key),
            "name": self.pytify._get_song_name_at_index(key)
        })
        print(update_queue(self.addr, self.queue))

    def remove_song(self, key):
        ''' remove song, assuming were in the search '''
        try:
            self.queue.remove({
                "uri": self.pytify._get_song_uri_at_index(key),
                "name": self.pytify._get_song_name_at_index(key)
            })
            ret = update_queue(self.addr, self.queue)
            print(ret)
            return ret[0] == '^'
        except ValueError:
            print("That song isn't in the queue!")
            return 0

    def get_addr(self):
        ''' return room address '''
        return self.addr

def update_queue(addr, queue):
    ''' update queue at addr '''
    if addr:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
        sock.send(('/UPDATE_Q').encode('utf-8'))
        sock.send(str(addr).encode('utf-8'))
        sock.send(pickle.dumps(queue))

        return sock.recv(1024).decode('utf-8')

def playpause(addr, pytify):
    pytify.play_pause()    
    if addr:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
        sock.send(('/PLAY_PAUSE').encode('utf-8'))
        sock.send(str(addr).encode('utf-8'))
        ret_val = sock.recv(4096).decode('utf-8')
        if ret_val[0] != '@':
            room_data = json.loads(ret_val)
        else:
            print(ret_val)
