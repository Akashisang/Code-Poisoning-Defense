
#
#  This class is responsible for:
#    - reading in the raw packet data from the /dev/eeg/encrypted device
#    - decrypting the signal (two 16-byte packets, ECB mode AES)
#    - queuing the decoded packets for buffer pull requests
#    - forwarding the packets to registered subscribers
#    - passing the packets to the EmotivDevice for updating
#
