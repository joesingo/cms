import os
from copy import copy

from jinja2 import Environment, FileSystemLoader

from mdss.page import Page
from mdss.tree import SiteTree
from mdss.config import SiteConfig
from mdss.exceptions import InvalidPageError


class SiteGenerator(object):
    def __init__(self, content_dir, config):
        self.tree = SiteTree()
        self.content_dir = content_dir
        self.config = config
        self.env = Environment(
            loader=FileSystemLoader(self.config.templates_path)
        )

    @classmethod
    def split_path(cls, path):
        """
        Split a path by list into its components
        """
        path = os.path.normpath(path)
        head, tail = os.path.split(path)
        if head in ("", os.path.sep):
            return [tail]
        if tail:
            return cls.split_path(head) + [tail]
        return cls.split_path(head)

    def add_page(self, page_path):
        """
        Insert a page at the given source path into the site tree
        """
        relpath = os.path.relpath(page_path, start=self.content_dir)
        parts = SiteGenerator.split_path(relpath[:-3])

        # remove trailing 'index' unless this is the root page
        if parts[-1] == "index" and len(parts) > 1:
            parts.pop(-1)

        name = parts[-1]
        breadcrumbs = parts[:-1]
        page = Page(name, breadcrumbs, page_path)
        self.tree.insert(page, location=breadcrumbs)

    def gen_site(self, export_dir):
        """
        Find all content and write rendered pages
        """
        for dirpath, dirnames, filenames in os.walk(self.content_dir):
            for fname in filenames:
                if fname.endswith(".md"):
                    self.add_page(os.path.join(dirpath, fname))
        self.render_all(export_dir)

    def get_dest_path(self, page):
        """
        Construct the path to write a page to in the export dir
        """
        prefix = copy(page.breadcrumbs)
        if page.name != "index":
            prefix.append(page.name)
        return os.path.join(*prefix, "index.html")

    def render_page(self, page):
        """
        Return a page HTML as a string
        """
        context, content = page.read_page_source()

        # modify context
        context.update(content=content)

        if "template" not in context:
            context["template"] = self.config.default_template

        if "title" not in context:
            context["title"] = page.name

        template = self.env.get_template(context.pop("template"))
        return template.render(**context)

    def render_all(self, export_dir):
        """
        Render each page in the tree and write it to a file
        """
        for page in self.tree:
            dest_path = os.path.join(export_dir, self.get_dest_path(page))

            # make sure containing directory exists
            par_dir = os.path.dirname(dest_path)
            if not os.path.isdir(par_dir):
                os.makedirs(par_dir)

            with open(dest_path, "w") as f:
                f.write(self.render_page(page))
