from mdss.page import Page, HomePage
from mdss.utils import transfer_pages


class SiteTree:
    """
    A tree to store the hierarchy of pages
    """

    def __init__(self):
        self.root = HomePage()

    def set_root(self, new_root):
        """
        Set the root page
        """
        transfer_pages(self.root, new_root)
        self.root = new_root

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
        for child in start.iterchildren():
            if child.id == location[0]:
                next_insert_at = child
                break

        # if none found create a new one
        if not next_insert_at:
            dummy_page = Page(location[0])
            start.add_child(dummy_page)
            next_insert_at = dummy_page

        self.insert(new_page, location[1:], insert_at=next_insert_at)

    def iter_node(self, start):
        """
        Perform a pre-order traversal starting at node `start`
        """
        yield start
        for child in start.iterchildren():
            yield from self.iter_node(child)

    def __iter__(self):
        return self.iter_node(self.root)
