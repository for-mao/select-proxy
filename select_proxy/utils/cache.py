

class CacheUtil:
    cache = {}

    @classmethod
    def query_cache(cls, func):
        def wrapper(self, *args, **kwargs):
            if func in cls.cache:
                return cls.cache.get(func)
            else:
                res = func(self)
                cls.cache.update({func: res})
                return res
        return wrapper
