
""" Stubbing out a bunch of "twisted" stuff that the plugins call """

class task:
    def deferLater(a,b,f):
        return f(b)

class reactor:
    pass

class threads:
    def deferToThread(func, arg):
        return func(arg)

class defer:
     retval = None
     
     def inlineCallbacks(f):
         """ decorator that calls something which uses returnValue, below """

         async def g(*args):
             print("about to await")
             await f(*args)
             print("don await")
             return defer.retval
         return g

     def returnValue(v):
         defer.retval = v
