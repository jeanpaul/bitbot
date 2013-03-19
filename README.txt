BitBot is an IRC bot for transfering (small) amounts of bitcoins (BTCs) to
other IRC users.

If you care to donate some BTCs, 18NcKvHXVTpx3EcUoUx61Cu93w2CoEC8YX is my
address :-)

Jean-Paul van Oosten <bitcoin@jpvanoosten.nl>


Dependencies
------------

BitBot requires a running bitcoind and python-irc. The latter can be installed
with `pip install irc`. Bitcoind can be downloaded from bitcoin.org.

Please know that before you can see your transactions, you need to have the
latest blocks in the blockchain; this might take a while (see `bitcoind
getblockcount` to see where you are at).

To communicate with bitcoind, we use the jsonrpc library from
http://json-rpc.org/wiki/python-json-rpc, but it is included in the package.
It is licensed as LGPL.

The bitcoin-24.com integration uses the requests library (`pip install
requests`). This is optional, and everything will work with just BTC. The
bitcoin24 module was provided by wilatai, and has an MIT license.

Configuration
-------------

For the IRC-connection, BitBot works with so-called ircnets. If you call your
ircnet FreeNode, BitBot expects two files in ./conf:

- ircnet-FreeNode
  Contains the configuration of host and port in the form: `host:port`, for
  example: `irc.freenode.net:6667`
- channels-FreeNode
  Contains the channels, one on each line. If the channel is protected with a
  key, separate it from the channel with a space.

The rpc user and password for the bitcoin daemon is done through reading
~/.bitcoin/bitcoin.conf. This is not ideal (since you might not be running the
bitcoin daemon as the same user as BitBot, so this will probably change in the
future).

Furthermore, you can make aliases between hosts (for example, if someone
connects using two different hosts). Configure this through the `conf/aliases`
file, which has the following format:

	nick1!ident1@host1 nick2!ident2@host2

this aliases nick1 to nick2.

Finally, the transfer fee for transfering funds from a BitBot account to your
own wallet is configurable through `conf/txfee`. Be advised that usually
transfers are confirmed more quickly when the transfer fee is not 0.


Available commands
------------------

+help
+wallet (shows the address for receiving payments to your account)
+balance (shows your balance)
+tip <nick> <amount><BTC|EUR> (give someone a bit of money)
+transfer <amount><BTC|EUR> <bitcoinaddress> (transfer money to another account)
+txfee (gets the current transfer fee)
