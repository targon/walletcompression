#!/usr/bin/env python

import json, os, sys, time

maxsize = 500
goodsize = 0.01

def rpccall(cmd, decodejson=False):
    f = os.popen("bitcoind %s" % cmd)#2>/dev/null
    s = f.read()
    if not f.close() is None:
	return
    if decodejson:
	return json.loads(s)
    else:
	return s
    
print ""
print "Bitcoin Wallet Compression"
print ""
    
if rpccall("listunspent") is None:
    s = os.popen("which bitcoind").read()
    if s=="":
	print "You need to install 'bitcoind' for this program to work."
	os.system("sudo apt-get install bitcoind")
    s = os.popen("which bitcoind").read()
    if s=="":
	print "bitcoind was not installed successfully."
	sys.exit()
    print "Starting bitcoind..."
    os.system(s[:-1] + " -addnode=173.242.112.53 &")
    for i in range(20):
	time.sleep(1)
	if not rpccall("listunspent") is None:
	    break
    if rpccall("listunspent") is None:
	print "Error: bitcoind could not be started"
	print "Please make sure you have closed your bitcoin wallet!"
	sys.exit(1)
    terminate = True
else:
    terminate = False

coins = rpccall("listunspent", decodejson=True)
good = []
goodamount = 0.0
bad = []
badamount = 0.0
for coin in coins:
    if coin["amount"]>=goodsize:
	goodamount += coin["amount"]
	good.append(coin)
    else:
	badamount += coin["amount"]
	bad.append(coin)
print "Inital wallet status:"
print "You have %.8f BTC in %d good coins." % (goodamount, len(good))
print "You have %.8f BTC in %d bad coins." % (badamount, len(bad))
print ""
	
if not good:
    print "I need at least one good coin (value >= %.3f BTC) to compress your wallet." % goodsize
    sys.exit(1)
    
if not bad:
    print "Your wallet is already well compressed."
    sys.exit(0)

#sys.exit(0)

print "Enter one of your addresses to send the compressed bitcoins to, or leave empty to create a new one."
print "Address [empty for new]:",
destination = raw_input()
print ""
if not destination:
    destination = rpccall("getnewaddress 'Wallet compression %s'" % time.strftime("%Y-%m-%d %H:%M"))
check = rpccall("validateaddress %s" % destination, decodejson=True)
if not check["isvalid"]:
    print "This is not a valid bitcoin address"
    sys.exit(1)
if not check["ismine"]:
    print "This address belongs to a different wallet!"
    sys.exit(1)

good.sort(key=lambda coin: coin["amount"]*coin["confirmations"])
queue = []
total = 0.
while good and bad:
    base = good.pop()
    tx = [{"txid": base["txid"], "vout": base["vout"]}]
    value = base["amount"]
    while bad:
	last = bad.pop()
	tx.append({"txid": last["txid"], "vout": last["vout"]})
	value += last["amount"]
	raw = rpccall("createrawtransaction '%s' '%s'" % 
	       (json.dumps(tx), json.dumps({destination: value})))
	signed = rpccall("signrawtransaction %s" % (raw,), decodejson=True)
	if not signed["complete"]:
	    print "There was a problem signing a transaction. Cannot continue."
	    sys.exit(1)
	signed = signed["hex"]
	if len(signed)/2>maxsize:
	    bad.append(last)
	    tx = tx[:-1]
	    value -= last["amount"]
	    break
    if len(tx)<2:
	print "Could not compress a single bad coin. Giving up."
	sys.exit(1)
    raw = rpccall("createrawtransaction '%s' '%s'" % 
	    (json.dumps(tx), json.dumps({destination: value})))
    signed = rpccall("signrawtransaction %s" % (raw,), decodejson=True)
    if not signed["complete"]:
	print "There was a problem signing a transaction. Cannot continue."
	sys.exit(1)
    signed = signed["hex"]
    print "Combined one good and %d bad coins into a transaction of size %d and value %.8f BTC." % (len(tx)-1, len(signed)/2, value)
    queue.append(signed)
    total += value

print ""
if queue:
    print "Created %d transactions for a total of %.8f BTC. Until the transactions confirm, " % (len(queue), total)
    print "the Bitcoins will be temporarily unavailable."
    print "Do you want to issue these transactions [Y]?",
    yesno = raw_input()
    print ""

    if not yesno or yesno[0].upper()=="Y":
	for signed in queue:
	    print "Sending transaction: http://blockchain.info/de/tx/%s" % rpccall("sendrawtransaction %s" % signed).strip()
    else:
	sys.exit(0)
    print ""
    
if bad:
    print "There are still some bad coins left. Please wait for the generated transactions"
    print "to confirm, then rerun this program."
else:
    print "All bad coins were sucessfully compressed. Please wait for the generated transactions"
    print "to confirm."
print "Note that it can take a day or longer for the transactions to confirm."
print "If the transactions don't confirm at all, you can recover the coins with these"
print "instructions: https://bitcointalk.org/index.php?topic=35214.0"
print ""

print "Did you like this program? Please consider donating for it! Send"
print "bitcoins to 12c8P6JeReV3HGtLg91jwh6vXET9LuZ1aq. Thank You!"
print ""
    
if terminate:
    rpccall("stop", False)
