import os
import copy

from jinja2 import Environment, FileSystemLoader
from flask import abort

from page import Page

class Site(object):
    def __init__(self, config):
        self.content_dir = config["content_dir"]
        self.default_page_config = config["default_page_config"]

        # jinja2 environment for loading templates
        self.env = Environment(loader=FileSystemLoader(config["template_dir"]))

    def generate_index(self, start_dir=None, depth=None):
        """Recursively generate a page index from the given starting directory.
        The listing is returned as an array of pages, where each page is
        represented in the form {"title": ..., "href": ..., children": [...]},
        where the children array may contain other pages.

        The depth parameter specifies the number of levels to go down, or None to
        give the full index"""
        start_dir = start_dir or self.content_dir
        listing = []

        dir_listing = os.listdir(start_dir)

        for entry in dir_listing:
            path = os.path.join(start_dir, entry)
            if os.path.isdir(path):

                # Only recurse if depth > 1
                if depth is None or depth > 1:
                    new_depth = None if depth is None else depth - 1
                    children = self.generate_index(start_dir=path, depth=new_depth)
                else:
                    children = []

                new_dir = {
                    "title": Page.format_page_name(path),
                    "url": self.get_url_for(path),
                    "children": children,
                    "path": os.path.join(path, "index.md")
                }
                listing.append(new_dir)

            elif entry.endswith(".md") and entry != "index.md":
                listing.append({
                    "title": Page.format_page_name(path),
                    "url": self.get_url_for(path),
                    "children": [],
                    "path": path
                })

        # If we are getting the root level pages then include home page
        if start_dir == self.content_dir:
            home = {"title": "Home",
                    "url": "/",
                    "children": [],
                    "path": os.path.join(self.content_dir, "index.md")}
            listing.insert(0, home)

        return listing

    def find_route_to_page(self, index, url):
        """Find the page in the index provided whose URL matches the URL
        provided. Return an route through the heirarchy of pages, e.g.
        for a page /articles/maths/calculus, the route would be
        [/articles, /articles/maths, /articles/maths/calculus]. Return False if
        the page is not found"""

        def find_route(page, url):
            p = page.copy()
            del p["children"]
            if p["url"] == url:
                return [p]
            for child in page["children"]:
                route = find_route(child, url)
                if route:
                    return [p] + route
            return False

        root = {"url": None, "children": index}
        route = find_route(root, url)

        if route:
            # Return from index 1 onwards since we do not want to include root
            return route[1:]
        else:
            # Page was not found
            return False

    def get_url_for(self, path):
        """Return the URL for the page at the specified path"""

        # Remove .md if present
        if path.endswith(".md"):
            path = path[:-3]

        # Return the part of the path after content directory
        return path.split(self.content_dir, 1)[1]

    def get_default_page_config(self):
        """Return the config that serves as a base for every page"""
        return copy.deepcopy(self.default_page_config)

    def view_page(self, url):
        """Render the specified page"""
        url = "/" + url

        # Get the site index and find page by URL
        index = self.generate_index()
        route = self.find_route_to_page(index, url)

        if route:
            default_config = self.get_default_page_config()

            # Set site index and header links
            default_config["site_index"] = index
            default_config["header_links"] = self.generate_index(depth=2)
            default_config["breadcrumbs"] = route

            page = Page(route[-1]["path"], default_config,
                        content_dir=self.content_dir)
            return page.to_html(self.env)

        else:
            abort(404)
