from copy import copy

from mdss.page import Page


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
