"""
NOTE Generated via Cursor running on claude-3.7-sonnet. Supervised by Arvin Armand.

Wrapper module for asynchronous MongoDB testing with mongomock.

"""
class AsyncMongoMockCollection:
    """A wrapper for mongomock.Collection that adds support for Motor's async methods."""
    
    def __init__(self, collection):
        self.collection = collection
        
    async def find_one(self, *args, **kwargs):
        """Async wrapper for find_one."""
        return self.collection.find_one(*args, **kwargs)
        
    async def insert_one(self, *args, **kwargs):
        """Async wrapper for insert_one."""
        return self.collection.insert_one(*args, **kwargs)
        
    async def delete_one(self, *args, **kwargs):
        """Async wrapper for delete_one."""
        return self.collection.delete_one(*args, **kwargs)
        
    async def count_documents(self, *args, **kwargs):
        """Async wrapper for count_documents."""
        return self.collection.count_documents(*args, **kwargs)
        
    def find(self, *args, **kwargs):
        """Returns a cursor wrapper with to_list support."""
        cursor = self.collection.find(*args, **kwargs)
        return AsyncCursor(cursor)
    
    async def delete_many(self, *args, **kwargs):
        """Async wrapper for delete_many."""
        return self.collection.delete_many(*args, **kwargs)

class AsyncCursor:
    """A wrapper for mongomock.Cursor that adds support for to_list and async iteration."""
    
    def __init__(self, cursor):
        self.cursor = cursor
        
    async def to_list(self, length=None):
        """Convert the cursor to a list."""
        if length is None:
            return list(self.cursor)
        else:
            return list(self.cursor)[:length]
    
    def __aiter__(self):
        """Support for async iteration using 'async for'."""
        self._cached_results = list(self.cursor)
        return self
        
    async def __anext__(self):
        """Get the next item in the async iteration."""
        try:
            if not hasattr(self, '_index'):
                self._index = 0
            if not hasattr(self, '_cached_results'):
                self._cached_results = list(self.cursor)
            
            if self._index < len(self._cached_results):
                item = self._cached_results[self._index]
                self._index += 1
                return item
            else:
                raise StopAsyncIteration
        except StopIteration:
            raise StopAsyncIteration