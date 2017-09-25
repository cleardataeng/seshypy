.. highlight:: python

=====
Usage
=====

There are broadly two options for using seshypy. First, you can use it to create
clients for calling API Gateway via specific method calls. For example, if you
have a library catalog application, you could have a `books` session, that has
the methods, `get_books`, `post_book`, etc. Those methods would know the route
and make the call accordingly.

The second method, is to use it as a very client, that only manages your
session. In that case, you simply create a `base_session`, then make the calls
like, `sess.get("books/")` or `sess.post("books/", json=book_data)`.

----------------------------------
Method 1 - specific client methods
----------------------------------

::

   # client.py
   from builtins import super
   from seshypy.base_session import BaseSession


   class BookSession(BaseSession):
       """Api Gateway Calls and Helper Methods Pertaining to /books routes """
       def __init__(self, cache_methods=None, *args, **kwargs):
           cache_methods = cache_methods if cache_methods is not None else [
               'get_books',
           ]
           super().__init__(cache_methods=cache_methods, *args, **kwargs)

       def get_books(self):
           """Get books.

           Returns:
               list: boooks
           """
           path = 'books/'
           return self.get(path).json()

::

   # caller.py
   from client import BookSession
   session = BookSession("https://yourapi.com", **creds)
   books = session.get_books()

----------------------------------
Method 2 - thin API method wrapper
----------------------------------

::

   # caller.py
   from seshypy import BaseSession
   session = BaseSession("https://yourapi.com", **creds)
   books = session.get("books/").json()
