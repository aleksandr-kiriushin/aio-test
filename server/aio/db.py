import asyncio
import os
import binascii
from typing import Dict
from abc import ABCMeta, abstractmethod
from aiopg.sa import create_engine
import sqlalchemy as sa

from datetime import datetime
import secrets
import hashlib

from .settings import settings
from .tables import (metadata, remote_managers, local_managers, restaurants,
                     users, tokens, orders, dishes, menu, categories, trees)

db = settings["database"]
dbname = db["dbname"]
host = db["host"]
port = db["port"]
dklen = db["hash_len"] // 2
token_n = db["token_len"] // 2
salt_n = db["salt_len"] // 2
token_time = db["token_time"]

dbuser = os.environ["DBUSER"]
dbpassword = os.environ["DBPASSWORD"]

def hashtoken(token_n=token_n):
    btoken = secrets.token_hex(token_n).encode()
    return btoken

def hashpass(password, salt=None, dklen=dklen, salt_n=salt_n, iterations=10000):
    if salt is None:
        salt = secrets.token_hex(salt_n).encode()
    bpassword = password.encode()
    bhash = binascii.hexlify(
                hashlib.pbkdf2_hmac("sha256", bpassword, salt,
                                    iterations, dklen=dklen))
    return salt, bhash

class Manager(metaclass=ABCMeta):
    @property
    def dsn(self):
        """ data source name """

        return  f'dbmane={dbname} user={dbuser} password={dbpassword} host={host} port={port}'

    @property
    @abstractmethod
    def user_table(self):
        """ table for users of current type """

        pass


    async def verify_credentials(self, login, password):
        """ verify login and password """

        async with create_engine(self.dsn) as engine:
            async with engine.acquire() as conn:
                join = sa.join(self.user_table, users, self.user_table.c.user == users.c.id)
                query = (users.select([self.user_table.c.id, users])
                         .select_from(join)
                         .where(users.c.login == login))
                async for uid, user in conn.execute(query):
                    test_hash = hashpass(password, user.salt)
                    if test_hash == user.password:
                        return uid

    async def create_token(self, uid):
        """ get session token by user id """

        token = hashtoken()
        values_dict = {'token': token, 'user': uid}
        tid = await self._insert(tokens, values_dict)
        if not tid:
            raise Exception("wrong token insertion")
        return token

    async def verify_token(self, token):
        """ verify session token """

        async with create_engine(self.dsn) as engine:
            async with engine.acquire() as conn:
                join = sa.join(self.user_table, tokens, self.user_table.c.id == tokens.c.user)
                query = (users.select([self.user_table.c.id, tokens])
                         .select_from(join)
                         .where(tokens.c.token == token))
                async for uid, token in conn.execute(query):
                    session_time = datetime.now() - token.c.inserted_at
                    if session_time.total_seconds() < token_time:
                        return uid

    async def _insert(self, table, values_dict):
        """ one value insertion to table """

        async with create_engine(self.dsn) as engine:
            async with engine.acquire() as conn:
                uid = await conn.scalar(table.insert().values(**values_dict))
                return uid

    async def create_all(self):
        """ one value insertion to table """

        async with create_engine(self.dsn) as engine:
            await metadata.create_all(engine)


class RemoteManager(Manager):
    """ local manager with administrative functions """

    @property
    def user_table(self):
        """ table for users of current type """

        return remote_managers

    async def get_menu(self):
        """ fetch all dishes from menu and the most actual tree id """

        async with create_engine(self.dsn) as engine:
            async with engine.acquire() as conn:
                join = sa.join(dishes, menu, dishes.c.id == menu.c.dish)
                query = (users.select([dishes]).select_from(join))
                dishes_ids = await conn.execute(query).fetchall()
                query = (trees.select([trees.c.id]).order_by(trees.c.id))
                tree_id = await conn.execute(query).first()
                return dishes_ids, tree_id

    async def store_order(self, uid, tree_id, order, ordered_at):
        """ store remote order """

        values_dict = {'manager': uid,
                       'tree': tree_id,
                       'order': order,
                       'ordered_at': ordered_at}
        return await self._insert(orders, values_dict)


class LocalManager(Manager):
    """ local manager with administrative functions """

    @property
    def user_table(self):
        """ table for users of current type """

        return local_managers

    async def create_user(self, user_table, login, password, **user_data):
        """ create new users """

        salt, hashed_pass = hashpass(password)
        user_dict = {'login': login, 'salt': salt, 'password': hashpass}
        async with create_engine(self.dsn) as engine:
            async with engine.acquire() as conn:
                trans = yield from conn.begin()
                uid = await conn.scalar(users.insert().values(**user_dict))
                if not uid:
                    yield from trans.rollback()
                else:
                    user_table_dict = {'user': uid, **user_data}
                    uid = await conn.scalar(user_table.insert().values(**user_table_dict))
                    if not uid:
                        yield from trans.rollback()
                    else:
                        yield from trans.commit()
                        return uid

    async def create_local_user(self, login, password, **user_data):
        """ create new local users """

        return await self.create_user(local_managers, login, password, **user_data)

    async def create_remote_user(self, login, password, **user_data):
        """ create new remote users """

        return await self.create_user(remote_managers, login, password, **user_data)


    async def add_category(self,
                           name: str,
                           changed_by: int):
        """ add new category of dishes """

        values_dict = {'name': name,
                       'changed_by': changed_by}
        return await self._insert(categories, values_dict)

    async def add_tree(self,
                       tree: Dict[int, int],  # json dict
                       changed_by: int):
        """ add tree of categories """

        values_dict = {'tree': tree,
                       'changed_by': changed_by}
        return await self._insert(trees, values_dict)

    async def add_dish_to_menu(self, dish):
        """ add dish to menu """

        values_dict = {'dish': dish}
        return await self._insert(menu, values_dict)

    async def add_dish(self,
                       name: str,
                       discription: str,
                       price: float,
                       category: int,
                       #  tree: int,
                       changed_by: int
                       ):
        """ add new dish to dish collection """

        values_dict = {'name': name,
                       'discription': discription,
                       'price': price,
                       'category': category,
                       #  'tree': tree,
                       'changed_by': changed_by,
                       }
        return await self._insert(dishes, values_dict)

    async def get_last_orders(self, n):
        """ get list of last orders """

        async with create_engine(self.dsn) as engine:
            async with engine.acquire() as conn:
                query = (users.select([orders]).order_by(orders.c.ordered_at))
                orders_list = await conn.execute(query).fetchmany(n)
                return orders_list

    async def get_starter_pack(self):
        """ initial database data """

        admin = await self.create_local_user('admin', 'admin', name='Admin')
        admin_token = await self.create_token(admin)
        guest = await self.create_remote_user('guest', 'guest', name='Guest')
        guest_token = await self.create_token(guest)

        tea = await self.add_category("Tea", admin)
        white_tea = await self.add_category("White", admin)
        green_tea = await self.add_category("Green", admin)
        tree = await self.add_tree({tea: {white_tea: None, green_tea: None}}, admin)

        async def init_dish(name, category):
            dish_id = await self.add_dish(name, name, 1.0, category, admin)
            await self.add_dish_to_menu(dish_id)

        green_tea_tasks = [init_dish(f"green_{i}", green_tea) for i in range(100)]
        white_tea_tasks = [init_dish(f"white_{i}", white_tea) for i in range(100)]
        dish_tasks = green_tea_tasks + white_tea_tasks
        await asyncio.wait(dish_tasks)
