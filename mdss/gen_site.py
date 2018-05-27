import sys
import argparse
import os
from copy import copy
from collections import namedtuple

from jinja2 import Environment, FileSystemLoader
import yaml

from mdss.exceptions import InvalidPageError


class Page(object):

    # string used to separate context and content
    SECTION_SEPARATOR = "---"

    def __init__(self, name, breadcrumbs, src_path, children=None):
        """
        name        - page title
        breadcrumbs - list of names of parent pages, up to but not including
                      this one
        src_path    - path on disk to content file
        children    - child pages
        """
        self.name = name
        self.breadcrumbs = breadcrumbs
        self.src_path = src_path
        self.children = children or []

    def add_child(self, new_page):
        """
        Insert a page beneath this one
        """
        self.children.append(new_page)

    @classmethod
    def parse_context(cls, context_str):
        """
        Parse the context section and return a dict
        """
        try:
            return yaml.load(context_str)
        except yaml.scanner.ScannerError:
            raise InvalidPageError("Context was not valid YAML")

    def read_page_source(self):
        """
        Read the page context and contents from the file and return
        (context, content), where `context` is a dictionary and `content` is a
        string
        """
        if not self.src_path:
            return {}, ""

        context_str = ""
        content = ""
        context_section = True

        with open(self.src_path) as f:
            for line in f.readlines():
                if line.strip() == self.SECTION_SEPARATOR:
                    context_section = False
                    continue
                if context_section:
                    context_str += line
                else:
                    content += line
        context = self.parse_context(context_str)
        return context, content


class SiteTree(object):
    """
    A tree to store the hierarchy of pages
    """
    def __init__(self):
        self.root = Page(name="index", breadcrumbs=[], src_path=None)

    def insert(self, new_page, location, insert_at=None):
        """
        Insert a new page

        new_page  - Page object
        location  - breadcrumbs relative to the node to insert at
        insert_at - the node under which to insert (default: root)
        """
        start = insert_at or self.root

        # special case for home page
        if not location and new_page.name == self.root.name:
            self.root.src_path = new_page.src_path
            return

        # if page has no location then it lives under this node
        if not location:
            start.add_child(new_page)
            return

        # if page is at a lower level in the hierarchy, find the child under
        # which it should live
        next_insert_at = None
        for child in start.children:
            if child.name == location[0]:
                next_insert_at = child
                break

        # if none found create a new one
        if not next_insert_at:
            bread = copy(start.breadcrumbs)
            if start != self.root:
                bread.append(start.name)

            dummy_page = Page(name=location[0], breadcrumbs=bread,
                              src_path=None)
            start.add_child(dummy_page)
            next_insert_at = dummy_page

        self.insert(new_page, location[1:], insert_at=next_insert_at)

    def iter_node(self, start):
        """
        Return a list of nodes underneath and including `start`
        """
        nodes = [start]
        for child in start.children:
            nodes += self.iter_node(child)
        return nodes

    def __iter__(self):
        return (x for x in self.iter_node(self.root))


ConfigOption = namedtuple("ConfigOption", ["name", "default"])


class SiteConfig(dict):
    """
    Class to represent a global site configuration
    """
    options = [
        ConfigOption("templates_path", ["templates"]),
        ConfigOption("default_template", "base.html"),
    ]
    error_if_extra = True

    def __init__(self, d=None, **kwargs):
        """
        Initialise this config from another dictionary and validate items
        """
        super().__init__()

        d = d or {}
        if kwargs:
            d.update(kwargs)

        for opt in self.options:
            if opt.name in d:
                self[opt.name] = d.pop(opt.name)
            elif opt.default is not None:
                self[opt.name] = opt.default
            else:
                raise ValueError(
                    "Required value '{}' missing".format(opt.name)
                )

        if not self.error_if_extra:
            self.update(d)
        elif d:
            raise ValueError(
                "Unrecognised options: {}".format(", ".join(d.keys()))
            )

    def __getattr__(self, x):
        return self[x]


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "content_dir",
        help="The directory containing Markdown content"
    )
    parser.add_argument(
        "export_dir",
        help="The directory to export HTML files to"
    )
    args = parser.parse_args(sys.argv[1:])

    with open("mdss_config.yml") as f:
        config_dict = yaml.load(f)
    config = SiteConfig(config_dict)
    SiteGenerator(args.content_dir, config).gen_site(args.export_dir)


if __name__ == "__main__":
    main()
