from mdss.page import Page


class SiteTree(object):
    """
    A tree to store the hierarchy of pages
    """
    HOME_PAGE_NAME = "Home"

    def __init__(self):
        self.root = Page(name=self.HOME_PAGE_NAME, location=[], src_path=None)

    def set_root_path(self, path):
        """
        Set the path to the source file for the root homepage
        """
        self.root.src_path = path

    def insert(self, new_page, location, insert_at=None):
        """
        Insert a new page

        new_page  - Page object
        location  - location of the new page in the hierarchy relative to the
                    node to insert at
        insert_at - the node under which to insert (default: root)
        """
        start = insert_at or self.root

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
            dummy_location = start.location + [start.name]
            dummy_page = Page(name=location[0], location=dummy_location,
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
