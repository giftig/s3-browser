import json
import os
import uuid

import pytest

from s3_browser import bookmarks


class TestBookmarks:
    FILE_PREFIX = "s3_browser_tests_"

    data = {
        "bookmarks": {
            "foo": {
                "path": "/test-bucket/bar/baz",
                "created_on": "2019-01-01 00:00:00",
                "bogus_extra_data": "hodor",
            }
        }
    }

    @pytest.fixture(scope="class", autouse=True)
    def tear_down(self):
        """Clean up temporary bookmark files"""
        yield
        for f in os.listdir("/tmp"):
            if not f.startswith(self.FILE_PREFIX):
                continue

            os.remove(os.path.join("/tmp", f))

    @classmethod
    def gen_filename(cls):
        return f"/tmp/{cls.FILE_PREFIX}{uuid.uuid4()}.json"

    @property
    def expected_bookmarks(self):
        return self.normalise_bookmarks(
            {k: bookmarks.Bookmark(**v) for k, v in self.data["bookmarks"].items()}
        )

    def normalise_bookmarks(self, data):
        """Normalise bookmark data as dicts for easy comparison"""
        return {k: v.__dict__ for k, v in data.items()}

    def write_fixture(self, f, data=None):
        data = data or self.data

        with open(f, "w") as ff:
            json.dump(data, ff)

    def test_read_bookmarks_file(self):
        """Should be able to parse the bookmark format"""
        f = self.gen_filename()
        self.write_fixture(f)

        manager = bookmarks.BookmarkManager(f)
        actual = self.normalise_bookmarks(manager.bookmarks)
        assert actual == self.expected_bookmarks

    def test_clean_bookmark_data(self):
        """Should ignore unexpected fields in the bookmark file"""
        f = self.gen_filename()
        data = self.data.copy()
        data["bookmarks"]["foo"]["hodor"] = "foo"
        self.write_fixture(f)

        manager = bookmarks.BookmarkManager(f)
        actual = self.normalise_bookmarks(manager.bookmarks)
        assert actual == self.expected_bookmarks

    def test_missing_bookmark_file(self):
        """Should create an empty bookmark manager if file is missing"""
        f = self.gen_filename()
        manager = bookmarks.BookmarkManager(f)
        assert manager.bookmarks == {}

    def test_add_bookmarks(self):
        f = self.gen_filename()
        manager = bookmarks.BookmarkManager(f)
        manager.add_bookmark("foo", "/hodor/hodor/hodor")
        manager.add_bookmark("bar", "/hodor/hodor")
        manager.add_bookmark("baz", "/hodor")

        actual = manager.bookmarks
        assert actual.keys() == {"foo", "bar", "baz"}
        assert {v.path for v in actual.values()} == {
            "/hodor",
            "/hodor/hodor",
            "/hodor/hodor/hodor",
        }

        for v in actual.values():
            assert v.created_on is not None

    def test_remove_bookmarks(self):
        f = self.gen_filename()
        self.write_fixture(f)
        manager = bookmarks.BookmarkManager(f)

        actual = self.normalise_bookmarks(manager.bookmarks)
        assert actual == self.expected_bookmarks

        for b in self.data["bookmarks"]:
            assert manager.remove_bookmark(b) is True

        actual = self.normalise_bookmarks(manager.bookmarks)
        assert actual == {}

    def test_remove_missing_bookmark(self):
        f = self.gen_filename()
        man = bookmarks.BookmarkManager(f)
        man.add_bookmark("awesome_bookmark", "amazing/path")
        assert man.remove_bookmark("lame_bookmark") is False

    def test_save_bookmarks(self):
        f = self.gen_filename()
        man1 = bookmarks.BookmarkManager(f)
        man2 = bookmarks.BookmarkManager(f)

        # Initial load of empty data
        man2.load()

        # Bookmarks are written to disk eagerly as they're added / removed
        man1.add_bookmark("mighty_bookmark", "/valley/of/strength")
        man1.add_bookmark("feeble_bookmark", "/plain/of/wimpiness")
        man1.add_bookmark("average_bookmark", "/hill/of/normality")
        man1.remove_bookmark("average_bookmark")
        expected = self.normalise_bookmarks(man1.bookmarks)

        # Check the second instance is indeed empty
        assert self.normalise_bookmarks(man2.bookmarks) == {}

        # Now reload from disk and check it's the same as we just saved
        man2.load()
        assert self.normalise_bookmarks(man2.bookmarks) == expected

    def test_validate_bookmark_key(self):
        """Key names should be checked against a pattern"""
        valid_names = ["hodor", "ostrich", "potato123", "dashy-key"]
        invalid_names = ["thisnameisabittoolong", "funny/characters", "-flag"]

        for n in valid_names:
            assert bookmarks.BookmarkManager.validate_key(n) is True

        for n in invalid_names:
            assert bookmarks.BookmarkManager.validate_key(n) is False

    def test_unreadable_bookmark_file(self):
        """If the bookmark file is unreadable, load no bookmarks"""
        f = self.gen_filename()
        self.write_fixture(f)
        os.chmod(f, 0o200)  # TODO: Cross-platform solution?

        man = bookmarks.BookmarkManager(f)
        assert man.bookmarks is None
        assert man.add_bookmark("nope", "nope/nope/nope") is False

    def test_malformed_bookmark_file(self):
        """If the JSON is malformed, refuse to support bookmarks"""
        f = self.gen_filename()
        with open(f, "w") as ff:
            ff.write("bad json")

        man = bookmarks.BookmarkManager(f)
        assert man.bookmarks is None
        assert man.add_bookmark("nope", "nope/nope/nope") is False

    def test_bad_bookmark_file_data(self):
        """If the JSON has a bad structure, refuse to support bookmarks"""
        f = self.gen_filename()
        self.write_fixture(f, {"bookmarks": "should be an object!"})

        man = bookmarks.BookmarkManager(f)
        assert man.bookmarks is None
        assert man.add_bookmark("nope", "nope/nope/nope") is False
