from operator import attrgetter

import yaml
from yaml.parser import ParserError
from yaml.scanner import ScannerError
import markdown

from mdss.exceptions import InvalidPageError


def cachedproperty(func):
    """
    Decorator to cache the value of a property so it is only calculated the
    first time it is accessed
    """
    def inner(self):
        attr = "_" + func.__name__
        if not hasattr(self, attr):
            setattr(self, attr, func(self))
        return getattr(self, attr)
    return property(inner)


class PageInfo:
    """
    Simplified object representing a page for use in templates
    """
    def __init__(self, path, title, children=None):
        self.path = path
        self.title = title
        self.children = children or []


class Page:
    """
    Class representing a page in the website. This may be a page corresponding
    to a source file, or an index page generated for a directory that contains
    source files
    """

    # string used to separate context and content
    section_separator = "---"

    markdown_extensions = ["markdown.extensions.tables",
                           "markdown.extensions.fenced_code",
                           "markdown.extensions.toc",
                           "markdown.extensions.codehilite"]

    def __init__(self, p_id, src_path=None):
        """
        p_id        - page ID
        src_path    - path on disk to content file (optional)
        """
        self.id = p_id
        self.src_path = src_path
        # relative URL path for exported page - will be set by parent in
        # add_child()
        self.dest_path = None

        self.children = {}
        self.parent = None

        self.title = self.get_default_title(self.id)
        if self.src_path:
            context, _ = self.read_page_source(context_only=True)
            if "title" in context:
                self.title = context["title"]

    @cachedproperty
    def breadcrumbs(self):
        """
        Return a path from the home page to this page through this page's
        parents.

        Return a list of PageInfo objects starting at home and ending with this
        page
        """
        p_info = PageInfo(self.dest_path, self.title)
        if self.parent is None:
            return [p_info]
        return self.parent.breadcrumbs + [p_info]

    @classmethod
    def get_default_title(cls, p_id):
        """
        Return a default title from an ID
        """
        return p_id.replace("-", " ").capitalize()

    def add_child(self, new_page):
        """
        Insert a page beneath this one
        """
        new_page.parent = self
        new_page.dest_path = self.dest_path + new_page.id + "/"

        # if page already exists (e.g. dummy page was created before content
        # file seen), transfer its children to its replacement
        if new_page.id in self.children:
            for grandchild in self.children[new_page.id].iterchildren():
                new_page.add_child(grandchild)

        self.children[new_page.id] = new_page

    def iterchildren(self):
        """
        Return an iterator over this page's children sorted by title
        """
        return sorted(self.children.values(), key=attrgetter("title"))

    def child_listing(self):
        """
        Return a list of this page's children as PageInfo objects and descend
        recursively
        """
        listing = []
        for child in self.iterchildren():
            listing.append(PageInfo(child.dest_path, child.title,
                                    child.child_listing()))
        return listing

    @classmethod
    def content_to_html(cls, md_str):
        """
        Convert page content and return HTML as a string
        """
        return markdown.markdown(md_str, extensions=cls.markdown_extensions)

    def parse_context(self, context_str):
        """
        Parse the context section and return a dict
        """
        try:
            context = yaml.load(context_str) or {}
        except (ParserError, ScannerError):
            raise InvalidPageError("Context was not valid YAML in file '{}'"
                                   .format(self.src_path))

        return context

    def read_page_source(self, context_only=False):
        """
        Read the page context and contents from the file and return
        (context, content), where `context` is a dictionary and `content` is
        the raw markdown content string.

        If `context_only` is True then the content part is not read and
        `content` is the empty string.
        """
        if not self.src_path:
            return {}, ""

        context_str = ""
        content = ""
        context_section = True

        with open(self.src_path) as f:
            for line in f.readlines():
                if line.strip() == self.section_separator:
                    if context_only:
                        break
                    context_section = False
                    continue
                if context_section:
                    context_str += line
                else:
                    content += line
        context = self.parse_context(context_str)
        return context, content


class HomePage(Page):
    """
    Root level page
    """
    title = "Home"

    def __init__(self, src_path=None):
        super().__init__(HomePage.title, src_path=src_path)
        self.dest_path = "/"
