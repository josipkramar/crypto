# sqlhelpers.py

from blockchain import Block, Blockchain

class InvalidTransactionException(Exception): pass
class InsufficientFundsException(Exception): pass

class Table():
    def __init__(self, table_name, *args):
        self.table = table_name
        self.columns = "(%s)" % ",".join(args)
        self.columnsList = args
        if isnewtable(table_name):
            create_data = ""
            for column in self.columnsList:
                create_data += "%s varchar(100)," % column
            from app import mysql
            cur = mysql.connection.cursor()
            cur.execute("CREATE TABLE %s(%s)" % (self.table, create_data[:len(create_data) - 1]))
            cur.close()

    def getall(self):
        from app import mysql
        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM %s" % self.table)
        data = cur.fetchall()
        return data

    def getone(self, search, value):
        from app import mysql
        data = {}
        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM %s WHERE %s = \"%s\"" % (self.table, search, value))
        if result > 0:
            data = cur.fetchone()
        cur.close()
        return data

    def deleteone(self, search, value):
        from app import mysql
        cur = mysql.connection.cursor()
        cur.execute("DELETE from %s where %s = \"%s\"" % (self.table, search, value))
        mysql.connection.commit()
        cur.close()

    def deleteall(self):
        self.drop()
        self.__init__(self.table, *self.columnsList)

    def drop(self):
        from app import mysql
        cur = mysql.connection.cursor()
        cur.execute("DROP TABLE %s" % self.table)
        cur.close()

    def insert(self, *args):
        from app import mysql
        data = ""
        for arg in args:
            data += "\"%s\"," % (arg)

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO %s%s VALUES(%s)" % (self.table, self.columns, data[:len(data) - 1]))
        mysql.connection.commit()
        cur.close()


def sql_raw(execution):
    from app import mysql
    cur = mysql.connection.cursor()
    cur.execute(execution)
    mysql.connection.commit()
    cur.close()


def isnewtable(tableName):
    from app import mysql
    cur = mysql.connection.cursor()

    try:
        result = cur.execute("SELECT * from %s" % tableName)
        cur.close()
    except:
        return True
    else:
        return False


def isnewuser(username):
    users = Table("users", "name", "email", "username", "password")
    data = users.getall()
    usernames = [user.get('username') for user in data]

    return False if username in usernames else True


def send_money(sender, recipient, amount):
    from app import mysql  # Uvozi se ovdje, kada je potrebno

    try:
        amount = float(amount)
    except ValueError:
        raise InvalidTransactionException("Invalid Transaction.")

    if amount > get_balance(sender) and sender != "BANK":
        raise InsufficientFundsException("Insufficient Funds.")
    elif sender == recipient or amount <= 0.00:
        raise InvalidTransactionException("Invalid Transaction.")
    elif isnewuser(recipient):
        raise InvalidTransactionException("User Does Not Exist.")

    blockchain = get_blockchain()
    number = len(blockchain.chain) + 1
    data = "%s-->%s-->%s" % (sender, recipient, amount)
    blockchain.mine(Block(number, data=data))
    sync_blockchain(blockchain)


def get_balance(username):
    from app import mysql  # Uvozi se ovdje, kada je potrebno

    balance = 0.00
    blockchain = get_blockchain()

    for block in blockchain.chain:
        data = block.data.split("-->")
        if username == data[0]:
            balance -= float(data[2])
        elif username == data[1]:
            balance += float(data[2])
    return balance


def get_blockchain():
    blockchain = Blockchain()
    blockchain_sql = Table("blockchain", "number", "hash", "previous", "data", "nonce")
    for b in blockchain_sql.getall():
        blockchain.add(Block(int(b.get('number')), b.get('previous'), b.get('data'), int(b.get('nonce'))))

    return blockchain


def sync_blockchain(blockchain):
    from app import mysql  # Uvozi se ovdje, kada je potrebno
    blockchain_sql = Table("blockchain", "number", "hash", "previous", "data", "nonce")
    blockchain_sql.deleteall()

    for block in blockchain.chain:
        blockchain_sql.insert(str(block.number), block.hash(), block.previous_hash, block.data, block.nonce)
