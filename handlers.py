import os
import re
import sys
from irc.client import NickMask
here = lambda x: os.path.join(os.path.dirname(__file__), x)
conf = lambda x: os.path.join(os.path.dirname(__file__), "conf/", x)

def resolve_alias(source):
	try:
		f = open(conf("aliases"))
		for line in f:
			frm, to = line.strip().split()
			if frm == source:
				return to
	except IOError:
		pass

	return "%s" % source

###########################
# Wrappers around bot._rpc
# Resolve aliases at the last possible moment.
def has_account(bot, host):
	accounts = bot._rpc("listaccounts")
	return resolve_alias(host) in accounts

def create_account(bot, host):
	bot._rpc("getnewaddress", "%s" % resolve_alias(host))

def get_balance(bot, host):
	return bot._rpc("getbalance", "%s" % resolve_alias(host))

def get_account_address(bot, host):
	return bot._rpc("getaccountaddress", "%s" % resolve_alias(host))

def move(bot, src, dst, amount):
	bot._rpc("move", "%s" % resolve_alias(src),
		"%s" % resolve_alias(dst), amount)

def get_txfee():
	try:
		return float(open(conf("txfee")).read().strip())
	except IOError:
		return 0.001 # fall back

def sendfrom(bot, host, address, amount):
	host = "%s" % resolve_alias(host)
	return bot._rpc("sendfrom", "%s" % host, "%s" % address, amount)

######################
# Actual IRC handlers
waiting_on_host = {} # nickname => (fun, list(partialargs))

USERHOST_RE = re.compile("([a-zA-Z0-9_\\\[\]{}^`|-]+)(\*?)=[+-](.+)")
def on_userhost(bot, e):
	m = USERHOST_RE.search(e.arguments[0].strip())
	if m:
		nick = m.group(1)
		ircop = m.group(2)
		host = m.group(3)
		if nick in waiting_on_host:
			fun, partialargs = waiting_on_host[nick]
			partialargs.append("%s!%s" % (nick, host))
			fun(*partialargs)
			del waiting_on_host[nick]

def on_privmsg(bot, e):
	args = e.arguments[0].split()
	# privmsg don't need to be prefixed with +, but might be.
	handle_command(bot, e, args)

def on_pubmsg(bot, e):
	args = e.arguments[0].split()
	if args[0].startswith("+"):
		handle_command(bot, e, args)

def handle_command(bot, e, args):
	thismodule = sys.modules[__name__]
	if args[0].startswith("+"):
		args[0] = args[0][1:]
	if not args[0].strip():
		return
	if not hasattr(thismodule, "do_%s" % args[0]):
		return
	getattr(thismodule, "do_%s" % args[0])(bot, e, args[1:])

###################
# Command handlers
def do_reload(bot, e, args):
	bot.reload_handlers()

def do_help(bot, e, args):
	target = e.target
	if e.type == "privmsg":
		target = e.source.nick

	msg = lambda m: bot.connection.privmsg(target, m)
	thismodule = sys.modules[__name__]
	for elem in dir(thismodule):
		if not elem.startswith("do_"):
			continue
		fun = getattr(thismodule, elem)
		if not fun.__doc__:
			continue
		msg(fun.__doc__)

def do_ls(bot, e, args):
	# small test-function.
	if e.type == "privmsg":
		bot.connection.privmsg(e.source.nick, "Can only use +ls in channels")
		return

	users = bot.channels[e.target].users()
	for user in users:
		bot.connection.send_raw("USERHOST :%s" % user)

def send_tip(bot, target, amount, currency, source, dest):
	print "Sending a tip from %s to %s" % (source, dest)
	source = NickMask(source)
	dest = NickMask(dest)
	bot.connection.privmsg(target, "Sending %s%s from %s to %s" % (amount, currency, source.nick, dest.nick))
	bot.connection.privmsg(dest.nick,
		"%s just sent you a tip of %s%s" % (source.nick, amount, currency))
	if not has_account(bot, dest):
		create_account(bot, dest)
		bot.connection.privmsg(dest.nick,
			"I created a wallet for you. For more information on your wallet, please send me the +wallet command.")
	move(bot, source, dest, amount)

