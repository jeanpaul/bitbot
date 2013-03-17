import os
import irc.bot
import time
from jsonrpc import ServiceProxy

import handlers

def read_config_file(filename):
	"""
	Read a simple '='-delimited config file.
	Raises IOError if unable to open file, or ValueError if an parse error
	occurs.
	Taken from bitcoinrpc library
	"""
	with open(filename) as f:
		cfg = {}
		for line in f:
			line = line.strip()
			if line and not line.startswith("#"):
				try:
					(key, value) = line.split('=', 1)
					cfg[key] = value
				except ValueError:
					pass # Happens when line has no '=', ignore
		return cfg

class BitBot(irc.bot.SingleServerIRCBot):
	def __init__(self, ircnet):
		self.ircnet = ircnet
		server, port = open(
			handlers.conf("ircnet-%s" % ircnet)).read().strip().split(":", 1)
		port = int(port)
		nickname = "BitBot"
		self._proxy = None
		irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname,
			nickname)
		
	def _rpc(self, method, *args):
		if not self._proxy:
			self._proxy_connect()
		while True:
			try:
				return getattr(self._proxy, method)(*args)
			except IOError:
				self._proxy_connect()
				time.sleep(.25)

	def _proxy_connect(self):
		# In case the config changed, read it everytime we connect
		cfg = read_config_file(os.path.expanduser("~/.bitcoin/bitcoin.conf"))
		port = int(cfg.get('rpcport', '8332'))
		url = "http://%s:%s@localhost:%s" % \
			(cfg['rpcuser'], cfg['rpcpassword'], port)
		self._proxy = ServiceProxy(url)

	def on_nicknameinuse(self, c, e):
		c.nick(c.get_nickname() + "_")

	def on_welcome(self, c, e):
		# join autochannels
		f = open(handlers.conf("channels-%s" % self.ircnet))
		for line in f:
			c.join(*line.strip().split(' ', 1))

	def reload_handlers(self):
		print "Reloading handlers"
		reload(handlers)

	def on_privmsg(self, c, e):
		handlers.on_privmsg(self, e)

	def on_pubmsg(self, c, e):
		handlers.on_pubmsg(self, e)

	def on_userhost(self, c, e):
		handlers.on_userhost(self, e)

if __name__ == "__main__":
	import sys
	b = BitBot(sys.argv[1])
	b.start()
