import datetime
import json
import logging
import os
import re

logger = logging.getLogger(__name__)


class BookmarkManager(object):
    KEY_REGEX = re.compile('^[a-zA-Z0-9_]{1,16}$')

    def __init__(self, bookmark_file):
        self.bookmark_file = bookmark_file
        self._bookmarks = None

    @property
    def bookmarks(self):
        if self._bookmarks is not None:
            return self._bookmarks

        if not self.load():
            return None

        return self._bookmarks

    def add_bookmark(self, name, path):
        """Add a new bookmark with the given name"""
        bookmarks = self.bookmarks
        if bookmarks is None:
            return False

        bookmarks[name] = Bookmark(
            path=str(path),
            created_on=datetime.datetime.now()
        )
        self._bookmarks = bookmarks
        self.save()

        return True

    def remove_bookmark(self, k):
        """Remove the named bookmark"""
        bookmarks = self.bookmarks

        if k not in bookmarks:
            return False

        del bookmarks[k]
        self._bookmarks = bookmarks
        self.save()

        return True

    @classmethod
    def clean_key(cls, k):
        if not cls.KEY_REGEX.match(k):
            return None

        return k

    def clean_data(self, data):
        bookmarks = data.get('bookmarks', {})
        return {k: Bookmark(**v) for k, v in bookmarks.items()}

    def load(self):
        """
        Load data from the bookmarks file into the bookmarks field

        :returns: Whether the load succeeded
        :rtype bool:
        """
        data = None
        ff = self.bookmark_file

        # Don't try to read something we know isn't present; it's not an error
        # though, we'll try to save an initial copy when we add some bookmarks
        if not os.path.exists(ff):
            logger.debug('No bookmark file %s, setting empty', ff)
            self._bookmarks = {}
            return True

        try:
            with open(ff, 'r') as f:
                data = self.clean_data(json.load(f))
        except IOError:
            logger.exception('Error reading bookmark file %s', ff)
        except ValueError:
            logger.exception('Error reading contents of bookmark file %s', ff)
        except AttributeError:
            logger.exception('Error with bookmark file format (%s)', ff)
        else:
            logger.debug('Successfully read %d bookmarks', len(data))

        self._bookmarks = data
        return data is not None

    def save(self):
        """Save bookmark data to file"""
        data = {
            'bookmarks': {k: v.__dict__ for k, v in self.bookmarks.items()}
        }
        data = json.dumps(data)

        with open(self.bookmark_file, 'w') as f:
            f.write(data)


class Bookmark(object):
    def __init__(self, path, created_on=None, *args, **kwargs):
        self.path = path

        if created_on is not None:
            if isinstance(created_on, str):
                self.created_on = created_on
            else:
                self.created_on = created_on.strftime('%Y-%m-%dT%H:%M:%SZ')

    def __str__(self):
        return self.path
