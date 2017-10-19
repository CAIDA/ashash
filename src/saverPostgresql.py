import psycopg2
import logging
from collections import defaultdict
import json
from sshtunnel import SSHTunnelForwarder

#TODO make the timebin value function of what is passed in ts

class saverPostgresql(object):

    """Dumps only hegemony results to a Postgresql database. """

    def __init__(self, starttime, af, saverQueue, host="127.0.0.1", dbname="ihr"):
       

        self.saverQueue = saverQueue
        self.expid = None
        self.prevts = -1
        self.asNames = defaultdict(str, json.load(open("data/asNames.json")))
        self.starttime = starttime
        self.af = af

        # with SSHTunnelForwarder(
            # 'romain.iijlab.net',
            # ssh_private_key="/home/romain/.ssh/id_ed25519",
            # ssh_username="romain",
            # remote_bind_address=('127.0.0.1', 5432)) as server:

            # server.start()
            # logging.debug("SSH tunnel opened")
            # local_port = str(server.local_bind_port)
            # conn_string = "host='127.0.0.1' port='%s' dbname='%s'" % (local_port, dbname)

        conn_string = "host='127.0.0.1' dbname='%s'" % (dbname)
        self.conn = psycopg2.connect(conn_string)
        self.cursor = self.conn.cursor()
        logging.debug("Connected to the PostgreSQL server")

        self.run()

    def run(self):

        while True:
            elem = self.saverQueue.get()
            if isinstance(elem, str) and elem.endswith(";"):
                self.cursor.execute(elem)
            else:
                self.save(elem)
            self.saverQueue.task_done()


    def save(self, elem):
        t, data = elem

        if t == "hegemony":
            ts, scope, hege = data

            if self.prevts != ts:
                self.prevts = ts
                logging.debug("start recording hegemony")

            self.cursor.execute("""do $$
                begin 
                    insert into ihr_asn(number, name, tartiflette, disco, ashash) values(%s, %s, FALSE, FALSE, TRUE);
                exception when unique_violation then
                    update ihr_asn set ashash = TRUE where number = %s;
                end $$;""", (scope, self.asNames["AS"+str(scope)], scope))

            for asn in hege.keys():
                if not asn.startswith("{"):
                    self.cursor.execute("INSERT INTO ihr_asn(number, name, tartiflette, disco, ashash) select %s, %s, FALSE, FALSE, FALSE WHERE NOT EXISTS ( SELECT number FROM ihr_asn WHERE number = %s); ", (asn, self.asNames["AS"+str(asn)], asn))
            
            self.cursor.executemany("INSERT INTO ihr_hegemony(timebin, originasn_id, asn_id, hege, af) VALUES (%s, %s, %s, %s, %s)", [(self.starttime, scope, k, v, self.af) for k,v in hege.iteritems() if not k.startswith("{") ] )

            # elif t == "graphchange":
                # self.cursor.execute("INSERT INTO graphchange(ts, scope, asn, nbvote, diffhege, expid) VALUES (?, ?, ?, ?, ?, ?)", data+[self.expid])

            # elif t == "anomalouspath":
                # self.cursor.execute("INSERT INTO anomalouspath(ts, path, origas, anoasn, hegepath, score, expid) VALUES (?, ?, ?, ?, ?, ?, ?)", data+[self.expid])

