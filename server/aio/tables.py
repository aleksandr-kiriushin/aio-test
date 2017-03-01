"""
Module with database tables declaration
Database: aio
Schema: aio
Tables: tokens, users, remote_managers, local_managers, restaurants,
        orders, dishes, menu, categories, trees
"""

import sqlalchemy as sa

from .settings import settings

metadata = sa.MetaData()

db = settings["database"]
n = db["string_len"]
acc = db["currency_acc"]
schema = db["schema"]
hash_n = db["hash_len"]
salt_n = db["salt_len"]
token_n = db["token_len"]

tokens = sa.Table('tokens', metadata,
                  sa.Column('token', sa.String(token_n), nullable=False),
                  sa.Column('user', sa.Integer,
                             sa.ForeignKey('users.id')),
                  sa.Column('inserted_at', sa.TIMESTAMP,
                            default=sa.func.current_timestamp(), nullable=False),
                  schema=schema)

users = sa.Table('users', metadata,
                 sa.Column('id', sa.Integer, primary_key=True),
                 sa.Column('login', sa.String(n), nullable=False),
                 sa.Column('password', sa.String(hash_n), nullable=False),
                 sa.Column('salt', sa.String(salt_n), nullable=False),
                 schema=schema)

remote_managers = sa.Table('remote_managers', metadata,
                           sa.Column('id', sa.Integer, primary_key=True),
                           sa.Column('user', sa.Integer,
                                      sa.ForeignKey('users.id')),
                           sa.Column('name', sa.String(n), nullable=False),
                           #  sa.Column('restaurant', sa.Integer,
                                     #  sa.ForeignKey('restaurants.id')),
                           schema=schema)

local_managers = sa.Table('local_managers', metadata,
                          sa.Column('id', sa.Integer, primary_key=True),
                          sa.Column('user', sa.Integer,
                                     sa.ForeignKey('users.id')),
                          sa.Column('name', sa.String(n), nullable=False),
                          schema=schema)

restaurants = sa.Table('restaurants', metadata,
                       sa.Column('id', sa.Integer, primary_key=True),
                       sa.Column('name', sa.String(n), nullable=False),
                       schema=schema)

orders = sa.Table('orders', metadata,
                  sa.Column('id', sa.Integer, primary_key=True),
                  sa.Column('manager', sa.Integer,
                            sa.ForeignKey('remote_managers.id')),
                  sa.Column('tree', sa.Integer,
                            sa.ForeignKey('trees.id')),
                  sa.Column('order', sa.JSON, nullable=False),
                  sa.Column('ordered_at', sa.TIMESTAMP, nullable=False),
                  schema=schema)

dishes = sa.Table('dishes', metadata,
                  sa.Column('id', sa.Integer, primary_key=True),
                  #  sa.Column('init', sa.Integer),
                  #  sa.Column('previous', sa.Integer),
                  sa.Column('name', sa.String(n), nullable=False),
                  sa.Column('discription', sa.TEXT, nullable=False),
                  sa.Column('price', sa.Numeric(*acc), nullable=False),
                  sa.Column('category', sa.Integer,
                            sa.ForeignKey('categories.id')),
                  #  sa.Column('tree', sa.Integer,
                            #  sa.ForeignKey('trees.id')),
                  sa.Column('changed_at', sa.TIMESTAMP,
                            default=sa.func.current_timestamp(), nullable=False),
                  sa.Column('changed_by', sa.Integer,
                            sa.ForeignKey('local_managers.id')),
                  schema=schema)

menu = sa.Table('menu', metadata,
                sa.Column('dish', sa.Integer,
                          sa.ForeignKey('dishes.id')),
                #  sa.Column('manager', sa.Integer,
                          #  sa.ForeignKey('local_managers.id')),
                #  sa.Column('tree', sa.Integer,
                          #  sa.ForeignKey('trees.id')),
                #  sa.Column('order', sa.JSON, nullable=False),
                schema=schema)

categories = sa.Table('categories', metadata,
                      sa.Column('id', sa.Integer, primary_key=True),
                      sa.Column('name', sa.String(n), nullable=False),
                      sa.Column('changed_at', sa.TIMESTAMP,
                                default=sa.func.current_timestamp(), nullable=False),
                      sa.Column('changed_by', sa.Integer,
                                sa.ForeignKey('local_managers.id')),
                      schema=schema)

trees = sa.Table('trees', metadata,
                 sa.Column('id', sa.Integer, primary_key=True),
                 sa.Column('tree', sa.JSON, nullable=False),
                 sa.Column('changed_at', sa.TIMESTAMP,
                           default=sa.func.current_timestamp(), nullable=False),
                 sa.Column('changed_by', sa.Integer,
                           sa.ForeignKey('local_managers.id')),
                 schema=schema)