def do_tip(bot, e, args):
	"+tip <nick> <amount><BTC|EUR> (give someone a bit of money)"
	if len(args) != 2:
		bot.connection.privmsg(e.target, "Usage: +tip <nick> <amount><BTC|EUR>")
		return

	user = args[0]
	amount = args[1]
	if 'EUR' not in amount and 'BTC' not in amount:
		print "Invalid amount:", amount
		bot.connection.privmsg(e.target, "Usage: +tip <nick> <amount><BTC|EUR>")
		return

	currency = amount[-3:]
	amount = float(amount[:-3])

	if currency != "BTC":
		bot.connection.privmsg(e.target,
			"Currently only BTC allowed as currency")
		return

	if user not in bot.channels[e.target].users():
		bot.connection.privmsg(e.target, "%s is not on this channel." % user)
		return

	if not has_account(bot, e.source):
		return bot.connection.privmsg(e.target,
			"You don't have a wallet. Use +wallet to get more information.")

	balance = get_balance(bot, e.source)
	if amount > balance:
		return bot.connection.privmsg(e.source.nick,
			"You don't have enough BTC in your wallet.")

	# We need a full userhost to be able to determine the account name for the
	# user. Therefore, we need to send a USERHOST command, which is handled by
	# the on_userhost handler above. This means that we have to split
	# do_tip into two functions, and wait for the userhost to arrive.
	waiting_on_host[user] = (send_tip,
		[bot, e.target, amount, currency, e.source])

	# unfortunately, the bot.connection.userhost() command seems to be broken.
	bot.connection.send_raw("USERHOST :%s" % user)


def do_balance(bot, e, args):
	"+balance (shows your balance)"
	if e.source != resolve_alias(e.source):
		bot.connection.privmsg(e.source.nick,
			"I know you by: %s." % resolve_alias(e.source))

	if not has_account(bot, e.source):
		bot.connection.privmsg(e.source.nick, "You have no wallet yet.")
	else:
		balance = get_balance(bot, e.source)
		bot.connection.privmsg(e.source.nick,
			"Balance: %sBTC" % balance)

def do_wallet(bot, e, args):
	"+wallet (shows the address for receiving payments to your account)"
	if e.source != resolve_alias(e.source):
		bot.connection.privmsg(e.source.nick,
			"I know you by: %s." % resolve_alias(e.source))

	if not has_account(bot, e.source):
		create_account(bot, e.source)
		bot.connection.privmsg(e.source.nick, "I created a wallet for you")
	address = get_account_address(bot, e.source)
	bot.connection.privmsg(e.source.nick,
		"Your address for receiving payments is: %s" % address)

def do_txfee(bot, e, args):
	"+txfee (gets the current transfer fee)"
	target = e.target
	if e.type == "privmsg":
		target = e.source.nick
	bot.connection.privmsg(target,
		"The current transfer fee is %sBTC" % get_txfee())
	
def do_transfer(bot, e, args):
	"+transfer <amount><BTC|EUR> <bitcoinaddress> (transfer money to another account)"
	target = e.target
	if e.type == "privmsg":
		target = e.source.nick
	if len(args) != 2:
		return bot.connection.privmsg(target,
			"Usage: +transfer <amount><BTC|EUR> <bitcoinaddress>")

	amount = args[0]
	address = args[1]
	if 'EUR' not in amount and 'BTC' not in amount:
		print "Invalid amount:", amount
		return bot.connection.privmsg(target,
			"Usage: +transfer <amount><BTC|EUR> <bitcoinaddress>")

	address_info = bot._rpc("validateaddress", address)
	if 'isvalid' not in address_info or not address_info['isvalid']:
		return bot.connection.privmsg(target,
			"%s is not a valid address" % address)

	currency = amount[-3:]
	amount = float(amount[:-3])

	if currency != "BTC":
		bot.connection.privmsg(target,
			"Currently only BTC allowed as currency")
		return

	if not has_account(bot, e.source):
		return bot.connection.privmsg(target,
			"You don't have a wallet. Use +wallet to get more information.")

	txfee = get_txfee()
	balance = get_balance(bot, e.source)
	if amount + txfee > balance:
		return bot.connection.privmsg(e.source.nick,
			"You don't have enough BTC in your wallet. (Current transfer fee is %sBTC)" % txfee)

	txid = None
	try:
		txid = sendfrom(bot, e.source, address, amount)
	except:
		bot.connection.privmsg(e.source.nick, "An error occurred while trying to sendfrom.")

	if not txid:
		return
	bot.connection.privmsg(target, "Follow your transaction: http://blockchain.info/tx/%s" % txid)
