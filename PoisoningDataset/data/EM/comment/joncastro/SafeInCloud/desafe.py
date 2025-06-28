"""Desafe for Safe In Cloud (safe-in-cloud.com).
A python utility to decrypt Safe In Cloud databases files

Usage:
  desafe card <file> [<filter>...] [-p] [-r] [-d]
  desafe label <file>
  desafe export <file> (json|xml) [<output-file>]
  desafe (-h | --help)

self.args:
  card    Print cards
  label   Print labels
  export  Exports given file in clear in the given format (json or xml).
  file    Safe in Cloud database file path
  filter  optional words to filter entries

Options:
  -p --password     Print passwords.
  -r --raw          Print information keeping the original format.
  -d --deleted      Included deleted items.
  -h --help         Show this screen.
  -v --version      Show version.
"""
